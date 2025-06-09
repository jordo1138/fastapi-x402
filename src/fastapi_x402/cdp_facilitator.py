"""CDP-compatible facilitator client for fastapi-x402."""

import base64
import json
import os
from typing import Any, Dict, Optional, Tuple

import httpx

from .models import PaymentRequirements, SettleResponse, VerifyResponse


class CDPFacilitatorClient:
    """
    Facilitator client compatible with Coinbase CDP authentication.

    Uses the cleaner API format from Coinbase's x402 implementation:
    - Sends raw payment header (not decoded)
    - Uses 'paymentHeader' and 'paymentRequirements' fields
    - Supports CDP authentication headers
    """

    def __init__(self, url: str):
        if url.startswith("http://") or url.startswith("https://"):
            self.url = url.rstrip("/")
        else:
            raise ValueError(f"Invalid URL {url}, must start with http:// or https://")

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )

        # Check for CDP credentials
        self.cdp_key_id: Optional[str] = os.getenv("CDP_API_KEY_ID")
        self.cdp_secret: Optional[str] = os.getenv("CDP_API_KEY_SECRET")
        self.has_cdp_auth = bool(self.cdp_key_id and self.cdp_secret)

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers, including CDP authentication if available."""
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "user-agent": "fastapi-x402-python",
        }

        if self.has_cdp_auth and self.cdp_key_id and self.cdp_secret:
            # Add CDP authentication headers
            # Note: This is a placeholder - actual CDP auth might use JWT or other methods
            headers["X-CDP-API-KEY-ID"] = self.cdp_key_id
            headers["X-CDP-API-SECRET"] = self.cdp_secret

        return headers

    async def verify_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> VerifyResponse:
        """
        Verify a payment header using the simplified Coinbase API format.

        Args:
            payment_header: Raw X-PAYMENT header value from client
            payment_requirements: Payment requirements for this request

        Returns:
            VerifyResponse with verification result
        """
        try:
            payload = {
                "paymentHeader": payment_header,
                "paymentRequirements": payment_requirements.model_dump(),
            }

            response = await self.client.post(
                f"{self.url}/verify",
                json=payload,
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                return VerifyResponse(**data)
            else:
                return VerifyResponse(
                    isValid=False,
                    error=f"Facilitator error: {response.status_code} {response.text}",
                )

        except Exception as e:
            return VerifyResponse(
                isValid=False,
                error=f"Failed to verify payment: {str(e)}",
            )

    async def settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> SettleResponse:
        """
        Settle a payment using the simplified Coinbase API format.

        Args:
            payment_header: Raw X-PAYMENT header value from client
            payment_requirements: Payment requirements for this request

        Returns:
            SettleResponse with settlement result
        """
        try:
            payload = {
                "paymentHeader": payment_header,
                "paymentRequirements": payment_requirements.model_dump(),
            }

            response = await self.client.post(
                f"{self.url}/settle",
                json=payload,
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                return SettleResponse(
                    success=True,
                    transaction=data.get("transaction", ""),
                    network=data.get("network", "unknown"),
                    payer=data.get("payer"),
                )
            else:
                try:
                    error_data = response.json()
                    error_reason = error_data.get(
                        "errorReason", f"HTTP {response.status_code}"
                    )
                except:
                    error_reason = f"HTTP {response.status_code}: {response.text}"

                return SettleResponse(
                    success=False,
                    errorReason=error_reason,
                )

        except Exception as e:
            return SettleResponse(
                success=False,
                errorReason=f"Failed to settle payment: {str(e)}",
            )

    async def verify_and_settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> Tuple[VerifyResponse, SettleResponse]:
        """Verify and immediately settle payment in one call."""
        # First verify
        verify_response = await self.verify_payment(
            payment_header, payment_requirements
        )

        if not verify_response.isValid:
            failed_settle = SettleResponse(
                success=False, errorReason="Verification failed"
            )
            return verify_response, failed_settle

        # Then settle
        settle_response = await self.settle_payment(
            payment_header, payment_requirements
        )
        return verify_response, settle_response

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

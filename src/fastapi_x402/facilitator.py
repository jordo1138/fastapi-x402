"""
Unified facilitator client for both testnet (x402.org) and mainnet (Coinbase CDP).
Automatically detects which facilitator to use based on configuration.
"""

import base64
import json
import os
import random
import time
from typing import Any, Dict, Optional, Tuple

import httpx

try:
    from cdp.auth import generate_jwt  # type: ignore[import-untyped]
    from cdp.auth.utils.jwt import JwtOptions  # type: ignore[import-untyped]

    CDP_SDK_AVAILABLE = True
except ImportError:
    CDP_SDK_AVAILABLE = False

from .models import PaymentRequirements, SettleResponse, VerifyResponse


def to_json_safe(data: Any) -> Any:
    """Convert bigint-like values to strings like TypeScript toJsonSafe function."""
    if isinstance(data, dict):
        return {key: to_json_safe(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [to_json_safe(item) for item in data]
    elif isinstance(data, int) and data > 2**53:  # Large integers that might be bigint
        return str(data)
    else:
        return data


class UnifiedFacilitatorClient:
    """
    Unified client for both testnet (x402.org) and mainnet (Coinbase CDP) facilitators.

    Automatically detects which facilitator to use:
    - Coinbase CDP: When base_url contains 'cdp.coinbase.com' or CDP credentials provided
    - x402.org: Default gasless facilitator for testnet
    """

    def __init__(
        self,
        base_url: str,
        cdp_api_key_id: Optional[str] = None,
        cdp_api_key_secret: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")

        # Detect if this is Coinbase CDP facilitator (based on URL only)
        self.is_coinbase_cdp = "cdp.coinbase.com" in self.base_url

        # Store CDP credentials if provided
        self.cdp_api_key_id = cdp_api_key_id or os.getenv("CDP_API_KEY_ID")
        self.cdp_api_key_secret = cdp_api_key_secret or os.getenv("CDP_API_KEY_SECRET")

        # Validate CDP setup if needed
        if self.is_coinbase_cdp:
            if not self.cdp_api_key_id or not self.cdp_api_key_secret:
                raise ValueError(
                    "CDP API key ID and secret are required for Coinbase facilitator"
                )
            if not CDP_SDK_AVAILABLE:
                raise ValueError(
                    "CDP SDK is required for Coinbase facilitator. Install with: pip install cdp-sdk"
                )

        # Configure HTTP client
        self.client = httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={},
        )

        # Set up endpoints
        if self.is_coinbase_cdp:
            self.verify_url = f"{self.base_url}/verify"
            self.settle_url = f"{self.base_url}/settle"
        else:
            self.verify_url = f"{self.base_url}/verify"
            self.settle_url = f"{self.base_url}/settle"

    def _create_coinbase_headers(self, endpoint: str) -> Dict[str, str]:
        """Create headers for Coinbase CDP facilitator."""
        if not self.is_coinbase_cdp:
            return {
                "accept": "*/*",
                "content-type": "application/json",
                "user-agent": "fastapi-x402-python",
            }

        # Generate JWT for Coinbase CDP
        request_path = f"/platform/v2/x402/{endpoint}"

        try:
            options = JwtOptions(
                api_key_id=self.cdp_api_key_id,
                api_key_secret=self.cdp_api_key_secret,
                method="POST",
                uri=request_path,
                service="x402",
                nonce=self._generate_nonce(),
                expiry=int(time.time()) + 300,  # 5 minutes
            )
            jwt_token = generate_jwt(options)
        except Exception as e:
            raise ValueError(f"Failed to generate CDP JWT: {e}")

        return {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "fastapi-x402-python",
            "Authorization": f"Bearer {jwt_token}",
            "Correlation-Context": f"x402-version=0.1.2,sdk-version=1.0.0,correlation-header={self._generate_nonce()}",
        }

    def _generate_nonce(self) -> str:
        """Generate a random nonce."""
        return "".join(random.choices("0123456789", k=16))

    async def verify_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> VerifyResponse:
        """Verify payment with the appropriate facilitator."""
        try:
            # Decode payment header (same for both facilitators)
            try:
                payment_data = base64.b64decode(payment_header).decode("utf-8")
                payment_obj = json.loads(payment_data)
            except Exception as e:
                return VerifyResponse(
                    isValid=False,
                    error=f"Failed to decode payment header: {str(e)}",
                )

            # Create request payload (same format for both)
            payload = {
                "paymentPayload": to_json_safe(payment_obj),
                "paymentRequirements": to_json_safe(payment_requirements.model_dump()),
            }

            # Get appropriate headers
            headers = self._create_coinbase_headers("verify")

            # Make request
            print(f"🔍 FACILITATOR DEBUG:")
            print(f"🔍 URL: {self.verify_url}")
            print(f"🔍 Method: POST")
            print(f"🔍 Headers: {headers}")
            print(f"🔍 Payload: {payload}")

            response = await self.client.post(
                self.verify_url,
                json=payload,
                headers=headers,
            )

            print(f"🔍 Response Status: {response.status_code}")
            print(f"🔍 Response Headers: {dict(response.headers)}")
            print(f"🔍 Response Body: {response.text}")

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
        """Settle payment with the appropriate facilitator."""
        try:
            # Decode payment header (same for both facilitators)
            try:
                payment_data = base64.b64decode(payment_header).decode("utf-8")
                payment_obj = json.loads(payment_data)
            except Exception as e:
                return SettleResponse(
                    success=False,
                    errorReason=f"Failed to decode payment header: {str(e)}",
                )

            # Create request payload (same format for both)
            payload = {
                "paymentPayload": to_json_safe(payment_obj),
                "paymentRequirements": to_json_safe(payment_requirements.model_dump()),
            }

            # Get appropriate headers
            headers = self._create_coinbase_headers("settle")

            # Make request
            response = await self.client.post(
                self.settle_url,
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                    return SettleResponse(
                        success=True,
                        transaction=data.get("transaction", ""),
                        network=data.get("network", "unknown"),
                        payer=data.get("payer"),
                    )
                except Exception:
                    return SettleResponse(
                        success=False,
                        errorReason="Invalid JSON response from facilitator",
                    )
            else:
                try:
                    data = response.json()
                    error_reason = data.get(
                        "errorReason", f"HTTP {response.status_code}"
                    )
                except Exception:
                    error_reason = f"HTTP {response.status_code}: {response.text[:100]}"
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
        verify_response = await self.verify_payment(
            payment_header, payment_requirements
        )
        if not verify_response.isValid:
            failed_settle = SettleResponse(
                success=False, errorReason="Verification failed"
            )
            return verify_response, failed_settle

        settle_response = await self.settle_payment(
            payment_header, payment_requirements
        )
        return verify_response, settle_response

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

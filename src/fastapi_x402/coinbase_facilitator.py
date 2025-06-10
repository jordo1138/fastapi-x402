"""
Official Coinbase facilitator client for mainnet x402.
Uses the real Coinbase CDP facilitator with proper JWT authentication.
"""

import base64
import json
import os
import random
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

try:
    import jwt
    from cdp.api_key_utils import _parse_private_key  # type: ignore[import-untyped]
    from cdp.errors import InvalidAPIKeyFormatError  # type: ignore[import-untyped]
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519

    CDP_SDK_AVAILABLE = True
except ImportError:
    CDP_SDK_AVAILABLE = False

from .models import PaymentRequirements, SettleResponse, VerifyResponse

# Official Coinbase facilitator configuration
COINBASE_FACILITATOR_BASE_URL = "https://api.cdp.coinbase.com"
COINBASE_FACILITATOR_V2_ROUTE = "/platform/v2/x402"

# Version info for correlation header
X402_VERSION = "0.1.2"  # Our package version
SDK_VERSION = "1.0.0"  # Our SDK version


class CoinbaseFacilitatorClient:
    """
    Official Coinbase facilitator client for mainnet x402 payments.

    This uses Coinbase's real CDP facilitator service at api.cdp.coinbase.com
    with proper JWT authentication and correlation headers.
    """

    def __init__(
        self, api_key_id: Optional[str] = None, api_key_secret: Optional[str] = None
    ):
        # Get credentials from parameters or environment
        self.api_key_id = api_key_id or os.getenv("CDP_API_KEY_ID")
        self.api_key_secret = api_key_secret or os.getenv("CDP_API_KEY_SECRET")

        if not self.api_key_id or not self.api_key_secret:
            raise ValueError(
                "CDP API credentials required. Set CDP_API_KEY_ID and CDP_API_KEY_SECRET "
                "environment variables or pass them to constructor."
            )

        if not CDP_SDK_AVAILABLE:
            raise ImportError(
                "CDP SDK required for Coinbase facilitator. Install with: pip install cdp-sdk"
            )

        # Official Coinbase facilitator URLs
        self.base_url = COINBASE_FACILITATOR_BASE_URL
        self.verify_url = f"{self.base_url}{COINBASE_FACILITATOR_V2_ROUTE}/verify"
        self.settle_url = f"{self.base_url}{COINBASE_FACILITATOR_V2_ROUTE}/settle"
        self.request_host = COINBASE_FACILITATOR_BASE_URL.replace("https://", "")

        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )

    def _create_correlation_header(self) -> str:
        """Create correlation header as per Coinbase specification."""
        data = {
            "sdk_version": SDK_VERSION,
            "sdk_language": "python",
            "source": "fastapi-x402",
            "source_version": X402_VERSION,
        }
        return ",".join(f"{key}={value}" for key, value in data.items())

    def _create_auth_header(self, request_path: str) -> str:
        """Create JWT authorization header for Coinbase API using CDP SDK approach."""
        try:
            # Build JWT using the same approach as CDP SDK
            jwt_token = self._build_jwt(request_path, "POST")
            return f"Bearer {jwt_token}"
        except Exception as e:
            raise ValueError(f"Failed to generate JWT: {e}")

    def _build_jwt(self, request_path: str, method: str = "POST") -> str:
        """Build JWT token using CDP SDK approach."""
        # Parse the private key
        private_key_obj = _parse_private_key(self.api_key_secret)

        # Determine signing algorithm based on the key type
        if isinstance(private_key_obj, ec.EllipticCurvePrivateKey):
            alg = "ES256"
        elif isinstance(private_key_obj, ed25519.Ed25519PrivateKey):
            alg = "EdDSA"
        else:
            raise InvalidAPIKeyFormatError("Unsupported key type")

        header = {
            "alg": alg,
            "kid": self.api_key_id,
            "typ": "JWT",
            "nonce": self._generate_nonce(),
        }

        # Build the URI in the format: "POST api.cdp.coinbase.com/platform/v2/x402/verify"
        uri = f"{method} {self.request_host}{request_path}"

        claims = {
            "sub": self.api_key_id,
            "iss": "cdp",
            "aud": ["cdp_service"],
            "nbf": int(time.time()),
            "exp": int(time.time()) + 60,  # Token valid for 1 minute
            "uris": [uri],
        }

        try:
            token: str = jwt.encode(
                claims, private_key_obj, algorithm=alg, headers=header
            )
            return token
        except Exception as e:
            raise InvalidAPIKeyFormatError(f"Could not sign the JWT: {e}")

    def _generate_nonce(self) -> str:
        """Generate a random nonce for the JWT."""
        return "".join(random.choices("0123456789", k=16))

    def _get_headers(self, endpoint: str) -> Dict[str, str]:
        """Get headers including JWT auth and correlation context."""
        request_path = f"{COINBASE_FACILITATOR_V2_ROUTE}/{endpoint}"

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "fastapi-x402-python",
            "Authorization": self._create_auth_header(request_path),
            "Correlation-Context": self._create_correlation_header(),
        }

        return headers

    async def verify_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> VerifyResponse:
        """
        Verify payment using Coinbase's official facilitator.

        Args:
            payment_header: Base64-encoded payment payload
            payment_requirements: Payment requirements for verification

        Returns:
            VerifyResponse with verification result
        """
        try:
            payload = {
                "paymentHeader": payment_header,
                "paymentRequirements": payment_requirements.model_dump(),
            }

            headers = self._get_headers("verify")

            response = await self.client.post(
                self.verify_url,
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                return VerifyResponse(**data)
            else:
                return VerifyResponse(
                    isValid=False,
                    error=f"Coinbase facilitator error: {response.status_code} {response.text}",
                )

        except Exception as e:
            return VerifyResponse(
                isValid=False,
                error=f"Failed to verify payment with Coinbase facilitator: {str(e)}",
            )

    async def settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> SettleResponse:
        """
        Settle payment using Coinbase's official facilitator.

        Args:
            payment_header: Base64-encoded payment payload
            payment_requirements: Payment requirements for settlement

        Returns:
            SettleResponse with settlement result
        """
        try:
            payload = {
                "paymentHeader": payment_header,
                "paymentRequirements": payment_requirements.model_dump(),
            }

            headers = self._get_headers("settle")

            response = await self.client.post(
                self.settle_url,
                json=payload,
                headers=headers,
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
                errorReason=f"Failed to settle payment with Coinbase facilitator: {str(e)}",
            )

    async def verify_and_settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> tuple[VerifyResponse, SettleResponse]:
        """Verify and settle payment in one call."""
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

"""Facilitator client for payment verification and settlement."""

import base64
import json
from typing import Optional

import httpx

from .models import (
    PaymentRequirements,
    SettleResponse,
    VerifyRequest,
    VerifyResponse,
)


def to_json_safe(data):
    """Convert bigint-like values to strings like TypeScript toJsonSafe function."""
    if isinstance(data, dict):
        return {key: to_json_safe(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [to_json_safe(item) for item in data]
    elif isinstance(data, int) and data > 2**53:  # Large integers that might be bigint
        return str(data)
    else:
        return data


class FacilitatorClient:
    """Client for interacting with x402 payment facilitator."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # Configure client to match Node.js fetch() behavior exactly
        self.client = httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=True,  # Critical: follow redirects like fetch() does
            headers={},  # No default headers
        )

    async def verify_payment(
        self,
        payment_header: str,
        payment_requirements: PaymentRequirements,
    ) -> VerifyResponse:
        """Verify a payment with the facilitator.

        Args:
            payment_header: X-PAYMENT header value from client
            payment_requirements: Payment requirements for this request

        Returns:
            VerifyResponse with verification result
        """
        try:
            # Decode the base64 payment header to get the payment object
            try:
                payment_data = base64.b64decode(payment_header).decode("utf-8")
                payment_obj = json.loads(payment_data)
            except Exception as e:
                return VerifyResponse(
                    isValid=False,
                    error=f"Failed to decode payment header: {str(e)}",
                )

            # Extract x402Version from payment object
            x402_version = payment_obj.get("x402Version", 1)

            # Check if we're using local facilitator
            is_local_facilitator = (
                "localhost" in self.base_url or "127.0.0.1" in self.base_url
            )

            if is_local_facilitator:
                # Local facilitator expects just paymentPayload and paymentRequirements
                payload = {
                    "paymentPayload": to_json_safe(payment_obj),
                    "paymentRequirements": to_json_safe(
                        payment_requirements.model_dump()
                    ),
                }
            else:
                # External facilitator expects x402Version wrapper
                request = VerifyRequest(
                    x402Version=x402_version,
                    paymentPayload=to_json_safe(payment_obj),
                    paymentRequirements=payment_requirements,
                )
                payload = request.model_dump()
            # Debug logging (comment out for production)
            # print(f"DEBUG: Sending to facilitator /verify:")
            # print(f"URL: {self.base_url}/verify")
            # print(f"Payload: {payload}")

            # Match EXACT headers that Node.js fetch() sends (no compression for now)
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "user-agent": "node",
            }

            response = await self.client.post(
                f"{self.base_url}/verify",
                content=json.dumps(payload),
                headers=headers,
            )

            # Debug logging (comment out for production)
            # print(f"DEBUG: Facilitator response status: {response.status_code}")
            # print(f"DEBUG: Facilitator response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                return VerifyResponse(**data)
            else:
                return VerifyResponse(
                    isValid=False,
                    error=f"Facilitator error: {response.status_code} {response.text}",
                )

        except Exception as e:
            # Handle network errors gracefully
            error_msg = f"Failed to verify payment: {str(e)}"
            if "nodename nor servname provided" in str(e):
                error_msg = "Facilitator service unavailable"
            elif "timeout" in str(e).lower():
                error_msg = "Facilitator request timeout"

            return VerifyResponse(
                isValid=False,
                error=error_msg,
            )

    async def settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> SettleResponse:
        """Settle a verified payment.

        Args:
            payment_header: X-PAYMENT header value from client
            payment_requirements: Payment requirements for this request

        Returns:
            SettleResponse with settlement result
        """
        try:
            # Decode payment and use the new settle_payment_object method
            decoded_payment = self._decode_payment_header(payment_header)
            return await self.settle_payment_object(
                decoded_payment, payment_requirements
            )

        except Exception as e:
            return SettleResponse(
                success=False,
                error_reason=f"Failed to settle payment: {str(e)}",
                network="base-sepolia",
            )

    async def verify_and_settle_payment(
        self, payment_header: str, payment_requirements: PaymentRequirements
    ) -> tuple[VerifyResponse, SettleResponse]:
        """Verify and immediately settle payment in one call (like TypeScript version)."""
        # First verify
        verify_response = await self.verify_payment(
            payment_header, payment_requirements
        )
        if not verify_response.is_valid:
            failed_settle = SettleResponse(
                success=False, error_reason="Verification failed"
            )
            return verify_response, failed_settle

        # Immediately settle using the same decoded payment
        decoded_payment = self._decode_payment_header(payment_header)
        settle_response = await self.settle_payment_object(
            decoded_payment, payment_requirements
        )
        return verify_response, settle_response

    def _decode_payment_header(self, payment_header: str) -> dict:
        """Decode payment header exactly like CDP's decodePayment function."""
        try:
            payment_data = base64.b64decode(payment_header).decode("utf-8")
            parsed_payment = json.loads(payment_data)

            # Reconstruct payment object exactly like CDP's decodePayment function
            decoded_payment = {
                **parsed_payment,
                "payload": {
                    "signature": parsed_payment["payload"]["signature"],
                    "authorization": {
                        **parsed_payment["payload"]["authorization"],
                        "value": parsed_payment["payload"]["authorization"]["value"],
                        "validAfter": parsed_payment["payload"]["authorization"][
                            "validAfter"
                        ],
                        "validBefore": parsed_payment["payload"]["authorization"][
                            "validBefore"
                        ],
                    },
                },
            }
            return decoded_payment
        except Exception as e:
            raise ValueError(f"Failed to decode payment header: {str(e)}")

    async def settle_payment_object(
        self, decoded_payment: dict, payment_requirements: PaymentRequirements
    ) -> SettleResponse:
        """Settle a payment using already decoded payment object (like CDP does).

        Args:
            decoded_payment: Already decoded payment object (not base64 header)
            payment_requirements: Payment requirements for this request

        Returns:
            SettleResponse with settlement result
        """
        try:
            # Extract x402Version from decoded payment
            x402_version = decoded_payment.get("x402Version", 1)

            # Check if we're using local facilitator
            is_local_facilitator = (
                "localhost" in self.base_url or "127.0.0.1" in self.base_url
            )

            if is_local_facilitator:
                # Local facilitator expects just paymentPayload and paymentRequirements
                settle_request = {
                    "paymentPayload": to_json_safe(decoded_payment),
                    "paymentRequirements": to_json_safe(
                        payment_requirements.model_dump()
                    ),
                }
            else:
                # External facilitator expects x402Version wrapper
                settle_request = {
                    "x402Version": x402_version,
                    "paymentPayload": to_json_safe(decoded_payment),
                    "paymentRequirements": to_json_safe(
                        payment_requirements.model_dump()
                    ),
                }

            print(f"DEBUG: Sending to facilitator /settle (object method):")
            print(f"URL: {self.base_url}/settle")

            # Log payment nonce to check if payments are fresh
            nonce = (
                decoded_payment.get("payload", {})
                .get("authorization", {})
                .get("nonce", "unknown")
            )
            print(f"DEBUG: Payment nonce: {nonce}")
            print(f"Payload: {settle_request}")

            # Save request to file for debugging
            import json

            with open("/tmp/bad_payload.json", "w") as f:
                json.dump(settle_request, f, indent=2)
            print(f"DEBUG: Saved Python settlement request to /tmp/bad_payload.json")

            # Use manual JSON stringification like TypeScript version does
            json_body = json.dumps(settle_request)
            print(f"DEBUG: JSON body: {json_body}")

            # Match EXACT headers that Node.js fetch() sends (no compression for now)
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "user-agent": "node",
            }

            response = await self.client.post(
                f"{self.base_url}/settle",
                content=json_body,
                headers=headers,
            )

            print(f"DEBUG: Settlement response status: {response.status_code}")
            print(f"DEBUG: Settlement response: {response.text}")
            print(f"DEBUG: Settlement response headers: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                return SettleResponse(
                    success=True,
                    transaction=data.get("transaction", ""),
                    network=data.get("network", "unknown"),
                )
            else:
                data = response.json()
                error_reason = data.get("errorReason", f"HTTP {response.status_code}")
                return SettleResponse(
                    success=False,
                    error_reason=error_reason,
                )

        except Exception as e:
            # Handle network errors gracefully
            error_msg = f"Failed to settle payment: {str(e)}"
            if "nodename nor servname provided" in str(e):
                error_msg = "Facilitator service unavailable"
            elif "timeout" in str(e).lower():
                error_msg = "Facilitator request timeout"

            return SettleResponse(
                success=False,
                error_reason=error_msg,
            )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

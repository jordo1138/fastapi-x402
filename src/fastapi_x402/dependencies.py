"""Payment dependencies for FastAPI x402."""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .facilitator import UnifiedFacilitatorClient

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .core import (
    get_config,
    get_facilitator_client,
    get_payment_config,
    requires_payment,
)
from .models import PaymentRequirements


class PaymentDependency:
    """Dependency to handle payment verification."""

    def __init__(self, auto_settle: bool = True):
        self.auto_settle = auto_settle
        self._facilitator_client: Optional["UnifiedFacilitatorClient"] = None

    @property
    def facilitator_client(self) -> "UnifiedFacilitatorClient":
        """Get or create facilitator client."""
        if self._facilitator_client is None:
            self._facilitator_client = get_facilitator_client()
        return self._facilitator_client

    async def __call__(self, request: Request) -> None:
        """Check payment for the current request."""

        # Get the route handler function from the request
        route_handler = None
        if hasattr(request, "scope") and "route" in request.scope:
            route_handler = request.scope["route"].endpoint

        # If no payment required, return None (allow request)
        if not route_handler or not requires_payment(route_handler):
            return None

        # Get payment configuration for this endpoint
        payment_config = get_payment_config(route_handler)
        if not payment_config:
            return None

        # Check for payment header
        payment_header = request.headers.get("X-PAYMENT")

        if not payment_header:
            # No payment provided, raise 402 with requirements
            payment_requirements = self._build_payment_requirements(
                request, payment_config
            )
            raise HTTPException(
                status_code=402,
                detail=payment_requirements.model_dump(),
            )

        # Verify payment
        try:
            payment_requirements = self._build_payment_requirements(
                request, payment_config
            )

            verify_response = await self.facilitator_client.verify_payment(
                payment_header, payment_requirements
            )

            if not verify_response.isValid:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "Payment verification failed",
                        "message": verify_response.error or "Invalid payment",
                    },
                )

            # Settle payment if auto_settle is enabled
            if self.auto_settle and verify_response.payment_id:
                settle_response = await self.facilitator_client.settle_payment(
                    payment_header, payment_requirements
                )

                if settle_response.tx_status != "SETTLED":
                    raise HTTPException(
                        status_code=402,
                        detail={
                            "error": "Payment settlement failed",
                            "message": settle_response.error or "Settlement failed",
                        },
                    )

                # Add settlement info to request state
                request.state.payment_settled = True
                request.state.tx_hash = settle_response.tx_hash

            # Add payment info to request state
            request.state.payment_verified = True
            request.state.payment_id = verify_response.payment_id

            return None  # Allow request to continue

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Payment processing failed",
                    "message": str(e),
                },
            ) from e

    def _build_payment_requirements(
        self,
        request: Request,
        payment_config: dict,
    ) -> PaymentRequirements:
        """Build payment requirements for the current request."""

        config = get_config()

        # Build resource identifier (method + path)
        resource = f"{request.method} {request.url.path}"
        if request.query_params:
            resource += f"?{request.query_params}"

        # Convert price to atomic units (assuming USDC with 6 decimals)
        price_str = payment_config["amount"]
        if price_str.startswith("$"):
            price_float = float(price_str[1:])  # Remove $ and convert
            atomic_amount = str(int(price_float * 1_000_000))  # USDC has 6 decimals
        else:
            atomic_amount = str(int(float(price_str) * 1_000_000))

        # Use the first network if config.network is a list
        network = (
            config.network if isinstance(config.network, str) else config.network[0]
        )

        # USDC contract address based on network
        if network == "base":
            usdc_address = (
                "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base mainnet
            )
        elif network == "base-sepolia":
            usdc_address = (
                "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC on Base Sepolia
            )
        else:
            # Default to Base mainnet USDC for other networks
            usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

        return PaymentRequirements(
            scheme="exact",
            network=network,
            maxAmountRequired=atomic_amount,
            resource=resource,
            description=f"Payment required for {resource}",
            mimeType="application/json",
            payTo=config.pay_to,
            maxTimeoutSeconds=payment_config.get("expires_in")
            or config.default_expires_in,
            asset=usdc_address,
        )


# Global dependency instance
payment_required = PaymentDependency()

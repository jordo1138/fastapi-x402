"""Payment middleware for FastAPI x402."""

import base64
import json
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from .facilitator import UnifiedFacilitatorClient

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from .core import (
    get_config,
    get_facilitator_client,
    get_payment_config,
    get_payment_config_by_name,
    requires_payment,
    requires_payment_by_name,
)
from .models import PaymentRequirements


class PaymentMiddleware(BaseHTTPMiddleware):
    """Middleware to handle x402 payment verification for FastAPI endpoints."""

    def __init__(self, app: Any, auto_settle: bool = True) -> None:
        """Initialize payment middleware.

        Args:
            app: FastAPI application
            auto_settle: Whether to automatically settle payments (default: True)
        """
        super().__init__(app)
        self.auto_settle = auto_settle
        self._facilitator_client: Optional["UnifiedFacilitatorClient"] = None

    @property
    def facilitator_client(self) -> "UnifiedFacilitatorClient":
        """Get or create facilitator client."""
        if self._facilitator_client is None:
            self._facilitator_client = get_facilitator_client()
        return self._facilitator_client

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Process request and handle payment verification."""

        # Get the route handler function by trying to match the route
        route_handler = None

        # Try to find the matching route
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                route_handler = route.endpoint

                # Check if this endpoint requires payment by function name
                func_name = getattr(route_handler, "__name__", None)
                if func_name and requires_payment_by_name(func_name):
                    break

                # Fallback: check the route endpoint directly
                if requires_payment(route_handler):
                    break

                # If not found, check if FastAPI wrapped the function
                # Look for the original function in the route's callback
                if hasattr(route, "dependant") and hasattr(route.dependant, "call"):
                    original_func = route.dependant.call
                    original_name = getattr(original_func, "__name__", None)
                    if original_name and requires_payment_by_name(original_name):
                        route_handler = original_func
                        break
                    if requires_payment(original_func):
                        route_handler = original_func
                        break

                # Continue searching if no payment required
                route_handler = None

        # If no payment required, continue normally
        if not route_handler:
            return await call_next(request)

        # Check if payment is required (by name or function)
        func_name = getattr(route_handler, "__name__", None)
        payment_required = False
        payment_config = None

        if func_name and requires_payment_by_name(func_name):
            payment_required = True
            payment_config = get_payment_config_by_name(func_name)
        elif requires_payment(route_handler):
            payment_required = True
            payment_config = get_payment_config(route_handler)

        if not payment_required or not payment_config:
            return await call_next(request)

        # Check for payment header
        payment_header = request.headers.get("X-PAYMENT")

        if not payment_header:
            # No payment provided, return 402 with requirements
            return await self._return_payment_required(request, payment_config)

        # Verify payment
        try:
            payment_requirements = self._build_payment_requirements(
                request, payment_config
            )

            verify_response = await self.facilitator_client.verify_payment(
                payment_header=payment_header,
                payment_requirements=payment_requirements,
            )

            if not verify_response.isValid:
                return JSONResponse(
                    status_code=402,
                    content={
                        "x402Version": 1,
                        "error": verify_response.error or "Payment verification failed",
                        "accepts": [payment_requirements.model_dump()],
                    },
                    headers={
                        "Content-Type": "application/json",
                    },
                )

            # Store decoded payment and requirements for settlement (like CDP does)
            request.state.payment_verified = True
            request.state.payment_id = verify_response.payment_id
            request.state.decoded_payment = self._decode_payment_header(payment_header)
            request.state.payment_requirements = payment_requirements

            # Continue to endpoint FIRST (like CDP implementation)
            response = await call_next(request)

            # Only settle if the response was successful (status < 400) and auto_settle is enabled
            if response.status_code < 400 and self.auto_settle:
                print("DEBUG: Route successful, proceeding with settlement...")
                # Use the appropriate settle method based on client type
                if hasattr(self.facilitator_client, "settle_payment_object"):
                    # Legacy FacilitatorClient
                    settle_response = (
                        await self.facilitator_client.settle_payment_object(
                            decoded_payment=request.state.decoded_payment,
                            payment_requirements=request.state.payment_requirements,
                        )
                    )
                else:
                    # CDP FacilitatorClient - uses raw header
                    settle_response = await self.facilitator_client.settle_payment(
                        payment_header=payment_header,
                        payment_requirements=request.state.payment_requirements,
                    )

                if settle_response.tx_status == "SETTLED":
                    # Payment was settled successfully - match CDP format exactly
                    payment_response = {
                        "success": True,
                        "transaction": settle_response.tx_hash,
                        "network": request.state.payment_requirements.network,
                        "payer": verify_response.payer,
                    }
                    print(
                        f"DEBUG: Settlement successful! Transaction: {settle_response.tx_hash}"
                    )
                else:
                    print(f"DEBUG: Settlement failed: {settle_response.error}")
                    # Settlement failed, but since route already executed, don't break the response
                    payment_response = {
                        "success": False,
                        "error": settle_response.error or "Settlement failed",
                    }
            elif response.status_code >= 400:
                print(
                    f"DEBUG: Route failed with status {response.status_code}, skipping settlement"
                )
                # Don't settle if route failed
                payment_response = {
                    "success": False,
                    "error": "Route execution failed, payment not settled",
                }
            else:
                # auto_settle is disabled
                payment_response = {
                    "success": True,
                    "status": "verified_only",
                    "paymentId": verify_response.payment_id,
                }

            # Add X-PAYMENT-RESPONSE header (base64 encoded JSON)
            response_json = json.dumps(payment_response)
            response_base64 = base64.b64encode(response_json.encode("utf-8")).decode(
                "utf-8"
            )
            response.headers["X-PAYMENT-RESPONSE"] = response_base64

            return response

        except Exception as e:
            # Always return 402 for payment-related errors, never 500
            return JSONResponse(
                status_code=402,
                content={
                    "x402Version": 1,
                    "error": f"Payment processing failed: {str(e)}",
                    "accepts": [
                        self._build_payment_requirements(
                            request, payment_config
                        ).model_dump()
                    ],
                },
                headers={
                    "Content-Type": "application/json",
                },
            )

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

    async def _return_payment_required(
        self,
        request: Request,
        payment_config: dict,
    ) -> JSONResponse:
        """Return 402 Payment Required with payment requirements."""

        payment_requirements = self._build_payment_requirements(request, payment_config)

        return JSONResponse(
            status_code=402,
            content={
                "x402Version": 1,
                "error": "X-PAYMENT header is required",
                "accepts": [payment_requirements.model_dump()],
            },
            headers={
                "Content-Type": "application/json",
            },
        )

    def _build_payment_requirements(
        self,
        request: Request,
        payment_config: dict,
        network: Optional[str] = None,
    ) -> PaymentRequirements:
        """Build payment requirements for the current request."""

        from .networks import get_default_asset_config, get_network_config

        config = get_config()

        # Determine which network to use
        if network:
            selected_network = network
        elif isinstance(config.network, list):
            # If multiple networks configured, use the first one as default
            # In the future, this could be based on client preferences
            selected_network = config.network[0]
        else:
            selected_network = config.network

        # Get network and asset configuration
        asset_config = get_default_asset_config(selected_network)

        # Build full resource URL (exclude query parameters like TypeScript implementation)
        resource = f"{request.url.scheme}://{request.url.netloc}{request.url.path}"

        # Convert price to atomic units based on asset decimals
        price_str = payment_config["amount"]
        if price_str.startswith("$"):
            price_float = float(price_str[1:])  # Remove $ and convert
            atomic_amount = str(int(price_float * (10**asset_config.decimals)))
        else:
            atomic_amount = str(int(float(price_str) * (10**asset_config.decimals)))

        return PaymentRequirements(
            scheme="exact",
            network=selected_network,
            maxAmountRequired=atomic_amount,
            resource=resource,
            description="",
            mimeType="",
            payTo=config.pay_to,
            maxTimeoutSeconds=payment_config.get("expires_in")
            or config.default_expires_in
            or 300,
            asset=asset_config.address,
            extra={
                "name": asset_config.eip712_name,
                "version": asset_config.eip712_version,
            },
        )

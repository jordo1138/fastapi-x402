"""Core functionality for FastAPI x402."""

import asyncio
import functools
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .facilitator import UnifiedFacilitatorClient

from dotenv import load_dotenv  # type: ignore[import-not-found]

from .models import X402Config
from .networks import (
    SupportedNetwork,
    get_default_asset_config,
    get_network_config,
    get_supported_networks,
    validate_network_asset_combination,
)

# Global configuration
_config: Optional[X402Config] = None
_endpoint_prices: Dict[str, Dict[str, Any]] = {}
_payment_required_funcs: Dict[str, Dict[str, Any]] = {}


def init_x402(
    app: Optional[Any] = None,
    pay_to: Optional[str] = None,
    network: Union[str, List[str]] = "base-sepolia",
    facilitator_url: Optional[str] = None,
    default_asset: str = "USDC",
    default_expires_in: int = 300,
    load_dotenv_file: bool = True,
    auto_add_middleware: bool = True,
) -> None:
    """Initialize global x402 configuration and optionally add middleware.

    Args:
        app: FastAPI app instance (if provided, automatically adds PaymentMiddleware)
        pay_to: Wallet address to receive payments (or set PAY_TO_ADDRESS in .env)
        network: Blockchain network(s) to support (or set X402_NETWORK in .env). Can be:
            - Single network: "base-sepolia"
            - Multiple networks: ["base", "avalanche", "iotex"]
            - "all" for all supported networks
            - "testnets" for all testnets
            - "mainnets" for all mainnets
        facilitator_url: URL of payment facilitator (or set FACILITATOR_URL in .env)
        default_asset: Default payment asset (default: USDC)
        default_expires_in: Default payment expiration in seconds
        load_dotenv_file: Whether to load .env file (default: True)
        auto_add_middleware: Whether to automatically add PaymentMiddleware when app is provided (default: True)
    """
    global _config

    # Load environment variables from .env file
    if load_dotenv_file:
        load_dotenv()

    # Get configuration from environment variables if not provided
    if pay_to is None:
        pay_to = os.getenv("PAY_TO_ADDRESS")
        if not pay_to:
            raise ValueError(
                "pay_to address is required. Set PAY_TO_ADDRESS environment variable or pass pay_to parameter."
            )

    if facilitator_url is None:
        # Check for custom facilitator URL
        facilitator_url = os.getenv("FACILITATOR_URL")

        # Leave facilitator_url as None if not explicitly set
        # The get_facilitator_client() function will auto-detect based on network type

    # Override network from environment if not provided
    env_network = os.getenv("X402_NETWORK")
    if env_network:
        network = env_network

    # Handle special network values
    if isinstance(network, str):
        if network == "all":
            networks = get_supported_networks()
        elif network == "testnets":
            from .networks import get_supported_testnets

            networks = get_supported_testnets()
        elif network == "mainnets":
            from .networks import get_supported_mainnets

            networks = get_supported_mainnets()
        else:
            # Validate single network
            get_network_config(network)  # Raises if invalid
            networks = [network]
    else:
        # Validate all networks in list
        for net in network:
            get_network_config(net)  # Raises if invalid
        networks = network

    _config = X402Config(
        pay_to=pay_to,
        network=networks[0] if len(networks) == 1 else networks,
        facilitator_url=facilitator_url,
        default_asset=default_asset,
        default_expires_in=default_expires_in,
    )

    # Automatically add PaymentMiddleware if app is provided
    if app is not None and auto_add_middleware:
        from .middleware import PaymentMiddleware

        app.add_middleware(PaymentMiddleware)


def get_config() -> X402Config:
    """Get global x402 configuration."""
    if _config is None:
        raise RuntimeError("x402 not initialized. Call init_x402() first.")
    return _config


def pay(
    amount: str,
    asset: Optional[str] = None,
    expires_in: Optional[int] = None,
) -> Callable:
    """Decorator to mark an endpoint as requiring payment.

    Args:
        amount: Payment amount (e.g., "$0.01" or "1000000")
        asset: Payment asset (defaults to global config)
        expires_in: Payment expiration in seconds (defaults to global config)

    Example:
        @pay("$0.01")
        @app.get("/thumbnail")
        def thumbnail(url: str):
            return {"thumb_url": create_thumb(url)}
    """

    def decorator(func: Callable) -> Callable:
        global _payment_required_funcs

        # Store payment metadata by function name for lookup
        func_name = func.__name__
        _payment_required_funcs[func_name] = {
            "amount": amount,
            "asset": asset,
            "expires_in": expires_in,
        }

        # Also store in the old way for compatibility
        endpoint_key = f"{func.__module__}.{func.__name__}"
        _endpoint_prices[endpoint_key] = {
            "amount": amount,
            "asset": asset,
            "expires_in": expires_in,
        }

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Use the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper

        # Mark the function as requiring payment
        wrapper._x402_payment_required = True  # type: ignore[attr-defined]
        wrapper._x402_payment_config = {  # type: ignore[attr-defined]
            "amount": amount,
            "asset": asset,
            "expires_in": expires_in,
        }

        return wrapper

    return decorator


def get_endpoint_payment_config(endpoint_key: str) -> Optional[Dict[str, Any]]:
    """Get payment configuration for an endpoint."""
    return _endpoint_prices.get(endpoint_key)


def requires_payment(func: Callable) -> bool:
    """Check if a function requires payment."""
    return hasattr(func, "_x402_payment_required") and func._x402_payment_required


def get_payment_config(func: Callable) -> Optional[Dict[str, Any]]:
    """Get payment configuration from a function."""
    return getattr(func, "_x402_payment_config", None)


def requires_payment_by_name(func_name: str) -> bool:
    """Check if a function requires payment by name."""
    return func_name in _payment_required_funcs


def get_payment_config_by_name(func_name: str) -> Optional[Dict[str, Any]]:
    """Get payment configuration by function name."""
    return _payment_required_funcs.get(func_name)


def get_supported_networks_list() -> List[str]:
    """Get list of all supported networks."""
    return get_supported_networks()


def get_config_for_network(network: str) -> Dict[str, Any]:
    """Get configuration details for a specific network."""
    network_config = get_network_config(network)
    asset_config = get_default_asset_config(network)

    return {
        "network": network_config.name,
        "chain_id": network_config.chain_id,
        "is_testnet": network_config.is_testnet,
        "default_asset": {
            "address": asset_config.address,
            "name": asset_config.name,
            "symbol": asset_config.symbol,
            "decimals": asset_config.decimals,
            "eip712": {
                "name": asset_config.eip712_name,
                "version": asset_config.eip712_version,
            },
        },
    }


def validate_payment_config(network: str, asset_address: Optional[str] = None) -> bool:
    """Validate that a network and optional asset address are supported."""
    try:
        get_network_config(network)
        if asset_address:
            return validate_network_asset_combination(network, asset_address)
        return True
    except ValueError:
        return False


def get_available_networks_for_config() -> Dict[str, Any]:
    """Get detailed information about all available networks and their assets."""
    result = {}
    for network_name in get_supported_networks():
        result[network_name] = get_config_for_network(network_name)
    return result


def get_facilitator_client() -> "UnifiedFacilitatorClient":
    """Get the unified facilitator client - auto-detects based on network and credentials."""
    config = get_config()

    # Get CDP credentials from environment
    cdp_key_id = os.getenv("CDP_API_KEY_ID")
    cdp_secret = os.getenv("CDP_API_KEY_SECRET")

    # Auto-detect facilitator based on network and credentials
    facilitator_url = config.facilitator_url

    # If facilitator_url is explicitly set in env, use it; otherwise auto-detect
    if facilitator_url is None:
        # Check if the default network is a testnet
        # Get the first network if multiple networks are configured
        network = (
            config.network if isinstance(config.network, str) else config.network[0]
        )
        network_config = get_network_config(network)

        if network_config and network_config.is_testnet:
            # Testnet -> always use x402.org gasless facilitator
            facilitator_url = "https://x402.org/facilitator"
        elif cdp_key_id and cdp_secret:
            # Mainnet with CDP credentials -> use official Coinbase facilitator
            facilitator_url = "https://api.cdp.coinbase.com"
        else:
            # Mainnet without CDP credentials -> fallback to x402.org
            facilitator_url = "https://x402.org/facilitator"
    # If facilitator_url was explicitly set, use it as-is

    from .facilitator import UnifiedFacilitatorClient

    return UnifiedFacilitatorClient(
        base_url=facilitator_url,
        cdp_api_key_id=cdp_key_id,
        cdp_api_key_secret=cdp_secret,
    )

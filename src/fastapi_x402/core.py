"""Core functionality for FastAPI x402."""

import functools
from typing import Any, Callable, Dict, List, Optional, Union

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
    pay_to: str,
    network: Union[str, List[str]] = "base-sepolia",
    facilitator_url: str = "https://x402.org/facilitator",
    default_asset: str = "USDC",
    default_expires_in: int = 300,
) -> None:
    """Initialize global x402 configuration.

    Args:
        pay_to: Wallet address to receive payments
        network: Blockchain network(s) to support. Can be:
            - Single network: "base-sepolia"
            - Multiple networks: ["base", "avalanche", "iotex"]
            - "all" for all supported networks
            - "testnets" for all testnets
            - "mainnets" for all mainnets
        facilitator_url: URL of payment facilitator
        default_asset: Default payment asset (default: USDC)
        default_expires_in: Default payment expiration in seconds
    """
    global _config

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
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

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

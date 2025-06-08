"""FastAPI x402 - One-liner pay-per-request for FastAPI endpoints."""

from .core import (
    init_x402, 
    pay, 
    get_supported_networks_list,
    get_config_for_network,
    get_available_networks_for_config,
    validate_payment_config
)
from .middleware import PaymentMiddleware
from .dependencies import payment_required
from .networks import (
    SupportedNetwork,
    get_supported_networks,
    get_supported_testnets,
    get_supported_mainnets,
    get_network_config,
    get_asset_config,
    get_default_asset_config
)

__version__ = "0.1.0"
__all__ = [
    # Core functionality
    "init_x402", 
    "pay", 
    "PaymentMiddleware",
    "payment_required",
    
    # Network information
    "get_supported_networks_list",
    "get_config_for_network", 
    "get_available_networks_for_config",
    "validate_payment_config",
    
    # Networks module
    "SupportedNetwork",
    "get_supported_networks",
    "get_supported_testnets", 
    "get_supported_mainnets",
    "get_network_config",
    "get_asset_config",
    "get_default_asset_config"
]

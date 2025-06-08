"""
Network and asset configurations for x402 payments.
Synchronized with the official Coinbase x402 facilitator supported chains and tokens.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class AssetConfig:
    """Configuration for a supported asset on a specific network."""

    address: str
    name: str
    symbol: str = "USDC"
    decimals: int = 6
    eip712_name: Optional[str] = None
    eip712_version: str = "2"

    def __post_init__(self) -> None:
        """Set default EIP712 name if not provided."""
        if self.eip712_name is None:
            self.eip712_name = self.name


@dataclass
class NetworkConfig:
    """Configuration for a supported network."""

    name: str
    chain_id: int
    is_testnet: bool = False
    assets: Optional[Dict[str, AssetConfig]] = None

    def __post_init__(self) -> None:
        """Initialize empty assets dict if not provided."""
        if self.assets is None:
            self.assets = {}


class SupportedNetwork(Enum):
    """Supported networks for x402 payments."""

    BASE_SEPOLIA = "base-sepolia"
    BASE = "base"
    AVALANCHE_FUJI = "avalanche-fuji"
    AVALANCHE = "avalanche"
    IOTEX = "iotex"


# Official x402 network configurations
# Synchronized with: /tmp/cdp-x402/typescript/packages/x402/src/types/shared/network.ts
NETWORK_CONFIGS: Dict[str, NetworkConfig] = {
    # Base Sepolia (Testnet)
    "base-sepolia": NetworkConfig(
        name="base-sepolia",
        chain_id=84532,
        is_testnet=True,
        assets={
            "usdc": AssetConfig(
                address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                name="USDC",
                symbol="USDC",
                decimals=6,
                eip712_name="USDC",
                eip712_version="2",
            )
        },
    ),
    # Base Mainnet
    "base": NetworkConfig(
        name="base",
        chain_id=8453,
        is_testnet=False,
        assets={
            "usdc": AssetConfig(
                address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                name="USDC",
                symbol="USDC",
                decimals=6,
                eip712_name="USDC",
                eip712_version="2",
            )
        },
    ),
    # Avalanche Fuji (Testnet)
    "avalanche-fuji": NetworkConfig(
        name="avalanche-fuji",
        chain_id=43113,
        is_testnet=True,
        assets={
            "usdc": AssetConfig(
                address="0x5425890298aed601595a70AB815c96711a31Bc65",
                name="USD Coin",
                symbol="USDC.e",
                decimals=6,
                eip712_name="USD Coin",
                eip712_version="2",
            )
        },
    ),
    # Avalanche Mainnet
    "avalanche": NetworkConfig(
        name="avalanche",
        chain_id=43114,
        is_testnet=False,
        assets={
            "usdc": AssetConfig(
                address="0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                name="USDC",
                symbol="USDC",
                decimals=6,
                eip712_name="USDC",
                eip712_version="2",
            )
        },
    ),
    # IoTeX
    "iotex": NetworkConfig(
        name="iotex",
        chain_id=4689,
        is_testnet=False,
        assets={
            "usdc": AssetConfig(
                address="0xcdf79194c6c285077a58da47641d4dbe51f63542",
                name="Bridged USDC",
                symbol="USDC.e",
                decimals=6,
                eip712_name="Bridged USDC",
                eip712_version="2",
            )
        },
    ),
}


def get_supported_networks() -> List[str]:
    """Get list of all supported network names."""
    return list(NETWORK_CONFIGS.keys())


def get_supported_testnets() -> List[str]:
    """Get list of supported testnet names."""
    return [name for name, config in NETWORK_CONFIGS.items() if config.is_testnet]


def get_supported_mainnets() -> List[str]:
    """Get list of supported mainnet names."""
    return [name for name, config in NETWORK_CONFIGS.items() if not config.is_testnet]


def get_network_config(network: str) -> NetworkConfig:
    """Get configuration for a specific network."""
    if network not in NETWORK_CONFIGS:
        raise ValueError(
            f"Unsupported network: {network}. Supported networks: {get_supported_networks()}"
        )
    return NETWORK_CONFIGS[network]


def get_asset_config(network: str, asset: str = "usdc") -> AssetConfig:
    """Get asset configuration for a specific network and asset."""
    network_config = get_network_config(network)
    if network_config.assets is None:
        raise ValueError(f"No assets configured for network '{network}'")
    if asset not in network_config.assets:
        available_assets = list(network_config.assets.keys())
        raise ValueError(
            f"Unsupported asset '{asset}' on network '{network}'. Available assets: {available_assets}"
        )
    return network_config.assets[asset]


def get_default_asset_config(network: str) -> AssetConfig:
    """Get default asset (USDC) configuration for a network."""
    return get_asset_config(network, "usdc")


def validate_network_asset_combination(network: str, asset_address: str) -> bool:
    """Validate that an asset address is supported on the given network."""
    try:
        network_config = get_network_config(network)
        if network_config.assets is None:
            return False
        for asset_config in network_config.assets.values():
            if asset_config.address.lower() == asset_address.lower():
                return True
        return False
    except ValueError:
        return False


# Convenience mappings for backward compatibility
CHAIN_ID_TO_NETWORK = {
    config.chain_id: name for name, config in NETWORK_CONFIGS.items()
}
NETWORK_TO_CHAIN_ID = {
    name: config.chain_id for name, config in NETWORK_CONFIGS.items()
}

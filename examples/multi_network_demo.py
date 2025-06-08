"""
FastAPI x402 Multi-Network Demo

This example shows how to accept payments across multiple blockchain networks
including Base, Avalanche, and IoTeX using different stablecoins.
"""

from fastapi import FastAPI

from fastapi_x402 import init_x402, pay
from fastapi_x402.core import (
    get_available_networks_for_config,
    get_supported_networks_list,
)

app = FastAPI(title="Multi-Network x402 API")

# Initialize x402 to support ALL networks supported by Coinbase Facilitator
init_x402(
    pay_to="0x9ecae3f1abfce10971353FD21bD8B4785473fD18",  # Your merchant wallet
    network="all",  # Support all available networks
    facilitator_url="https://x402.org/facilitator",
)


@app.get("/")
async def root():
    """Show supported networks and their configurations."""
    return {
        "message": "Multi-network x402 payment API",
        "supported_networks": get_supported_networks_list(),
        "network_details": get_available_networks_for_config(),
    }


@app.get("/free")
async def free_endpoint():
    """Free endpoint - no payment required."""
    return {"message": "This endpoint is completely free!"}


@app.get("/micro-payment")
@pay("$0.001")  # 1/10th of a cent - works on all networks
async def micro_payment():
    """Micro-payment endpoint - 0.1 cent."""
    return {
        "data": "This costs $0.001 and works on any supported network!",
        "networks_supported": get_supported_networks_list(),
    }


@app.get("/small-payment")
@pay("$0.01")  # 1 cent payment
async def small_payment():
    """Small payment endpoint."""
    return {
        "premium_data": "This costs 1 cent on any network",
        "available_on": {
            "base": "USDC",
            "base-sepolia": "USDC",
            "avalanche": "USDC",
            "avalanche-fuji": "USD Coin",
            "iotex": "Bridged USDC",
        },
    }


@app.get("/medium-payment")
@pay("$0.10")  # 10 cents
async def medium_payment():
    """Medium payment endpoint."""
    return {
        "valuable_data": "This costs 10 cents",
        "note": "Payment can be made with USDC on any supported network",
    }


@app.get("/premium-payment")
@pay("$1.00")  # $1 payment
async def premium_payment():
    """Premium payment endpoint."""
    return {
        "premium_content": "This is premium content worth $1",
        "features": [
            "Works across all supported networks",
            "Automatic settlement",
            "Replay protection",
            "Real blockchain transactions",
        ],
    }


@app.get("/networks")
async def list_networks():
    """Get detailed information about all supported networks."""
    return get_available_networks_for_config()


@app.get("/networks/{network}")
async def network_details(network: str):
    """Get details about a specific network."""
    from fastapi_x402.core import get_config_for_network, validate_payment_config

    if not validate_payment_config(network):
        return {"error": f"Network '{network}' is not supported"}

    return get_config_for_network(network)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
FastAPI x402 Multi-Option Demo

This example shows how to offer clients multiple network options
in a single 402 response, letting them choose their preferred network.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fastapi_x402 import init_x402, pay
from fastapi_x402.core import get_config_for_network

app = FastAPI(title="Multi-Option x402 API")

# Initialize with Base Sepolia as default
init_x402(
    pay_to="0x9ecae3f1abfce10971353FD21bD8B4785473fD18",
    network="base-sepolia",
    facilitator_url="https://x402.org/facilitator",
)


@app.get("/")
async def root():
    """Show available payment networks."""
    networks = ["base-sepolia", "base", "avalanche", "iotex"]
    network_info = {}

    for network in networks:
        try:
            config = get_config_for_network(network)
            network_info[network] = {
                "chain_id": config["chain_id"],
                "usdc_address": config["default_asset"]["address"],
                "is_testnet": config["is_testnet"],
            }
        except:
            pass

    return {
        "message": "Multi-option x402 payment API",
        "payment_networks_available": network_info,
        "note": "Endpoints return 402 with multiple network options",
    }


@app.get("/multi-network-choice")
async def multi_network_choice(request: Request):
    """
    Endpoint that offers multiple network payment options.
    Returns 402 with payment requirements for different networks.
    """

    # Define networks to offer
    networks_to_offer = [
        "base-sepolia",  # Testnet
        "base",  # Mainnet
        "avalanche",  # Mainnet
        "iotex",  # Mainnet
    ]

    # Build payment requirements for each network
    accepts = []
    for network in networks_to_offer:
        try:
            config = get_config_for_network(network)

            # Convert $0.01 to atomic units (1 cent = 10,000 units for 6 decimal USDC)
            atomic_amount = "10000"

            payment_requirement = {
                "scheme": "exact",
                "network": network,
                "maxAmountRequired": atomic_amount,
                "resource": f"{request.url.scheme}://{request.url.netloc}{request.url.path}",
                "description": f"Payment via {network.upper()}",
                "mimeType": "",
                "payTo": "0x9ecae3f1abfce10971353FD21bD8B4785473fD18",
                "maxTimeoutSeconds": 3600,
                "asset": config["default_asset"]["address"],
                "extra": {
                    "name": config["default_asset"]["name"],
                    "version": config["default_asset"]["eip712"]["version"],
                    "network_display": network.replace("-", " ").title(),
                    "chain_id": config["chain_id"],
                },
            }
            accepts.append(payment_requirement)
        except Exception as e:
            print(f"Failed to add {network}: {e}")
            continue

    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "error": "Payment required - choose your preferred network",
            "accepts": accepts,
            "message": f"Pay $0.01 using any of {len(accepts)} supported networks",
        },
    )


@app.get("/base-only")
@pay("$0.01")
async def base_only():
    """Endpoint that only accepts Base network payments."""
    return {
        "data": "This endpoint only accepts Base network payments",
        "network": "base-sepolia",
        "cost": "$0.01",
    }


@app.get("/specific-network/{network}")
async def specific_network(network: str, request: Request):
    """
    Endpoint that accepts payment only on a specific network.
    Shows how servers can dictate the exact network.
    """

    try:
        config = get_config_for_network(network)
    except ValueError:
        return JSONResponse(
            status_code=400, content={"error": f"Network '{network}' not supported"}
        )

    # Return 402 with ONLY this network as option
    payment_requirement = {
        "scheme": "exact",
        "network": network,
        "maxAmountRequired": "5000",  # $0.005
        "resource": f"{request.url.scheme}://{request.url.netloc}{request.url.path}",
        "description": f"Must pay on {network} network only",
        "mimeType": "",
        "payTo": "0x9ecae3f1abfce10971353FD21bD8B4785473fD18",
        "maxTimeoutSeconds": 3600,
        "asset": config["default_asset"]["address"],
        "extra": {
            "name": config["default_asset"]["name"],
            "version": config["default_asset"]["eip712"]["version"],
        },
    }

    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "error": f"Payment required on {network} network only",
            "accepts": [payment_requirement],
            "required_network": network,
            "cost": "$0.005",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

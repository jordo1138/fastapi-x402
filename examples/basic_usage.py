"""
Basic FastAPI x402 Usage Example

This example shows the simplest way to add payments to a FastAPI app.
"""

from fastapi import FastAPI

from fastapi_x402 import PaymentMiddleware, init_x402, pay

# Create FastAPI app
app = FastAPI(title="My Paid API")

# Initialize x402 (one-time setup)
init_x402(
    pay_to="0x9ecae3f1abfce10971353FD21bD8B4785473fD18",  # Your wallet address
    network="base-sepolia",  # Start with testnet
    facilitator_url="https://x402.org/facilitator",
)

# Add payment middleware
app.add_middleware(PaymentMiddleware)


@app.get("/")
async def root():
    return {"message": "Welcome to my API! Some endpoints require payment."}


@app.get("/free-data")
async def free_data():
    """Free endpoint - no payment required."""
    return {"data": "This information is free!", "cost": "$0.00"}


@app.get("/premium-data")
@pay("$0.01")  # Require 1 cent payment
async def premium_data():
    """Paid endpoint - requires payment."""
    return {
        "data": "This is premium information!",
        "cost": "$0.01",
        "network": "base-sepolia",
    }


@app.get("/expensive-data")
@pay("$0.10")  # Require 10 cent payment
async def expensive_data():
    """More expensive endpoint."""
    return {
        "data": "This is very valuable information!",
        "cost": "$0.10",
        "analysis": "High-value content worth the price",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
    # Access at: http://127.0.0.1:8000
    # Try: curl http://127.0.0.1:8000/premium-data

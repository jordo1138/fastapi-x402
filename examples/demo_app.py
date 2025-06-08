"""Demo FastAPI app with x402 payment integration."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Import our x402 package
from fastapi_x402 import PaymentMiddleware, init_x402, pay

# Create FastAPI app
app = FastAPI(
    title="FastAPI x402 Demo",
    description="Demo app showing one-liner pay-per-request functionality",
    version="0.1.0",
)

# Initialize x402 with your wallet address
# In production, use environment variables
init_x402(
    pay_to=os.getenv(
        "PAY_TO_ADDRESS", "0x9ecae3f1abfce10971353FD21bD8B4785473fD18"
    ),  # Merchant wallet (receives payments)
    facilitator_url=os.getenv(
        "FACILITATOR_URL", "https://x402.org/facilitator"
    ),  # Facilitator URL for Base Sepolia testnet
    network="base-sepolia",  # Use testnet for easier testing
)

# Add payment middleware with settlement enabled (redirects fixed)
app.add_middleware(PaymentMiddleware, auto_settle=True)


# Free endpoint (no payment required)
@app.get("/")
async def root():
    """Free welcome endpoint."""
    return {
        "message": "Welcome to FastAPI x402 Demo!",
        "paid_endpoints": [
            {
                "path": "/thumbnail",
                "price": "$0.002",
                "description": "Generate thumbnail",
            },
            {
                "path": "/premium-data",
                "price": "$0.01",
                "description": "Access premium data",
            },
            {
                "path": "/ai-summary",
                "price": "$0.05",
                "description": "AI-powered text summary",
            },
        ],
    }


# Paid endpoints using the @pay decorator
@pay("$0.002")
@app.get("/thumbnail")
async def thumbnail(url: str):
    """Generate a thumbnail for the given URL - costs $0.002."""
    # In a real app, you'd generate an actual thumbnail
    return {
        "thumbnail_url": f"https://thumbnails.example.com/thumb/{hash(url)}.jpg",
        "original_url": url,
        "generated_at": "2024-12-06T10:30:00Z",
        "cost": "$0.002",
    }


@pay("$0.01")
@app.get("/premium-data")
async def premium_data():
    """Access premium market data - costs $0.01."""
    return {
        "market_data": {
            "bitcoin": {"price": 96543.21, "change_24h": 2.34},
            "ethereum": {"price": 3842.67, "change_24h": -1.23},
            "base": {"price": 1.00, "change_24h": 0.01},
        },
        "timestamp": "2024-12-06T10:30:00Z",
        "cost": "$0.01",
    }


@pay("$0.05", asset="USDC")
@app.post("/ai-summary")
async def ai_summary(text: str):
    """Generate AI summary of text - costs $0.05."""
    if not text or len(text.strip()) < 10:
        raise HTTPException(
            status_code=400, detail="Text must be at least 10 characters"
        )

    # In a real app, you'd use an AI service
    word_count = len(text.split())
    summary = (
        f"This {word_count}-word text discusses various topics and provides insights."
    )

    return {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
        "compression_ratio": round(len(summary) / len(text), 2),
        "cost": "$0.05",
    }


# Endpoint with custom expiration (1 hour)
@pay("$0.001", expires_in=3600)
@app.get("/quick-fact")
async def quick_fact():
    """Get a quick fact (valid for 1 hour) - costs $0.001."""
    return {
        "fact": "FastAPI x402 allows you to monetize APIs with just one decorator!",
        "category": "tech",
        "expires_in": "1 hour",
        "cost": "$0.001",
    }


# Health check endpoint (free)
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fastapi-x402-demo"}


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting FastAPI x402 Demo App")
    print("💳 Payment required endpoints:")
    print("  • GET /thumbnail?url=<url> - $0.002")
    print("  • GET /premium-data - $0.01")
    print("  • POST /ai-summary - $0.05")
    print("  • GET /quick-fact - $0.001")
    print(
        "\n💡 Try calling any paid endpoint without X-PAYMENT header to see 402 response"
    )

    uvicorn.run(
        "demo_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

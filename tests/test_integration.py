"""Integration tests for fastapi-x402 package."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_x402 import init_x402, pay
from fastapi_x402.middleware import PaymentMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI app with x402 configured."""
    # Reset any existing config
    from fastapi_x402.core import _config, _payment_required_funcs

    _config = None
    _payment_required_funcs.clear()

    # Initialize x402
    init_x402(
        pay_to="0x1234567890123456789012345678901234567890",
        network="base-sepolia",
        facilitator_url="https://test.facilitator.com",
    )

    app = FastAPI()
    app.add_middleware(PaymentMiddleware)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_pay_decorator_basic(app, client):
    """Test that @pay decorator works and returns 402 without payment."""

    @app.get("/protected")
    @pay("$0.01")
    def protected_endpoint():
        return {"data": "secret content"}

    # Request without payment should return 402
    response = client.get("/protected")
    assert response.status_code == 402
    assert "application/json" in response.headers.get("content-type", "")

    # Should include payment requirements in x402 format
    data = response.json()
    assert data["x402Version"] == 1
    assert "error" in data
    assert "accepts" in data
    assert len(data["accepts"]) == 1

    payment_req = data["accepts"][0]
    assert payment_req["scheme"] == "exact"
    assert payment_req["network"] == "base-sepolia"
    assert payment_req["payTo"] == "0x1234567890123456789012345678901234567890"


def test_unprotected_endpoint_works(app, client):
    """Test that endpoints without @pay work normally."""

    @app.get("/public")
    def public_endpoint():
        return {"data": "public content"}

    response = client.get("/public")
    assert response.status_code == 200
    assert response.json() == {"data": "public content"}


def test_pay_decorator_with_different_amounts(app, client):
    """Test @pay decorator with different price formats."""

    @app.get("/cheap")
    @pay("$0.01")
    def cheap_endpoint():
        return {"data": "cheap"}

    @app.get("/expensive")
    @pay("$1.00")
    def expensive_endpoint():
        return {"data": "expensive"}

    # Both should return 402 without payment
    cheap_response = client.get("/cheap")
    expensive_response = client.get("/expensive")

    assert cheap_response.status_code == 402
    assert expensive_response.status_code == 402

    # Check different amounts in atomic units
    cheap_data = cheap_response.json()
    expensive_data = expensive_response.json()

    cheap_req = cheap_data["accepts"][0]
    expensive_req = expensive_data["accepts"][0]

    assert cheap_req["maxAmountRequired"] == "10000"  # $0.01 = 10,000 atomic units
    assert (
        expensive_req["maxAmountRequired"] == "1000000"
    )  # $1.00 = 1,000,000 atomic units


def test_multiple_protected_endpoints(app, client):
    """Test multiple endpoints with @pay decorator."""

    @app.get("/data1")
    @pay("$0.05")
    def data1():
        return {"endpoint": "data1"}

    @app.get("/data2")
    @pay("$0.10")
    def data2():
        return {"endpoint": "data2"}

    @app.get("/free")
    def free_data():
        return {"endpoint": "free"}

    # Protected endpoints should return 402
    assert client.get("/data1").status_code == 402
    assert client.get("/data2").status_code == 402

    # Free endpoint should work
    response = client.get("/free")
    assert response.status_code == 200
    assert response.json() == {"endpoint": "free"}


def test_configuration_validation():
    """Test that init_x402 validates configuration properly."""

    # Test invalid network
    with pytest.raises(ValueError, match="Unsupported network"):
        init_x402(pay_to="0x123", network="invalid-network")


def test_payment_header_structure(app, client):
    """Test that 402 response includes proper payment requirements structure."""

    @app.post("/api/submit")
    @pay("$0.25")
    def submit_data():
        return {"status": "submitted"}

    response = client.post("/api/submit")
    assert response.status_code == 402

    data = response.json()

    # Verify x402 response structure
    assert data["x402Version"] == 1
    assert "accepts" in data
    assert len(data["accepts"]) == 1

    payment_req = data["accepts"][0]

    # Verify required fields are present
    required_fields = [
        "scheme",
        "network",
        "maxAmountRequired",
        "resource",
        "payTo",
        "asset",
        "maxTimeoutSeconds",
    ]
    for field in required_fields:
        assert field in payment_req, f"Missing required field: {field}"

    # Verify values make sense
    assert "/api/submit" in payment_req["resource"]  # Should contain the path
    assert payment_req["maxAmountRequired"] == "250000"  # $0.25 in atomic units
    assert payment_req["payTo"] == "0x1234567890123456789012345678901234567890"


def test_middleware_without_decorator(app, client):
    """Test that middleware doesn't interfere with non-decorated endpoints."""

    @app.get("/health")
    def health_check():
        return {"status": "healthy"}

    @app.post("/webhook")
    def webhook():
        return {"received": True}

    # These should work normally
    assert client.get("/health").status_code == 200
    assert client.post("/webhook").status_code == 200


def test_error_handling_with_invalid_payment_header(app, client):
    """Test error handling when invalid payment header is provided."""

    @app.get("/test")
    @pay("$0.01")
    def test_endpoint():
        return {"test": True}

    # Test with invalid payment header
    response = client.get("/test", headers={"X-PAYMENT": "invalid-payment-data"})

    # Should still return 402 (payment invalid/verification failed)
    assert response.status_code == 402

"""Tests for x402 data models."""

import pytest

from fastapi_x402.models import (
    PaymentRequirements,
    SettleRequest,
    SettleResponse,
    VerifyRequest,
    VerifyResponse,
    X402Config,
)


def test_payment_requirements():
    """Test PaymentRequirements model."""
    req = PaymentRequirements(
        resource="GET /api/data",
        price="$0.01",
        asset="USDC",
        network="base-mainnet",
        expires_in=300,
        pay_to="0x123",
        facilitator="https://facilitator.example.com",
    )

    assert req.resource == "GET /api/data"
    assert req.price == "$0.01"
    assert req.asset == "USDC"
    assert req.network == "base-mainnet"
    assert req.expires_in == 300
    assert req.pay_to == "0x123"
    assert req.facilitator == "https://facilitator.example.com"


def test_payment_requirements_defaults():
    """Test PaymentRequirements with default values."""
    req = PaymentRequirements(
        resource="GET /api/data",
        price="$0.01",
        pay_to="0x123",
        facilitator="https://facilitator.example.com",
    )

    assert req.asset == "USDC"  # default
    assert req.network == "base-mainnet"  # default
    assert req.expires_in == 300  # default


def test_verify_request():
    """Test VerifyRequest model."""
    payment_req = PaymentRequirements(
        resource="GET /api/data",
        price="$0.01",
        pay_to="0x123",
        facilitator="https://facilitator.example.com",
    )

    req = VerifyRequest(
        payment_header="payment_header_value",
        payment_requirements=payment_req,
    )

    assert req.payment_header == "payment_header_value"
    assert req.payment_requirements == payment_req


def test_verify_response_success():
    """Test successful VerifyResponse."""
    resp = VerifyResponse(
        is_valid=True,
        payment_id="payment_123",
    )

    assert resp.is_valid is True
    assert resp.payment_id == "payment_123"
    assert resp.error is None


def test_verify_response_error():
    """Test error VerifyResponse."""
    resp = VerifyResponse(
        is_valid=False,
        error="Invalid payment signature",
    )

    assert resp.is_valid is False
    assert resp.payment_id is None
    assert resp.error == "Invalid payment signature"


def test_settle_request():
    """Test SettleRequest model."""
    req = SettleRequest(payment_id="payment_123")
    assert req.payment_id == "payment_123"


def test_settle_response_success():
    """Test successful SettleResponse."""
    resp = SettleResponse(
        tx_status="SETTLED",
        tx_hash="0xabc123",
    )

    assert resp.tx_status == "SETTLED"
    assert resp.tx_hash == "0xabc123"
    assert resp.error is None


def test_settle_response_error():
    """Test error SettleResponse."""
    resp = SettleResponse(
        tx_status="FAILED",
        error="Insufficient funds",
    )

    assert resp.tx_status == "FAILED"
    assert resp.tx_hash is None
    assert resp.error == "Insufficient funds"


def test_x402_config():
    """Test X402Config model."""
    config = X402Config(
        pay_to="0x123",
        network="base-testnet",
        facilitator_url="https://test.facilitator.com",
        default_asset="DAI",
        default_expires_in=600,
    )

    assert config.pay_to == "0x123"
    assert config.network == "base-testnet"
    assert config.facilitator_url == "https://test.facilitator.com"
    assert config.default_asset == "DAI"
    assert config.default_expires_in == 600


def test_x402_config_defaults():
    """Test X402Config with default values."""
    config = X402Config(pay_to="0x123")

    assert config.pay_to == "0x123"
    assert config.network == "base-mainnet"  # default
    assert config.facilitator_url == "https://facilitator.cdp.coinbase.com"  # default
    assert config.default_asset == "USDC"  # default
    assert config.default_expires_in == 300  # default

"""Tests for x402 data models - focusing on real-world usage."""

import pytest

from fastapi_x402.models import (
    PaymentRequirements,
    SettleResponse,
    VerifyRequest,
    VerifyResponse,
    X402Config,
)


def test_payment_requirements_from_real_402_response():
    """Test PaymentRequirements with realistic data from a 402 response."""
    req = PaymentRequirements(
        scheme="exact",
        network="base-sepolia",
        maxAmountRequired="10000",  # $0.01 USDC in atomic units
        resource="GET /api/data?user=123",
        description="Payment required for premium API access",
        payTo="0x1234567890123456789012345678901234567890",
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
        maxTimeoutSeconds=300,
    )

    # Test that JSON serialization works (for 402 responses)
    json_data = req.model_dump()
    assert json_data["scheme"] == "exact"
    assert json_data["maxAmountRequired"] == "10000"
    assert json_data["payTo"] == "0x1234567890123456789012345678901234567890"


def test_verify_response_parsing():
    """Test parsing VerifyResponse from facilitator service."""
    # Simulate successful verification response
    success_resp = VerifyResponse(
        isValid=True,
        payment_id="payment_abc123",
        payer="0x9876543210987654321098765432109876543210",
    )

    assert success_resp.isValid is True
    assert success_resp.payment_id == "payment_abc123"
    assert success_resp.payer == "0x9876543210987654321098765432109876543210"

    # Simulate failed verification response
    failed_resp = VerifyResponse(isValid=False, error="Invalid signature")

    assert failed_resp.isValid is False
    assert failed_resp.error == "Invalid signature"
    assert failed_resp.payment_id is None


def test_settle_response_parsing():
    """Test parsing SettleResponse from facilitator service."""
    # Successful settlement
    success_resp = SettleResponse(
        success=True,
        transaction="0xabc123def456789...",
        payer="0x9876543210987654321098765432109876543210",
        network="base-sepolia",
    )

    assert success_resp.success is True
    assert success_resp.tx_status == "SETTLED"  # computed property
    assert success_resp.tx_hash == "0xabc123def456789..."  # computed property
    assert success_resp.error is None  # computed property

    # Failed settlement
    failed_resp = SettleResponse(
        success=False, errorReason="Insufficient funds", network="base-sepolia"
    )

    assert failed_resp.success is False
    assert failed_resp.tx_status == "FAILED"  # computed property
    assert failed_resp.error == "Insufficient funds"  # computed property
    assert failed_resp.tx_hash is None  # computed property


def test_x402_config_realistic():
    """Test X402Config with realistic production values."""
    # Single network config
    config = X402Config(
        pay_to="0x1234567890123456789012345678901234567890",
        network="base-sepolia",
        facilitator_url="https://x402.org/facilitator",
    )

    assert config.pay_to == "0x1234567890123456789012345678901234567890"
    assert config.network == "base-sepolia"
    assert config.facilitator_url == "https://x402.org/facilitator"

    # Multi-network config
    multi_config = X402Config(
        pay_to="0x1234567890123456789012345678901234567890",
        network=["base-sepolia", "base"],
        facilitator_url="https://x402.org/facilitator",
    )

    assert multi_config.network == ["base-sepolia", "base"]


def test_verify_request_construction():
    """Test constructing VerifyRequest for facilitator API calls."""
    payment_req = PaymentRequirements(
        scheme="exact",
        network="base-sepolia",
        maxAmountRequired="10000",
        resource="GET /api/data",
        payTo="0x123",
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    )

    verify_req = VerifyRequest(
        x402Version=1,
        paymentPayload={
            "signature": "0x1234...",
            "amount": "10000",
            "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        },
        paymentRequirements=payment_req,
    )

    assert verify_req.x402Version == 1
    assert "signature" in verify_req.paymentPayload
    assert verify_req.paymentRequirements.maxAmountRequired == "10000"

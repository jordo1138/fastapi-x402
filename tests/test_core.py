"""Tests for core x402 functionality."""

import pytest
from fastapi import FastAPI

from fastapi_x402 import init_x402, pay
from fastapi_x402.core import get_config, get_payment_config, requires_payment


def test_init_x402():
    """Test x402 initialization."""
    init_x402(
        pay_to="0x123",
        network="base-sepolia",
        facilitator_url="https://test.facilitator.com",
    )

    config = get_config()
    assert config.pay_to == "0x123"
    assert config.network == "base-sepolia"
    assert config.facilitator_url == "https://test.facilitator.com"


def test_pay_decorator():
    """Test @pay decorator functionality."""

    @pay("$0.01", asset="USDC")
    def test_endpoint():
        return {"message": "paid content"}

    # Check if payment is required
    assert requires_payment(test_endpoint)

    # Check payment configuration
    config = get_payment_config(test_endpoint)
    assert config["amount"] == "$0.01"
    assert config["asset"] == "USDC"


def test_pay_decorator_defaults():
    """Test @pay decorator with default values."""

    @pay("$0.001")
    def test_endpoint():
        return {"message": "paid content"}

    config = get_payment_config(test_endpoint)
    assert config["amount"] == "$0.001"
    assert config["asset"] is None  # Should use global default
    assert config["expires_in"] is None  # Should use global default


def test_function_without_payment():
    """Test function without payment requirement."""

    def free_endpoint():
        return {"message": "free content"}

    assert not requires_payment(free_endpoint)
    assert get_payment_config(free_endpoint) is None


def test_config_not_initialized():
    """Test error when config not initialized."""
    # Reset global config
    import fastapi_x402.core as core

    core._config = None

    with pytest.raises(RuntimeError, match="x402 not initialized"):
        get_config()

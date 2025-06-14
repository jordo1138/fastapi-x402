"""Data models for x402 payments."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class PaymentRequirements(BaseModel):
    """Payment requirements returned in 402 responses (x402 spec format)."""

    scheme: str = "exact"
    network: str = "base-sepolia"
    maxAmountRequired: str  # Amount in atomic units
    resource: str  # Full URL
    description: str = ""
    mimeType: str = "application/json"
    payTo: str
    maxTimeoutSeconds: int = 60
    asset: str  # Asset contract address
    extra: Optional[dict] = {"name": "USD Coin", "version": "2"}
    # outputSchema is optional and should be omitted if not provided

    class Config:
        exclude_none = True  # Exclude None values from JSON output


class VerifyRequest(BaseModel):
    """Request to verify payment with facilitator."""

    x402Version: int
    paymentPayload: dict  # The decoded payment object
    paymentRequirements: PaymentRequirements


class VerifyResponse(BaseModel):
    """Response from payment verification."""

    isValid: bool
    payment_id: Optional[str] = None
    error: Optional[str] = None
    payer: Optional[str] = None


class SettleResponse(BaseModel):
    """Response from payment settlement."""

    success: bool
    errorReason: Optional[str] = None
    payer: Optional[str] = None
    transaction: Optional[str] = None
    network: Optional[str] = None

    # Computed property for backward compatibility
    @property
    def tx_status(self) -> str:
        return "SETTLED" if self.success else "FAILED"

    @property
    def tx_hash(self) -> Optional[str]:
        return self.transaction

    @property
    def error(self) -> Optional[str]:
        return self.errorReason

    class Config:
        allow_population_by_field_name = True


class X402Config(BaseModel):
    """Global x402 configuration."""

    pay_to: str
    network: Union[str, List[str]] = (
        "base-sepolia"  # Support single or multiple networks
    )
    facilitator_url: Optional[str] = None
    default_asset: str = "USDC"
    default_expires_in: int = 300

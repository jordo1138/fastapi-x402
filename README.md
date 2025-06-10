# FastAPI x402

**One-liner cryptocurrency payments for FastAPI endpoints using the x402 protocol.**

Transform any FastAPI endpoint into a paid API with just a single decorator. Accept stablecoin payments (USDC) on Base network with automatic settlement.

```python
from fastapi import FastAPI
from fastapi_x402 import init_x402, pay

app = FastAPI()
init_x402(app, pay_to="0x...", facilitator_url="https://x402.org/facilitator")

@app.get("/premium-data")
@pay("$0.01")  # Require 1 cent payment
async def get_premium_data():
    return {"data": "This costs $0.01 to access!"}
```

## 🚀 Features

- **🔒 Pay-per-request**: Monetize individual API calls
- **🌐 Multi-network support**: Accept payments on Base, Avalanche, and IoTeX
- **💰 Stablecoin payments**: Accept USDC across all supported networks
- **⚡ Real-time settlement**: Automatic blockchain settlement
- **🛡️ Replay protection**: Cryptographic payment verification
- **📝 Standard protocol**: Built on the [x402 payment standard](https://x402.org)
- **🔧 One-line integration**: Just add `@pay("$0.01")` to any endpoint
- **🔄 Auto-sync**: Stays synchronized with Coinbase Facilitator supported networks
- **🎯 Network control**: Server dictates which networks clients can use for payment

## 📦 Installation

```bash
pip install fastapi-x402
```

## 🎯 Quick Start

### 1. Environment Setup

Create a `.env` file in your project root:

```bash
# Required: Your merchant wallet address  
PAY_TO_ADDRESS=0x1234567890123456789012345678901234567890

# For testnet development (default)
# Uses public x402.org facilitator - no additional setup needed

# For mainnet production (requires Coinbase CDP)
# CDP_API_KEY_ID=your_cdp_api_key_id
# CDP_API_KEY_SECRET=your_cdp_api_secret
```

### 2. Basic FastAPI Integration

```python
from fastapi import FastAPI
from fastapi_x402 import init_x402, pay

app = FastAPI()

# Initialize x402 (loads from .env and adds middleware automatically)
init_x402(app, network="base-sepolia")  # or "base" for mainnet

@app.get("/free")
async def free_endpoint():
    return {"message": "This endpoint is free!"}

@app.get("/premium")
@pay("$0.01")  # Require 1 cent payment
async def premium_endpoint():
    return {"data": "This cost 1 cent to access!"}

@app.get("/expensive")
@pay("$1.00")  # Require $1 payment  
async def expensive_endpoint():
    return {"premium_data": "This is worth $1!"}
```

### 3. Run Your Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Test the Payment Flow

**Without payment (gets 402 response):**
```bash
curl http://localhost:8000/paid-endpoint
```

**With payment (success):**
```bash
curl -H "X-PAYMENT: eyJ4NDAyVmVyc2lvbiI6..." http://localhost:8000/paid-endpoint
```

## 💳 Client Integration

### JavaScript/TypeScript
```javascript
import { X402Client } from '@x402/client';

const client = new X402Client({
  network: 'base-sepolia',
  privateKey: 'your-wallet-private-key'
});

const response = await client.get('http://localhost:8000/paid-endpoint');
console.log(response.data); // Automatically handles payment
```

### Python
```python
import httpx
from x402_client import X402Client  # Coming soon

client = X402Client(network='base-sepolia', private_key='...')
response = await client.get('http://localhost:8000/paid-endpoint')
```

## 🔧 Configuration

### Environment Variables (.env file)

```bash
# Required
PAY_TO_ADDRESS=0x1234567890123456789012345678901234567890

# Optional: Network configuration
X402_NETWORK=base-sepolia                    # Single network
# X402_NETWORK=base,avalanche,iotex          # Multiple networks  
# X402_NETWORK=mainnets                      # All mainnets
# X402_NETWORK=testnets                      # All testnets

# Optional: Custom facilitator (advanced)
# FACILITATOR_URL=https://your-facilitator.com

# Required for mainnet production
# CDP_API_KEY_ID=your_coinbase_cdp_api_key_id
# CDP_API_KEY_SECRET=your_coinbase_cdp_api_secret
```

### Testnet vs Mainnet Setup

**🧪 Testnet Development (Default)**
```python
# .env
PAY_TO_ADDRESS=0x...
X402_NETWORK=base-sepolia

# main.py
init_x402(app)  # Uses public facilitator, no API keys needed
```

**🚀 Mainnet Production**
```python
# .env  
PAY_TO_ADDRESS=0x...
X402_NETWORK=base                 # or avalanche, iotex
CDP_API_KEY_ID=your_key_id
CDP_API_KEY_SECRET=your_secret

# main.py
init_x402(app)  # Auto-detects CDP credentials for mainnet
```

### Multi-Network Configuration
```python
from fastapi_x402 import init_x402

# Support all available networks
init_x402(app, network="all")  # Accepts payments on Base, Avalanche, and IoTeX

# Support specific networks
init_x402(app, network=["base", "avalanche"])  # Multiple networks

# Network shortcuts
init_x402(app, network="testnets")   # Base Sepolia + Avalanche Fuji
init_x402(app, network="mainnets")   # Base + Avalanche + IoTeX mainnet
```

### Manual Configuration (No .env)
```python
# Direct parameter passing (overrides .env)
init_x402(
    app,
    pay_to="0x...",
    network="base-sepolia", 
    facilitator_url="https://x402.org/facilitator"
)
```

### Network Information
```python
from fastapi_x402 import get_supported_networks_list, get_config_for_network

# List all supported networks
networks = get_supported_networks_list()
print(networks)  # ['base-sepolia', 'base', 'avalanche-fuji', 'avalanche', 'iotex']

# Get configuration for a specific network
config = get_config_for_network("base")
print(config["default_asset"]["address"])  # 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
```

## 🎯 Network Control Patterns

Your API can control which networks clients can use to pay:

### 1. **Single Network (Server Dictates)**
```python
# Only accept Base network payments
init_x402(app, pay_to="0x...", network="base")

@pay("$0.01")
@app.get("/base-only")
def base_only():
    return {"data": "Must pay with Base USDC"}
```
**402 Response:** Client MUST pay on Base network
```json
{"accepts": [{"network": "base", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}]}
```

### 2. **Multiple Options (Client Chooses)**
```python
# Accept payments from multiple networks
init_x402(app, pay_to="0x...", network=["base", "avalanche", "iotex"])

@pay("$0.01")  
@app.get("/multi-choice")
def multi_choice():
    return {"data": "Pay with any supported network"}
```
**402 Response:** Client can choose from multiple networks
```json
{"accepts": [
  {"network": "base", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
  {"network": "avalanche", "asset": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"},
  {"network": "iotex", "asset": "0xcdf79194c6c285077a58da47641d4dbe51f63542"}
]}
```

### 3. **Network-Specific Endpoints**
```python
@app.get("/pay-with-avalanche")
async def avalanche_only(request: Request):
    # Custom 402 response for Avalanche only
    return JSONResponse(status_code=402, content={
        "accepts": [{"network": "avalanche", "asset": "0xB97..."}]
    })
```

### 4. **Dynamic Network Selection**
```python
@app.get("/premium/{network}")
def network_specific(network: str):
    if network not in ["base", "avalanche"]:
        raise HTTPException(400, "Network not supported")
    # Endpoint accepts payment only on specified network
```

## 📋 API Reference

### `init_x402(app, merchant_wallet, facilitator_url=None, config=None)`

Initialize x402 middleware for your FastAPI app.

**Parameters:**
- `app` (FastAPI): Your FastAPI application instance
- `merchant_wallet` (str): Your wallet address to receive payments
- `facilitator_url` (str, optional): Custom facilitator URL
- `config` (X402Config, optional): Advanced configuration

### `@pay(amount)`

Decorator to require payment for an endpoint.

**Parameters:**
- `amount` (str): Payment amount (e.g., "$0.01", "$1.00")

**Returns:**
- HTTP 402 if no valid payment provided
- HTTP 200 with settlement info if payment valid

## 🌐 Networks & Assets

### Supported Networks
- **Base Sepolia** (testnet) - `base-sepolia`
- **Base Mainnet** - `base`
- **Avalanche Fuji** (testnet) - `avalanche-fuji`
- **Avalanche Mainnet** - `avalanche`
- **IoTeX Mainnet** - `iotex`

### Supported Assets
All networks support USDC with automatic configuration:
- **Base Sepolia**: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- **Base Mainnet**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Avalanche Fuji**: `0x5425890298aed601595a70AB815c96711a31Bc65`
- **Avalanche Mainnet**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **IoTeX**: `0xcdf79194c6c285077a58da47641d4dbe51f63542`

## 🔑 Coinbase CDP Setup (Mainnet)

To accept payments on mainnet networks, you need Coinbase Developer Platform (CDP) credentials:

### 1. Create CDP Account
1. Go to [Coinbase Developer Platform](https://www.coinbase.com/cloud)
2. Sign up for a CDP account
3. Navigate to API Keys section

### 2. Generate API Keys
1. Create a new API key pair
2. Download and securely store your credentials
3. Note your `API Key ID` and `API Secret`

# For mainnet production (requires Coinbase CDP)
# CDP_API_KEY_ID=[REDACTED:api-key]
# CDP_API_KEY_SECRET=[REDACTED:api-key]

> **Note**: Based on the official Coinbase x402 Python implementation, facilitator requests use simple HTTP without authentication headers. CDP credentials may be stored for future use but are not currently required for facilitator API calls.

### 3. Add to Environment
```bash
# .env
PAY_TO_ADDRESS=0x...
CDP_API_KEY_ID=your_api_key_id_here
CDP_API_KEY_SECRET=your_api_secret_here
X402_NETWORK=base  # or avalanche, iotex
```

### 4. Initialize for Mainnet
```python
# Automatically detects CDP credentials and enables mainnet
init_x402(app, network="mainnets")  # Supports Base, Avalanche, IoTeX
```

**Why CDP?** Mainnet payment settlement requires authenticated access to blockchain infrastructure. CDP provides reliable, scalable blockchain access with the security needed for production applications.

**Note**: Based on the official Coinbase x402 Python implementation, facilitator requests currently use simple HTTP without authentication headers. CDP credentials may be stored for future use but are not currently required for facilitator API calls.

## 🧪 Testing

### Run Tests
```bash
# Install dev dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=fastapi_x402
```

### Test on Base Sepolia
1. Get testnet USDC from [Base Sepolia faucet](https://faucet.quicknode.com/base/sepolia)
2. Set up test wallet with CDP SDK
3. Use the test client examples in `/examples`

## 🔐 Security

- **Replay Protection**: Each payment can only be used once
- **Cryptographic Verification**: All payments are cryptographically signed
- **Timeout Protection**: Payments expire after specified timeout
- **Facilitator Validation**: Third-party validation of payment authenticity

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
git clone https://github.com/jordo1138/fastapi-x402.git
cd fastapi-x402
pip install -e .[dev]
pre-commit install
```

## 📚 Examples

Check out the `/examples` directory for:
- Basic server setup
- Client integration examples
- Advanced configuration
- Testing utilities

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/jordo1138/fastapi-x402/issues)
- **Documentation**: [x402 protocol docs](https://x402.org)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the [x402 payment standard](https://x402.org)
- Powered by [Base](https://base.org) and [Coinbase CDP](https://coinbase.com/cloud)
- Inspired by [FastAPI](https://fastapi.tiangolo.com)'s elegant API design

---

**Ready to monetize your APIs? Install fastapi-x402 and start earning in minutes! 🚀**

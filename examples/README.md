# FastAPI x402 Examples

This directory contains practical examples of using `fastapi-x402` in real applications.

## Examples

### 📚 **basic_usage.py**
The simplest possible integration - great for getting started.
```bash
python examples/basic_usage.py
# Visit: http://127.0.0.1:8000/premium-data
```

### 🚀 **demo_app.py** 
Production-ready example with multiple endpoints and real testnet integration.
```bash
FACILITATOR_URL=https://x402.org/facilitator python examples/demo_app.py
# Visit: http://127.0.0.1:8000
```

### 🌐 **multi_network_demo.py**
Shows multi-network support across Base, Avalanche, and IoTeX.
```bash
python examples/multi_network_demo.py
# Visit: http://127.0.0.1:8000/networks
```

### 🎯 **multi_option_demo.py**
Advanced example showing how to offer clients multiple network payment options.
```bash
python examples/multi_option_demo.py
# Visit: http://127.0.0.1:8001/multi-network-choice
```

## Testing with Real Payments

To test with actual cryptocurrency payments:

1. **Get testnet USDC** from [Base Sepolia faucet](https://faucet.quicknode.com/base/sepolia)
2. **Use a TypeScript x402 client** or build your own
3. **Make payments** to the running endpoints

All examples use **Base Sepolia testnet** by default for safe testing.

## Production Usage

For production, change the network to mainnet:
```python
init_x402(
    pay_to="0x...",
    network="base",  # Use mainnet
    facilitator_url="https://x402.org/facilitator"
)
```

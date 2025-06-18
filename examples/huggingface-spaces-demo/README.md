# x402 AI Demo for Hugging Face Spaces

A demo application showcasing pay-per-use AI services using FastAPI and fastapi-x402.

## Features

- 💭 **Text Generation** - $0.01 per request using DistilGPT-2
- 😊 **Sentiment Analysis** - $0.005 per request using RoBERTa  
- 🔄 **Real x402 payments** with MetaMask support
- 🚀 **Lightweight models** optimized for quick loading

## Local Testing

### Option 1: Standard Python Setup

```bash
# Clone and setup
git clone https://github.com/jordo1138/fastapi-x402
cd fastapi-x402/examples/huggingface-spaces-demo

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your wallet address

# Run the app
python app.py
```

### Option 2: With Ollama (Alternative)

For even lighter local testing, you could replace the HuggingFace models with Ollama:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a small model
ollama pull phi3:mini

# Modify app.py to use Ollama API instead of transformers
```

### Option 3: CPU-Only Mode

The app automatically detects if CUDA is available and falls back to CPU. Models chosen are lightweight enough for CPU inference.

## Models Used

- **DistilGPT-2**: Distilled version of GPT-2, 82M parameters (6x smaller than GPT-2)
- **Twitter-RoBERTa-Base-Sentiment**: Fine-tuned RoBERTa for sentiment analysis

## Testing the Payment Flow

1. **Start the server**: `python app.py`
2. **Open browser**: `http://localhost:7860`
3. **Try without payment**: You'll get a 402 Payment Required response
4. **Use x402 client**: Try the [demo website](../demo-website/) with MetaMask

## Deployment to Hugging Face Spaces

1. Create a new Space with "FastAPI" template
2. Upload these files to your Space repository
3. Add secrets in Space settings:
   - `PAY_TO_ADDRESS`: Your wallet address
   - `X402_NETWORK`: `base-sepolia` for testnet
4. Your Space will automatically build and deploy

## Performance Notes

- **Model Loading**: ~30-60 seconds on CPU, ~10-20 seconds on GPU
- **Memory Usage**: ~2-4GB RAM for both models
- **Inference Speed**: 
  - Text generation: ~2-5 seconds on CPU
  - Sentiment analysis: ~1-2 seconds on CPU

## Customization

Want different models? Easy to swap:

```python
# Replace DistilGPT-2 with other text models:
text_generator = pipeline("text-generation", model="microsoft/DialoGPT-small")

# Or use different tasks:
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
```

## Architecture

```
User Request → FastAPI → x402 Middleware → 402 Payment Required
                ↓
User Payment → x402 Verification → AI Model → Response
```

The x402 middleware automatically handles payment verification before allowing access to the AI services.

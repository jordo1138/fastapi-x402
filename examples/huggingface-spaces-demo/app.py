"""
FastAPI x402 Demo for Hugging Face Spaces
A pay-per-use AI service with lightweight models
"""

import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import pipeline

# Load environment variables
load_dotenv()

# Initialize FastAPI and x402
from fastapi_x402 import init_x402, pay

app = FastAPI(title="x402 AI Demo", description="Pay-per-use AI services")

# Add CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize x402 with testnet for demo
init_x402(app, network=os.getenv("X402_NETWORK", "base-sepolia"))

# Setup templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Load lightweight AI models
print("🤖 Loading AI models...")

# Use DistilGPT-2 - much smaller than GPT-2 but still capable
text_generator = pipeline(
    "text-generation", 
    model="distilgpt2",
    device=0 if torch.cuda.is_available() else -1
)

# Use a simple sentiment analysis model as second service
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    device=0 if torch.cuda.is_available() else -1
)

print("✅ Models loaded successfully!")

# Request models
class TextRequest(BaseModel):
    prompt: str

class SentimentRequest(BaseModel):
    text: str

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main demo page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "models_loaded": True}

@app.post("/generate-text")
@pay("$0.01")  # 1 cent for text generation
async def generate_text(request: TextRequest):
    """Generate text using DistilGPT-2"""
    try:
        print(f"💭 Generating text for: '{request.prompt}'")
        
        result = text_generator(
            request.prompt, 
            max_new_tokens=50,
            num_return_sequences=1,
            temperature=0.8,
            do_sample=True,
            pad_token_id=text_generator.tokenizer.eos_token_id
        )[0]['generated_text']
        
        return {"result": result, "model": "distilgpt2"}
    except Exception as e:
        print(f"❌ Text generation error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/analyze-sentiment")
@pay("$0.005")  # Half cent for sentiment analysis
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment using RoBERTa"""
    try:
        print(f"😊 Analyzing sentiment for: '{request.text}'")
        
        result = sentiment_analyzer(request.text)[0]
        
        return {
            "text": request.text,
            "sentiment": result["label"],
            "confidence": round(result["score"], 3),
            "model": "twitter-roberta-base-sentiment"
        }
    except Exception as e:
        print(f"❌ Sentiment analysis error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check x402 configuration"""
    from fastapi_x402.core import get_config, get_facilitator_client
    
    config = get_config()
    facilitator = get_facilitator_client()
    
    return {
        "network": config.network,
        "facilitator_url": facilitator.base_url,
        "is_coinbase_cdp": facilitator.is_coinbase_cdp,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "models": ["distilgpt2", "twitter-roberta-base-sentiment"]
    }

if __name__ == "__main__":
    import uvicorn
    # Disable uvloop to avoid async context issues, use standard asyncio instead
    uvicorn.run(app, host="0.0.0.0", port=7860, loop="asyncio")

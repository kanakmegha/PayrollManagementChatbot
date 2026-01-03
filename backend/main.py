import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()
app = FastAPI()

# Enable CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from Environment Variables
HF_TOKEN = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """
    Generates vector embeddings for the user's question.
    Uses the standard Inference API for embedding models.
    """
    # Use the standard api-inference for embeddings (Router is mainly for Chat)
    url = "https://api-inference.huggingface.co/models/BAAI/bge-small-en-v1.5"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if not response.ok:
        print(f"Embedding Error: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    # Handle both list of floats and list of lists formats
    return data[0] if isinstance(data, list) and isinstance(data[0], list) else data

def search_supabase(embedding):
    """
    Searches Supabase for relevant payroll data using vector similarity.
    """
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.3,
        "match_count": 10
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json() if response.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Generate Embedding
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Failed to generate text embeddings. Please check your HF token."}

        # 2. Retrieve Context from Supabase
        matches = search_supabase(vector)
        context = "\n".join([m["content"] for m in matches]) if matches else "No relevant payroll records found."

        # 3. Generate Answer using the HF Router (OpenAI Compatible Format)
        # Fix: The Router endpoint requires /v1/chat/completions for POST requests
        llm_url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }

        # The Router requires the Chat "messages" format to bypass CloudFront 403 blocks
        payload = {
            "model": "meta-llama/Llama-3.2-1B-Instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": f"You are a helpful payroll assistant. Use the following context to answer the user: {context}"
                },
                {
                    "role": "user", 
                    "content": request_data.question
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "stream": False 
        }

        response = requests.post(llm_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            # Extract content from the OpenAI-style response structure
            answer = result['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        else:
            # Catching specific errors from the Router
            return {"status": "error", "message": f"LLM Router Error: {response.status_code} - {response.text}"}

    except Exception as e:
        return {"status": "error", "message": f"Server Error: {str(e)}"}
import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Generates embeddings using OpenRouter's OpenAI-compatible API."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/text-embedding-3-small", # Efficient and cheap
        "input": text
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()['data'][0]['embedding']
        print(f"Embedding Error: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"Embedding Exception: {str(e)}")
        return None

def search_supabase(embedding):
    """Retrieves relevant context from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.3,
        "match_count": 5
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.json() if res.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get Vector
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Failed to generate embedding via OpenRouter."}

        # 2. Search Context
        matches = search_supabase(vector)
        context = "\n".join([m["content"] for m in matches]) if matches else "No data."

        # 3. Chat via OpenRouter
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://render.com", # Optional for OpenRouter rankings
            "X-Title": "Payroll Assistant"
        }
        
        payload = {
            "model": "meta-llama/llama-3.2-3b-instruct", # Powerful & very cheap on OpenRouter
            "messages": [
                {"role": "system", "content": f"You are a payroll assistant. Context: {context}"},
                {"role": "user", "content": request_data.question}
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"OpenRouter Error: {response.text}"}

    except Exception as e:
        return {"status": "error", "message": f"Server Error: {str(e)}"}
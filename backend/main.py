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
HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Hugging Face Chat Model (Fast & Free)
# Use the Router URL for speed and reliability
# --- THE 404 FIX ---
# Use the direct model endpoint which is most stable for Mistral
HF_MODEL_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
# The rest of your code remains the same!

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Uses OpenRouter for 1536-dimension embeddings (keeps your DB compatible)."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": "openai/text-embedding-3-small", "input": text}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        return res.json()['data'][0]['embedding'] if res.status_code == 200 else None
    except:
        return None

def search_supabase_vectors(embedding):
    """Searches Supabase and returns results sorted by ID (newest first)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query_embedding": embedding, "match_threshold": 0.2, "match_count": 10}
    res = requests.post(url, headers=headers, json=payload)
    results = res.json() if res.ok else []
    
    # SORT BY ID: Ensures the '7 employee' update is prioritized over old data
    results.sort(key=lambda x: x.get('id', 0), reverse=True)
    return results

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get Embedding (OpenRouter)
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Search service unavailable."}

        # 2. Search Database (Supabase)
        matches = search_supabase_vectors(vector)
        final_context = "\n".join([m['content'] for m in matches])

        # 3. New HF Router Request (OpenAI Format)
        headers = {
            "Authorization": f"Bearer {HF_TOKEN.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": [
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": f"Context: {final_context}\n\nQuestion: {request_data.question}"}
            ],
            "max_tokens": 500,
            "stream": False
        }

        # Use the NEW Router URL
        res = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions", 
            headers=headers, 
            json=payload, 
            timeout=20
        )

        if res.status_code == 200:
            result = res.json()
            # Extract the answer from the new OpenAI-style response format
            answer = result['choices'][0]['message']['content'].strip()
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"HF Router Error: {res.status_code} - {res.text}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
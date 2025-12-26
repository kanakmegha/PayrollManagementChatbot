import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_API_KEY")

class Query(BaseModel):
    question: str

def get_embedding(text):
    """Call Hugging Face directly using requests"""
    url = "https://router.huggingface.co/v1/embeddings"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {"input": text, "model": "sentence-transformers/all-MiniLM-L6-v2"}
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()["data"][0]["embedding"]

def search_supabase(embedding):
    """Call Supabase RPC directly using requests"""
    # Note: 'rpc/match_documents' matches the function name you created in SQL
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.5,
        "match_count": 5
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

@app.post("/chat")
async def chat(q: Query):
    try:
        # 1. Get embedding
        emb = get_embedding(q.question)
        
        # 2. Get context from Supabase
        matches = search_supabase(emb)
        context = "\n".join([m["content"] for m in matches])
        
        # 3. Get answer from GPT-OSS 120B
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "model": "openai/gpt-oss-120b:fireworks-ai",
            "messages": [
                {"role": "system", "content": f"Use this context: {context}"},
                {"role": "user", "content": q.question}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return {"answer": response.json()["choices"][0]["message"]["content"]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/")
async def root():
    return {"status": "Payroll AI is online"}
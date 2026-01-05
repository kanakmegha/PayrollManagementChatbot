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
        # 1. Get 1536-dim Embedding from OpenRouter
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Embedding service failed."}

        # 2. Search Database
        matches = search_supabase_vectors(vector)
        
        # 3. Prepare Context
        summaries = [m['content'] for m in matches if "Summary" in m['content']]
        details = [m['content'] for m in matches if "Summary" not in m['content']]
        final_context = "\n".join(summaries + details)

        # 4. Human-Like Prompt for Hugging Face
        # Mistral uses [INST] tags for instructions
        prompt = f"<s>[INST] You are a friendly HR assistant. Use this data:\n{final_context}\n\nQuestion: {request_data.question}\nAnswer directly and humanly. Do not mention file names or technical IDs. [/INST]"
        
        # Ensure there are no extra spaces in the token
        hf_token_clean = HF_TOKEN.strip() if HF_TOKEN else ""
        headers = {"Authorization": f"Bearer {hf_token_clean}", "Content-Type": "application/json"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "return_full_text": False
            }
        }

        # Use the updated Router URL
        res = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=15)
        
        if res.status_code == 200:
            answer = res.json()[0]['generated_text'].strip()
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"Hugging Face API error: {res.status_code}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
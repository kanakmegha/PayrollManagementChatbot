import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Use Service Role for better reliability
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Supabase environment variables are MISSING!")
    print(f"URL found: {bool(SUPABASE_URL)}, KEY found: {bool(SUPABASE_KEY)}")
else:
    print("✅ Environment variables loaded successfully.")
class ChatRequest(BaseModel):
    question: str

def get_embedding(text):
    """
    MATCHES EDGE FUNCTION: Uses BAAI/bge-small-en-v1.5
    """
    # Using the same router logic as your Edge Function
    url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en-v1.5"
    
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"inputs": text}
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    
    if response.status_code != 200:
        raise Exception(f"Hugging Face Embedding failed: {response.text}")
        
    return response.json()

def search_supabase(embedding):
    """
    Queries the RPC function in Supabase with the REQUIRED headers.
    """
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    
    # WE MUST SEND BOTH 'apikey' AND 'Authorization'
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.1, # Keep it low for testing
        "match_count": 3
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code != 200:
            print(f"Supabase Search Error: {response.status_code} - {response.text}")
            return []
            
        return response.json()
    except Exception as e:
        print(f"Supabase Connection Error: {e}")
        return []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        print(f"--- Incoming Question: {request_data.question} ---")
        
        # 1. Get Embedding
        vector = get_embedding(request_data.question)
        print(f"DEBUG: Vector generated. Length: {len(vector)}")

        # 2. Search Supabase
        matches = search_supabase(vector)
        print(f"DEBUG: Supabase returned {len(matches)} matches.")
        
        if len(matches) > 0:
            for i, m in enumerate(matches):
                print(f"Match {i+1}: Similarity {m.get('similarity')} | Content: {m.get('content')[:50]}...")

        # 3. Context Construction
        if not matches:
            context = "No relevant payroll documents found."
        else:
            context = "\n".join([m.get("content", "") for m in matches])

        # 4. LLM Call
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": f"You are a payroll assistant. Use this context: {context}"},
                {"role": "user", "content": request_data.question}
            ],
            "max_tokens": 500
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        answer = response.json()["choices"][0]["message"]["content"]
        
        print(f"--- AI Answer Generated ---")
        return {"answer": answer}

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
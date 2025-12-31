import os
import requests
from fastapi import FastAPI, HTTPException
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

# Standardize your environment variables here
HF_TOKEN = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Matches your Edge Function: uses BAAI/bge-small-en-v1.5"""
    url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en-v1.5"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"inputs": text}, timeout=30)
    
    if not response.ok:
        raise Exception(f"Embedding failed: {response.text}")
    
    data = response.json()
    return data[0] if isinstance(data[0], list) else data

def search_supabase(embedding):
    """Searches your database using the match_documents SQL function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.4, # Good balance for payroll data
        "match_count": 5
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    return response.json() if response.ok else []

import time # Add this at the top of your file

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        embedding = get_embedding(request_data.question)
        matches = search_supabase(embedding)
        context = "\n".join([m["content"] for m in matches]) if matches else "No records found."

        llm_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        # Replace the payload in your /chat endpoint with this:
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": [
                {"role": "system", "content": f"Context: {context}"},
                {"role": "user", "content": request_data.question}
                ],
                "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.1
                },
                "options": {
                "wait_for_model": True  # <--- THIS IS THE KEY
            }
        }

        # --- SMART RETRY LOGIC ---
        response = requests.post(llm_url, headers=headers, json=payload, timeout=60)
        
        # If model is loading (Status 503), wait 15 seconds and try ONE more time
        if response.status_code == 503:
            print("Model is waking up... waiting 15 seconds...")
            time.sleep(15)
            response = requests.post(llm_url, headers=headers, json=payload, timeout=60)

        if not response.ok:
            return {"answer": "I'm still waking up my brain cells. Please ask again in a moment!"}

        result = response.json()
        return {"answer": result["choices"][0]["message"]["content"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
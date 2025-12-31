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

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Generate search vector
        embedding = get_embedding(request_data.question)

        # 2. Retrieve payroll facts
        matches = search_supabase(embedding)
        context = "\n".join([m["content"] for m in matches]) if matches else "No data found."

        # 3. Generate answer using Mistral
        llm_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "You are a professional payroll assistant. Answer ONLY using the provided context. "
                        "If the info is missing, say you don't know. Be concise.\n\n"
                        f"CONTEXT:\n{context}"
                    )
                },
                {"role": "user", "content": request_data.question}
            ],
            "temperature": 0.1
        }

        response = requests.post(llm_url, headers=headers, json=payload, timeout=60)
        answer = response.json()["choices"][0]["message"]["content"]
        
        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
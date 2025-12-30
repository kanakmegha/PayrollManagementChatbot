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

HF_TOKEN = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Service role key recommended

if not all([HF_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    raise RuntimeError("Missing required environment variables!")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Matches your Edge Function exactly"""
    url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en-v1.5"
    
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"inputs": text}
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if not response.ok:
        raise Exception(f"Embedding failed ({response.status_code}): {response.text}")
    
    data = response.json()
    if isinstance(data, list) and len(data) == 1:
        return data[0]  # Sometimes returns [[...]]
    return data

def search_supabase(embedding):
    """Calls your match_documents RPC – ensure it returns similarity"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"  # Helps get full response
    }
    
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.5,   # bge-small: 0.75–0.85 typical for good matches
        "match_count": 3
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if not response.ok:
        print(f"Supabase RPC error ({response.status_code}): {response.text}")
        return []
    
    return response.json()

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        print(f"--- Question: {request_data.question} ---")
        
        # 1. Embed question
        embedding = get_embedding(request_data.question)
        print(f"Embedding generated (dim: {len(embedding)})")

        # 2. Retrieve relevant chunks
        matches = search_supabase(embedding)
        print(f"Found {len(matches)} relevant chunks")

        if matches:
            for i, m in enumerate(matches[:3]):
                sim = m.get("similarity", "?")
                content_snip = m.get("content", "")[:100]
                print(f"Match {i+1} [sim={sim:.3f}]: {content_snip}...")
        
        # 3. Build context
        if not matches:
            context = "No relevant payroll information found in uploaded documents."
        else:
            context = "\n\n".join([m["content"] for m in matches])

        # 4. Call LLM – CORRECTED endpoint + base_url style
        llm_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",  # Must be exact model ID
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful payroll assistant. Answer ONLY using the provided context. "
                        "If the information is not in the context, say you don't have access to that data. "
                        "Be concise and professional.\n\nCONTEXT:\n" + context
                    )
                },
                {"role": "user", "content": request_data.question}
            ],
            "temperature": 0.1,
            "max_tokens": 200
        }

        response = requests.post(llm_url, headers=headers, json=payload, timeout=60)
        
        if not response.ok:
            error_msg = response.text[:200]
            print(f"LLM failed ({response.status_code}): {error_msg}")
            raise Exception(f"LLM generation failed: {response.status_code}")

        answer = response.json()["choices"][0]["message"]["content"].strip()
        print("--- Answer generated ---")
        return {"answer": answer}

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
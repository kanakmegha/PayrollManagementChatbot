import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import Groq  # Make sure to run: pip install groq

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardize environment variables
HF_TOKEN = os.getenv("HF_API_KEY") # Used for embeddings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    url = "https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en-v1.5"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"inputs": text}, timeout=30)
    if not response.ok:
        raise Exception(f"Embedding failed: {response.text}")
    data = response.json()
    return data[0] if isinstance(data[0], list) else data

def search_supabase(embedding):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.4,
        "match_count": 3 # Reduced count for faster context processing
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    return response.json() if response.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get knowledge from Supabase
        embedding = get_embedding(request_data.question)
        matches = search_supabase(embedding)
        context = "\n".join([m["content"] for m in matches]) if matches else "No payroll records found."

        # 2. Define the Streaming Generator
        async def stream_generator():
            # Use Llama-3-8b on Groq for lightning-fast speeds
            stream = groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a payroll assistant. Use only this context:\n{context}"
                    },
                    {"role": "user", "content": request_data.question}
                ],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # We wrap in JSON so the frontend can easily parse it
                    yield json.dumps({"answer": content}) + "\n"

        return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

    except Exception as e:
        print(f"Error: {e}")
        # Fallback to a standard JSON error if streaming fails to start
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
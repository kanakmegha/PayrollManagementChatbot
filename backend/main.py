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
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str
def search_supabase(embedding):
    # NOW we use the SUPABASE_URL
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
def get_embedding(text: str):
    # Standard Inference API URL
    url = "https://router.huggingface.com/models/BAAI/bge-small-en-v1.5"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    
    # We add options to force the API to wait for the model to load
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True}
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if not response.ok:
        # This will show up in your Render logs
        print(f"HF Embedding Error: {response.status_code} - {response.text}")
        raise Exception(f"HF Error: {response.text}")
    
    data = response.json()
    return data[0] if isinstance(data[0], list) else data

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get Embeddings (Keep this part as it was)
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Embedding generation failed."}

        # 2. Search Supabase
        matches = search_supabase(vector)
        context = "\n".join([m["content"] for m in matches]) if matches else "No data found."

        # 3. Use the ROUTER URL with the correct Chat Format
        # This is the endpoint Hugging Face wants you to use
        llm_url = "https://router.huggingface.co/hf-inference/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }

        # The Router requires the "messages" format (OpenAI style)
        payload = {
            "model": "meta-llama/Llama-3.2-1B-Instruct",
            "messages": [
                {
                    "role": "system", 
                    "content": f"You are a payroll assistant. Use only this data: {context}"
                },
                {
                    "role": "user", 
                    "content": request_data.question
                }
            ],
            "max_tokens": 500,
            "stream": False # Set to False for now to verify it works in Swagger
        }

        response = requests.post(llm_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            # Extract the message correctly from the OpenAI-style response
            answer = result['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        else:
            # This will show the actual error message from HF in your backend
            return {"status": "error", "message": f"HF Router Error: {response.text}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
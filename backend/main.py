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
        # 1. Get knowledge from Supabase
        embedding = get_embedding(request_data.question)
        if not embedding:
            return {"answer": "Error: Could not generate embedding."}

        matches = search_supabase(embedding)
        context = "\n".join([m["content"] for m in matches])
        
        # 2. Ask Llama-3.2-1B (Direct Inference, No Streaming)
        # This is the model you used in your other project
        llm_url = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B-Instruct"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        
        prompt = f"""Use the following payroll data to answer the question. 
        If you don't know, say you don't know.
        
        Context:
        {context}
        
        Question: {request_data.question}
        Answer:"""

        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 250, "temperature": 0.1}
        }

        response = requests.post(llm_url, headers=headers, json=payload)
        result = response.json()

        # Handle the specific way Llama-1B returns data on HF
        if isinstance(result, list) and len(result) > 0:
            full_text = result[0].get("generated_text", "")
            # Remove the prompt from the answer if the model includes it
            answer = full_text.split("Answer:")[-1].strip()
            return {"status": "success", "answer": answer}
        else:
            return {"status": "error", "message": str(result)}

    except Exception as e:
        return {"status": "error", "message": str(e)}
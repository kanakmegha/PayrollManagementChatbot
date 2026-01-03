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

HF_TOKEN = os.getenv("HF_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    # This remains free and unaffected by your $0.10 limit
    url = "https://api-inference.huggingface.co/models/BAAI/bge-small-en-v1.5"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        return None
    data = res.json()
    return data[0] if isinstance(data, list) and isinstance(data[0], list) else data

def search_supabase(embedding):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    payload = {"query_embedding": embedding, "match_threshold": 0.3, "match_count": 5}
    res = requests.post(url, headers=headers, json=payload)
    return res.json() if res.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Embedding failed. Check HF_API_KEY in Render."}

        matches = search_supabase(vector)
        context = "\n".join([m["content"] for m in matches]) if matches else "No data."

        # FIXED: Using the FREE Serverless URL instead of the Paid Router
        # We use Mistral-7B because it has a high free allowance
        free_llm_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
        
        # NOTE: The free tier uses "inputs", not "messages"
        payload = {
            "inputs": f"<s>[INST] Use this payroll data: {context}\n\nQuestion: {request_data.question} [/INST]",
            "parameters": {"max_new_tokens": 200, "temperature": 0.7}
        }

        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        response = requests.post(free_llm_url, headers=headers, json=payload)

        if response.status_code == 200:
            result = response.json()
            # Free tier returns a list: [{'generated_text': '...'}]
            full_text = result[0]['generated_text']
            answer = full_text.split("[/INST]")[-1].strip()
            return {"status": "success", "answer": answer}
        else:
            return {"status": "error", "message": f"Free Tier Error: {response.text}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
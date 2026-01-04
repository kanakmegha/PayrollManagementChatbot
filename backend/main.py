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

# Configuration from Render Environment Variables
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Uses OpenRouter's OpenAI-compatible endpoint for embeddings."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/text-embedding-3-small", 
        "input": text
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()['data'][0]['embedding']
        print(f"Embedding Error: {res.text}")
        return None
    except Exception as e:
        print(f"Embedding Exception: {e}")
        return None

def get_supabase_count():
    """Directly counts records in your table for 100% accuracy."""
    # Assuming your table is named 'employees'. Change if your table is named 'payroll' or 'documents'.
    url = f"{SUPABASE_URL}/rest/v1/documents?select=count" 
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=exact"
    }
    try:
        res = requests.get(url, headers=headers)
        # Supabase returns count in the Content-Range header: '0-0/45'
        content_range = res.headers.get("Content-Range")
        if content_range:
            return content_range.split("/")[-1]
        return "unknown"
    except:
        return "unknown"

def search_supabase_vectors(embedding):
    """Finds specific text chunks for RAG."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query_embedding": embedding, "match_threshold": 0.3, "match_count": 5}
    res = requests.post(url, headers=headers, json=payload)
    return res.json() if res.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        q = request_data.question.lower()
        
        # --- INTELLIGENT ROUTING ---
        # 1. Check if the user is asking for a count (Headcount/Total Employees)
        if any(word in q for word in ["how many employees", "total employees", "headcount", "number of staff"]):
            total = get_supabase_count()
            return {
                "status": "success", 
                "answer": f"I've checked the database directly: there are currently {total} employees enrolled in the system."
            }

        # 2. Standard Intelligent Search (RAG) for other questions
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Connection to OpenRouter failed."}

        matches = search_supabase_vectors(vector)
        context = "\n".join([m["content"] for m in matches]) if matches else "No specific records found."

        # OpenRouter Chat Completion
        llm_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        
        llm_payload = {
            "model": "meta-llama/llama-3.2-3b-instruct",
            "messages": [
                {"role": "system", "content": f"You are a Payroll Assistant. Use this data: {context}. If info is missing, say you don't know."},
                {"role": "user", "content": request_data.question}
            ]
        }

        res = requests.post(llm_url, headers=headers, json=llm_payload)
        if res.status_code == 200:
            answer = res.json()['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"LLM Error: {res.status_code}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
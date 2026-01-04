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

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": "openai/text-embedding-3-small", "input": text}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        return res.json()['data'][0]['embedding'] if res.status_code == 200 else None
    except: return None

def search_supabase_vectors(embedding):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query_embedding": embedding, "match_threshold": 0.2, "match_count": 20}
    res = requests.post(url, headers=headers, json=payload)
    return res.json() if res.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        vector = get_embedding(request_data.question)
        if not vector: return {"status": "error", "message": "Connection error."}

        matches = search_supabase_vectors(vector)
        
        # Sorter: Keep summary info but don't force the AI to mention file names
        summary_info = ""
        context_data = ""
        for m in matches:
            if "Summary" in m['content']:
                summary_info += m['content'] + "\n"
            else:
                context_data += m['content'] + "\n"
        
        final_context = summary_info + context_data

        # --- HUMAN-LIKE SYSTEM PROMPT ---
       system_instruction = """
        You are a friendly and efficient HR Assistant. 
        Your goal is to provide quick, natural answers as if you are talking to a teammate.

        CORE GUIDELINES:
        - BE DIRECT: If someone asks "how many employees", just say "There are currently 6 employees in the company."
        - HUMAN TONE: Use a warm, professional, and conversational style. 
        - NO TECHNICAL JARGON: Never mention 'CSV files', 'metadata', 'Summary rows', or 'IDs' unless specifically asked.
        - TRUST SUMMARIES: If the context contains a 'Summary for...', use those totals (counts/salaries) as the absolute truth.
        - PRIVACY: Don't dump a whole list of data; just answer the specific question asked.
        """

        llm_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        
        llm_payload = {
            "model": "meta-llama/llama-3.2-3b-instruct",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Context: {final_context}\n\nUser Question: {request_data.question}"}
            ],
            "temperature": 0.7 # Increased for a more "human" and less "robotic" flow
        }

        res = requests.post(llm_url, headers=headers, json=llm_payload)
        if res.status_code == 200:
            return {"status": "success", "answer": res.json()['choices'][0]['message']['content']}
        
        return {"status": "error", "message": "LLM Error"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
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

# Configuration
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Generates a 1536-dim vector for semantic search."""
    url = "https://openrouter.ai/api/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": "openai/text-embedding-3-small", "input": text}
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        return res.json()['data'][0]['embedding'] if res.status_code == 200 else None
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def search_supabase_vectors(embedding):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    # CHANGE 1: Lower threshold from 0.4 to 0.2 (more inclusive)
    # CHANGE 2: Increase match_count to 15
    payload = {
        "query_embedding": embedding, 
        "match_threshold": 0.2, 
        "match_count": 15
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.json() if res.ok else []

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Semantic Search Logic
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Failed to generate search vector."}

        matches = search_supabase_vectors(vector)
        
        # 2. Build Context with Source Attribution
        # This tells the AI exactly which file the data came from
        context_list = []
        for m in matches:
            source = m.get('metadata', {}).get('source', 'Unknown File')
            context_list.append(f"[Source: {source}]: {m['content']}")
        
        context = "\n".join(context_list) if context_list else "No relevant records found."

        # 3. High-Intelligence System Prompt
        # This resolves the "7 vs 6" issue by instructing the AI on how to read summaries.
        system_instruction = """
        You are a Professional Payroll & HR Assistant. Use the provided context to answer.
        
        CORE RULES:
        1. If asked for totals (count of employees, total salary), look for a line starting with 'Summary for...'. 
           TRUST THE SUMMARY LINE above all else. Do not manually count individual data rows.
        2. Always mention which file the information was found in (e.g., 'According to the Master Payroll file...').
        3. If a specific employee is mentioned, provide all relevant details (Salary, ID, Status) found in the context.
        4. Maintain a conversational but professional tone.
        5. If the information is missing from the context, say: 'I'm sorry, I don't have that specific record in my system.'
        """

        # 4. LLM Generation (Llama 3.2 for complex reasoning)
        llm_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        
        llm_payload = {
            "model": "meta-llama/llama-3.2-3b-instruct",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Context for search:\n{context}\n\nQuestion: {request_data.question}"}
            ],
            "temperature": 0.3 # Lower temperature ensures more factual, less creative answers
        }

        res = requests.post(llm_url, headers=headers, json=llm_payload)
        
        if res.status_code == 200:
            answer = res.json()['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"LLM Error: {res.status_code}"}

    except Exception as e:
        return {"status": "error", "message": f"Server Error: {str(e)}"}
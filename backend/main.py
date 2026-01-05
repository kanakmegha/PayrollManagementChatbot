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

# --- CONFIGURATION ---
# Make sure to add HF_TOKEN to your .env file
HF_TOKEN = os.getenv("HF_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class ChatRequest(BaseModel):
    question: str

def get_embedding(text: str):
    """Uses Hugging Face Serverless API for embeddings"""
    # Standard fast embedding model
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(url, headers=headers, json={"inputs": [text], "options": {"wait_for_model": True}}, timeout=15)
        if response.status_code == 200:
            # Hugging Face returns a list of lists for feature-extraction
            return response.json()[0] 
        return None
    except Exception as e:
        print(f"Embedding Error: {e}")
        return None

def search_supabase_vectors(embedding):
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query_embedding": embedding, 
        "match_threshold": 0.2, 
        "match_count": 10 
    }
    res = requests.post(url, headers=headers, json=payload)
    results = res.json() if res.ok else []
    
    # Sort by ID descending for newest context
    results.sort(key=lambda x: x.get('id', 0), reverse=True)
    return results

@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get Vector from Hugging Face
        vector = get_embedding(request_data.question)
        if not vector: 
            return {"status": "error", "message": "Could not generate embedding."}

        # 2. Search Supabase
        matches = search_supabase_vectors(vector)
        
        summary_info = ""
        context_data = ""
        for m in matches:
            if "Summary" in m['content']:
                summary_info += m['content'] + "\n"
            else:
                context_data += m['content'] + "\n"
        
        final_context = summary_info + context_data

        # 3. Call LLM (Llama 3.2 via HF Router)
        # Using the OpenAI-compatible router at Hugging Face
        llm_url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        
        system_instruction = """
        You are a friendly and efficient HR Assistant. 
        Your goal is to provide quick, natural answers as if you are talking to a teammate.
        - BE DIRECT: Just give the answer.
        - HUMAN TONE: Warm and professional.
        - NO TECHNICAL JARGON: Never mention file types or metadata.
        - TRUST SUMMARIES: Use 'Summary for...' totals as truth.
        """

        llm_payload = {
            "model": "meta-llama/Llama-3.2-3B-Instruct:hf-inference", # Ensure provider is specified
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Context: {final_context}\n\nUser Question: {request_data.question}"}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        res = requests.post(llm_url, headers=headers, json=llm_payload)
        
        if res.status_code == 200:
            return {"status": "success", "answer": res.json()['choices'][0]['message']['content']}
        elif res.status_code == 503:
            return {"status": "error", "message": "Model is loading on Hugging Face. Please try again in 30 seconds."}
        
        return {"status": "error", "message": f"HF Error: {res.text}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
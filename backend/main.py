import os
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException

app = FastAPI()

# --- 1. CONFIGURATION ---
# These must be in your Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HF_SPACE_URL = "https://Meg89-payroll-heavy-lifter.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN")

def wake_hf():
    """Wakes up the HF Space so it doesn't sleep"""
    try:
        requests.get(HF_SPACE_URL, timeout=5)
    except:
        pass

@app.get("/")
def root():
    return {"message": "Payroll Manager (Requests-Mode) Online"}

@app.post("/chat")
async def chat(request_data: dict, background_tasks: BackgroundTasks):
    # Keep the worker awake in the background
    background_tasks.add_task(wake_hf)

    user_text = request_data.get("question")
    if not user_text:
        raise HTTPException(status_code=400, detail="No question provided")

    # STEP 1: Get Vector from Hugging Face
    headers_hf = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response_hf = requests.post(
            f"{HF_SPACE_URL}/embed", 
            headers=headers_hf, 
            json={"text": user_text}, 
            timeout=15
        )
        vector = response_hf.json().get("embedding")
    except Exception as e:
        return {"answer": "The AI brain is warming up. Please try again in 30 seconds."}

    # STEP 2: Search Supabase using direct REST API (Manual Mode)
    # This replaces the broken 'supabase' library logic
    supabase_rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers_sb = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload_sb = {
        "query_embedding": vector,
        "match_threshold": 0.5,
        "match_count": 1
    }

    try:
        response_sb = requests.post(supabase_rpc_url, headers=headers_sb, json=payload_sb)
        data = response_sb.json()
        
        if data and len(data) > 0:
            return {"answer": data[0]['content']}
        return {"answer": "I couldn't find an answer in the payroll documents."}
        
    except Exception as e:
        return {"answer": f"Database error: {str(e)}"}
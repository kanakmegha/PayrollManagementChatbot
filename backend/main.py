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
        raw_data = response_hf.json()

        # --- THE STRICT CLEANER ---
        # This loop digs through lists and dicts until it finds the raw list of floats
        vector = raw_data
        while isinstance(vector, list) and len(vector) > 0 and not isinstance(vector[0], (int, float)):
            vector = vector[0]
        
        if isinstance(vector, dict):
            vector = vector.get("embedding")

        # Validation: If it's not a list of numbers now, it's broken
        if not isinstance(vector, list) or not isinstance(vector[0], (int, float)):
            return {"answer": f"Embedding format error: Received {type(vector)} instead of list of floats."}

    except Exception as e:
        return {"answer": f"AI Brain Error: {str(e)}"}

    # STEP 2: Search Supabase
    supabase_rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers_sb = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload_sb = {
        "query_embedding": vector, # This is now guaranteed to be [0.123, 0.456, ...]
        "match_threshold": 0.1,
        "match_count": 1
    }

    try:
        response_sb = requests.post(supabase_rpc_url, headers=headers_sb, json=payload_sb)
        
        if response_sb.status_code != 200:
            # This will show you exactly what Postgres is complaining about
            return {"answer": f"Database Error: {response_sb.text}"}
            
        data = response_sb.json()
        if data and len(data) > 0:
            return {"answer": data[0].get('content', "No content found.")}
        
        return {"answer": "I couldn't find an answer in the payroll documents."}
        
    except Exception as e:
        return {"answer": f"System error: {str(e)}"}
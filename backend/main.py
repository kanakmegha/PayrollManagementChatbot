import os
import requests
from fastapi import FastAPI, BackgroundTasks
from supabase import create_client, Client

app = FastAPI()

# --- 1. THE CONNECTION (FIXED) ---
# This ensures 'supabase' is defined globally so all functions can see it
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# URL of your new HF Space
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
    return {"message": "Payroll Manager Online"}

@app.post("/chat")
async def chat(request_data: dict, background_tasks: BackgroundTasks):
    # Keep the worker awake in the background
    background_tasks.add_task(wake_hf)

    user_text = request_data.get("question")

    # STEP 1: Get math from Hugging Face
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(f"{HF_SPACE_URL}/embed", 
                                 headers=headers, 
                                 json={"text": user_text}, 
                                 timeout=15)
        vector = response.json().get("embedding")
    except Exception:
        return {"answer": "The AI brain is waking up. Please try again in 10 seconds."}

    # STEP 2: Search your Supabase Database
    # This uses the exact same function name you likely used in SQL
    result = supabase.rpc("match_documents", {
        "query_embedding": vector,
        "match_threshold": 0.5,
        "match_count": 1
    }).execute()

    if result.data:
        return {"answer": result.data[0]['content']}
    
    return {"answer": "I couldn't find that in the payroll records."}
import os
import requests
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

class Settings:
    # These must be set in your Render/Local environment variables
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY") 
    HF_SPACE_URL = os.getenv("HF_SPACE_URL")

app = FastAPI()

class ChatRequest(BaseModel):
    question: str

def wake_hf():
    """Background task to keep the HF Space awake and responsive."""
    try:
        # Pinging the root endpoint
        requests.get(Settings.HF_SPACE_URL, timeout=10)
    except:
        pass

@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    # Keep HF Space from idling
    background_tasks.add_task(wake_hf)
    
    user_text = request.question
    cot = [f"User asked: '{user_text}'"]
    
    headers_hf = {"Authorization": f"Bearer {Settings.HF_TOKEN}"}
    vector = None

    # --- STEP 1: GET EMBEDDING (SEARCH PREP) ---
    try:
        cot.append("Step 1: Requesting vector from Hugging Face Space...")
        for attempt in range(2):
            resp_hf = requests.post(
                f"{Settings.HF_SPACE_URL}/embed", 
                headers=headers_hf, 
                json={"text": user_text}, 
                timeout=20
            )
            
            if resp_hf.status_code == 503:
                cot.append("HF Space is warming up. Retrying in 5s...")
                time.sleep(5)
                continue

            data_hf = resp_hf.json()
            # Robust vector extraction from your HF structure
            if isinstance(data_hf, list) and len(data_hf) > 0:
                vector = data_hf[0].get("embedding") if isinstance(data_hf[0], dict) else data_hf[0]
            elif isinstance(data_hf, dict):
                vector = data_hf.get("embedding")

            if vector: break
        
        if not vector:
            return {"answer": "Error: Could not generate search vector.", "chain_of_thought": cot}
            
    except Exception as e:
        return {"answer": f"Connection Error (HF Embed): {str(e)}", "chain_of_thought": cot}

    # --- STEP 2: SEARCH SUPABASE ---
    try:
        cot.append("Step 2: Retrieving top candidates from Supabase...")
        rpc_url = f"{Settings.SUPABASE_URL}/rest/v1/rpc/match_documents"
        headers_sb = {
            "apikey": Settings.SUPABASE_KEY,
            "Authorization": f"Bearer {Settings.SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        payload_sb = {
            "query_embedding": vector,
            "match_threshold": 0.2, 
            "match_count": 8
        }

        resp_sb = requests.post(rpc_url, headers=headers_sb, json=payload_sb)
        db_results = resp_sb.json()
        
        if not db_results:
            return {"answer": "I couldn't find any relevant data in my records.", "chain_of_thought": cot}

        # Filter out invalid summaries (your existing bug filter)
        valid_chunks = []
        for d in db_results:
            content = d.get("content", "")
            if "is 0" in content and "Summary" in content:
                continue
            valid_chunks.append(content)
            
        if not valid_chunks:
            return {"answer": "Found data, but it appears to be empty or corrupted.", "chain_of_thought": cot}

    except Exception as e:
        return {"answer": f"Database Error: {str(e)}", "chain_of_thought": cot}

    # --- STEP 3: Reranking & Extraction ---
    # --- In your main.py /chat endpoint ---
    try:
        rerank_resp = requests.post(
            f"{Settings.HF_SPACE_URL}/rerank",
            headers=headers_hf,
            json={"query": user_text, "documents": valid_chunks},
            timeout=30 # Important for the Brain to have time to write
        )
        # ... rest of your code
        
        rank_data = rerank_resp.json()
        
        # This is now the intelligent answer from FLAN-T5
        intelligent_answer = rank_data.get("best_answer", "No answer found.")
        
        # Log the confidence score from the CrossEncoder for transparency
        score = rank_data.get("score", 0)
        cot.append(f"Answer extracted successfully. Judge Score: {score}")

        return {
            "answer": intelligent_answer,
            "chain_of_thought": cot,
            "status": "success"
        }

    except Exception as e:
        # Safety Fallback: If the Brain/Reranker fails, return the best raw chunk
        fallback = valid_chunks[0].split(":")[-1].strip() if valid_chunks else "Error during extraction."
        return {
            "answer": fallback, 
            "chain_of_thought": cot, 
            "note": f"Reranking/Extraction failed: {str(e)}"
        }

@app.get("/")
def home():
    return {"status": "Payroll Bot is Online with Intelligent Extraction"}
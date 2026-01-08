import os
import requests
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI()

# --- Configuration ---
# Ensure these are set in your Render Dashboard -> Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
# Must be the .hf.space link, e.g., https://username-space.hf.space
HF_SPACE_URL = os.getenv("HF_SPACE_URL") 

class ChatRequest(BaseModel):
    question: str

def wake_hf():
    """Background task to keep the HF Space awake."""
    try:
        requests.get(HF_SPACE_URL, timeout=5)
    except:
        pass

@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(wake_hf)
    user_text = request.question
    
    # 1. CHAIN OF THOUGHT: Start
    cot = [f"User asked: '{user_text}'"]
    print(f"[LOG] {cot[-1]}")

    # 2. STEP: Get Embedding from Hugging Face
    headers_hf = {"Authorization": f"Bearer {HF_TOKEN}"}
    vector = None
    
    try:
        cot.append("Step 1: Requesting 384-dim vector from Hugging Face Space...")
        # Use a retry loop for 'NoneType' or 503 errors (Warming up)
        for attempt in range(2):
            resp_hf = requests.post(f"{HF_SPACE_URL}/embed", headers=headers_hf, json={"text": user_text}, timeout=20)
            
            if resp_hf.status_code == 503:
                cot.append("HF Space is sleeping. Retrying in 5 seconds...")
                time.sleep(5)
                continue

            data_hf = resp_hf.json()
            # Robust extraction to avoid 'NoneType' error
            if isinstance(data_hf, list) and len(data_hf) > 0:
                vector = data_hf[0].get("embedding") if isinstance(data_hf[0], dict) else data_hf[0]
            elif isinstance(data_hf, dict):
                vector = data_hf.get("embedding")

            if vector:
                break
        
        if not vector:
            error_msg = f"Embedding Error: HF returned {type(data_hf)}. Raw: {str(data_hf)[:100]}"
            cot.append(error_msg)
            return {"answer": error_msg, "chain_of_thought": cot}

        cot.append(f"Successfully received vector of length {len(vector)}.")

    except Exception as e:
        return {"answer": f"Embedding Connection Error: {str(e)}", "chain_of_thought": cot}

    # 3. STEP: Search Supabase
    cot.append("Step 2: Searching Supabase using 'match_documents' RPC...")
    rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_documents"
    headers_sb = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    # We grab 8 chunks to bypass any "0 summary" bugs
    payload_sb = {
        "query_embedding": vector,
        "match_threshold": 0.2, 
        "match_count": 8
    }

    try:
        resp_sb = requests.post(rpc_url, headers=headers_sb, json=payload_sb)
        db_results = resp_sb.json()
        
        if not db_results or len(db_results) == 0:
            cot.append("Database Search: No relevant document chunks found.")
            return {"answer": "I don't have enough information in my database to answer that.", "chain_of_thought": cot}

        cot.append(f"Found {len(db_results)} matching chunks. Filtering results...")

        # 4. STEP: Logic/Reasoning (Chain of Thought)
        final_context = []
        for i, doc in enumerate(db_results):
            txt = doc.get("content", "")
            score = round(doc.get("similarity", 0), 3)
            
            # THE BUG FILTER: Skip the summary lines that contain the "0" error
            if "Summary for" in txt and "is 0" in txt:
                cot.append(f"Chunk {i+1} (Score {score}): Skipped (Detected incorrect auto-summary).")
                continue
            
            cot.append(f"Chunk {i+1} (Score {score}): Accepted factual data.")
            final_context.append(txt)

        if not final_context:
            return {"answer": "I found references, but they were incomplete summaries. Please check your source file.", "chain_of_thought": cot}

        # 5. STEP: Conclusion
        cot.append("Step 3: Compiling final answer from valid raw text.")
        answer = "\n".join([f"• {c}" for c in final_context])
        
        return {
            "answer": f"Based on the files provided:\n\n{answer}",
            "chain_of_thought": cot,
            "status": "success"
        }

    except Exception as e:
        return {"answer": f"Database Error: {str(e)}", "chain_of_thought": cot}

@app.get("/")
def home():
    return {"status": "Payroll Bot is Online"}
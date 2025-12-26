import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client

import sys

# --- EMERGENCY MONKEY PATCH START ---
# This fixes the 'proxy' error by forcing httpx to ignore that argument
try:
    import httpx
    if hasattr(httpx, "Client"):
        original_init = httpx.Client.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.pop("proxy", None) # Remove the problematic argument
            return original_init(self, *args, **kwargs)
        httpx.Client.__init__ = patched_init
        
    if hasattr(httpx, "AsyncClient"):
        original_async_init = httpx.AsyncClient.__init__
        def patched_async_init(self, *args, **kwargs):
            kwargs.pop("proxy", None)
            return original_async_init(self, *args, **kwargs)
        httpx.AsyncClient.__init__ = patched_async_init
    print("--- DEBUG: HTTPX Monkey Patch Applied ---")
except Exception as e:
    print(f"--- DEBUG: Patch Failed: {e} ---")
# --- EMERGENCY MONKEY PATCH END ---

from fastapi import FastAPI
# ... rest of your imports and create_client code
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

app = FastAPI()

# --- ENV ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, HF_API_KEY]):
    print("WARNING: Missing environment variables. Check your Render Dashboard.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================
# LlamaIndex Global Settings
# ===========================
# We must specify an embedding model, otherwise LlamaIndex 
# will try to use OpenAI and crash on Render.
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = None  # We are calling HuggingFace manually via API
Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

# ===========================
# Models
# ===========================
class Query(BaseModel):
    question: str

# ===========================
# HuggingFace Call
# ===========================
async def call_hf_model(prompt: str):
    # Ensure this model ID is correct for the Inference API
    endpoint = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            res = await client.post(endpoint, headers=headers, json={"inputs": prompt})
            res.raise_for_status()
            data = res.json()
            # Standard HF Inference return is a list of dicts
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "No response from model.")
            return str(data)
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

# ===========================
# Build LlamaIndex
# ===========================
def load_index():
    # Corrected the table_name and supabase_client mapping
    vector_store = SupabaseVectorStore(
        supabase_client=supabase,
        table_name="documents" # Ensure this matches your Supabase table name
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    # Reconstruct the index from the existing vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context
    )
    return index

# Initialize index and engine globally
try:
    index = load_index()
    query_engine = index.as_query_engine(similarity_top_k=5)
except Exception as e:
    print(f"Index Load Error: {e}")
    index = None

# ===========================
# API Route
# ===========================
@app.post("/chat")
async def rag_chat(q: Query):
    if not index:
        raise HTTPException(status_code=500, detail="Index not initialized.")

    # 1. Retrieve context using LlamaIndex
    response = query_engine.query(q.question)
    context_text = str(response)

    # 2. Build the final prompt for HuggingFace
    final_prompt = f"Context: {context_text}\n\nQuestion: {q.question}\n\nAnswer:"

    # 3. Get answer from HuggingFace
    answer = await call_hf_model(final_prompt)
    
    return {"answer": answer, "context_used": context_text}
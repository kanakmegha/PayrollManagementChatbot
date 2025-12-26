# --- EMERGENCY MONKEY PATCH MUST BE LINE 1 ---
import httpx

try:
    if hasattr(httpx, "Client"):
        original_init = httpx.Client.__init__
        def patched_init(self, *args, **kwargs):
            kwargs.pop("proxy", None)
            return original_init(self, *args, **kwargs)
        httpx.Client.__init__ = patched_init
        
    if hasattr(httpx, "AsyncClient"):
        original_async_init = httpx.AsyncClient.__init__
        def patched_async_init(self, *args, **kwargs):
            kwargs.pop("proxy", None)
            return original_async_init(self, *args, **kwargs)
        httpx.AsyncClient.__init__ = patched_async_init
    print("--- DEBUG: HTTPX Monkey Patch Applied Successfully ---")
except Exception as e:
    print(f"--- DEBUG: Patch Failed: {e} ---")

import os

import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client


from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai import OpenAI # Added this import

app = FastAPI()

# --- ENV ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_API_KEY") # Ensure this is your Hugging Face Token

if not all([SUPABASE_URL, SUPABASE_KEY, HF_TOKEN]):
    print("WARNING: Missing environment variables. Check your Render Dashboard.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===========================
# LlamaIndex Global Settings
# ===========================
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# MODIFIED: Using the HF Router (OpenAI-compatible)
Settings.llm = OpenAI(
    model="mistralai/Mistral-7B-Instruct-v0.2", # You can change this to any HF model
    api_key=HF_TOKEN,
    api_base="https://router.huggingface.co/v1"
)

Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

# ===========================
# Models
# ===========================
class Query(BaseModel):
    question: str

# ===========================
# Build LlamaIndex
# ===========================
def load_index():
    vector_store = SupabaseVectorStore(
        supabase_client=supabase,
        table_name="documents" 
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context
    )
    return index

try:
    index = load_index()
    # The query engine now uses the LLM defined in Settings.llm
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

    try:
        # 1. & 2. & 3. Combined: LlamaIndex retrieves context, 
        # builds the prompt, and calls the HF Router all in one go.
        response = query_engine.query(q.question)
        
        # We can extract the text and the sources used
        answer = str(response)
        context_used = [node.get_content() for node in response.source_nodes]

        return {
            "answer": answer, 
            "context_used": context_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query Error: {str(e)}")
from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.vector_stores import SupabaseVectorStore
from llama_index.core import SimpleDirectoryReader
import httpx
import os

app = FastAPI()

# --- ENV ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ===========================
# Models
# ===========================
class Query(BaseModel):
    question: str


# ===========================
# HuggingFace Call
# ===========================
async def call_hf_model(prompt: str):
    endpoint = "https://api-inference.huggingface.co/models/gpt-oss-120b"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    async with httpx.AsyncClient(timeout=180) as client:
        res = await client.post(endpoint, headers=headers,
            json={"inputs": prompt}
        )
        return res.json()[0]["generated_text"]


# ===========================
# Build LlamaIndex
# ===========================
def load_index():
    vector_store = SupabaseVectorStore(
        supabase_client=supabase,
        table_name="documents"
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context
    )
    return index


index = load_index()
query_engine = index.as_query_engine(similarity_top_k=5)


# ===========================
# API Route
# ===========================
@app.post("/chat")
async def rag_chat(q: Query):
    retrieved = query_engine.query(q.question)

    final_prompt = f"""
    Answer using context below.

    Context:
    {retrieved}

    Question:
    {q.question}
    """

    answer = await call_hf_model(final_prompt)
    return {"answer": answer}

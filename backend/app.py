import os
from fastapi import FastAPI, Header, HTTPException
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI()

# 1. This uses 16GB RAM to load the math brain
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.get("/")
def health():
    return {"status": "Heavy Lifter is Running"}

@app.post("/embed")
async def get_embedding(data: dict, authorization: str = Header(None)):
    # 2. SECURITY: Uses the token you already put in your ENV
    expected = f"Bearer {os.environ.get('HF_TOKEN')}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    text = data.get("text", "")
    # 3. Returns the numbers Render is looking for
    embedding = model.encode(text).tolist()
    return {"embedding": embedding}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
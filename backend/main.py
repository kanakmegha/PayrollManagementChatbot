@app.post("/chat")
async def chat(request_data: ChatRequest):
    try:
        # 1. Get Embedding (OpenRouter)
        vector = get_embedding(request_data.question)
        if not vector:
            return {"status": "error", "message": "Search service unavailable."}

        # 2. Search Database (Supabase)
        matches = search_supabase_vectors(vector)
        final_context = "\n".join([m['content'] for m in matches])

        # 3. New HF Router Request (OpenAI Format)
        headers = {
            "Authorization": f"Bearer {HF_TOKEN.strip()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.3",
            "messages": [
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": f"Context: {final_context}\n\nQuestion: {request_data.question}"}
            ],
            "max_tokens": 500,
            "stream": False
        }

        # Use the NEW Router URL
        res = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions", 
            headers=headers, 
            json=payload, 
            timeout=20
        )

        if res.status_code == 200:
            result = res.json()
            # Extract the answer from the new OpenAI-style response format
            answer = result['choices'][0]['message']['content'].strip()
            return {"status": "success", "answer": answer}
        
        return {"status": "error", "message": f"HF Router Error: {res.status_code} - {res.text}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
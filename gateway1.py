import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

app = FastAPI(title="Local AI Router")

# The local target (Ollama running Gemma 4 natively in WSL)
OLLAMA_URL = "http://localhost:11434/v1"

@app.post("/v1/chat/completions")
async def handle_routing(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    
    if not messages:
        raise HTTPException(status_code=400, detail="Conversation payload empty.")
        
    # Inspect the last message from the user
    last_prompt = messages[-1].get("content", "").lower()
    
    # ---------------------------------------------------------
    # Route 1: The Google Agent Team (Triggered by '#agent')
    # ---------------------------------------------------------
    if "#agent" in last_prompt:
        logger.info("⚡ Agent trigger detected! Routing to Google ADK framework...")
        # Note: We will wire the actual agent_team.py execution block here next!
        # For now, we return a system message acknowledging the route.
        async def mock_agent_stream():
            yield b'{"choices":[{"delta":{"content":"[System] Agent route engaged. Standing by for code execution integration."}}]}'
        return StreamingResponse(mock_agent_stream(), media_type="text/event-stream")

    # ---------------------------------------------------------
    # Route 2: Fast Local VRAM Tier (Default)
    # ---------------------------------------------------------
    logger.info("🚀 Routing directly to Local GPU (Gemma 4)")
    async def stream_local():
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/chat/completions", json=body) as response:
                if response.status_code != 200:
                    yield b"Error communicating with local inference node."
                    return
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_local(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
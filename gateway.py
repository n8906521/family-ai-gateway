import asyncio
import json
import logging
import httpx
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types

# Load secrets from the .env file
load_dotenv()

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ai-gateway")

# ---------------------------------------------------------
# Global Configurations & Client Initializations
# ---------------------------------------------------------
app = FastAPI(title="AI Homelab Gateway Control Tower")

# Centralized Model Variable
gemini_model = "gemini-2.5-flash"

# Backend Upstream URLs
OLLAMA_URL = "http://localhost:11434/v1"

# Automatically picks up GEMINI_API_KEY from environment variables
gemini_client = genai.Client()

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def format_chunk(text: str) -> bytes:
    """Formats plain text into a valid OpenAI/Open WebUI SSE streaming data chunk."""
    chunk = {
        "choices": [{
            "index": 0,
            "delta": {"content": text},
            "finish_reason": None
        }]
    }
    return f"data: {json.dumps(chunk)}\n\n".encode('utf-8')

# ---------------------------------------------------------
# Streaming Multi-Agent Loop (#codeagent)
# ---------------------------------------------------------
async def run_agent_team_stream(user_request: str):
    try:
        yield format_chunk("### 🤖 Supervisor Strategy Planning\n")
        yield format_chunk("Consulting live internet sources and mapping technical strategy...\n\n")
        await asyncio.sleep(0.1)
        
        # 1. Supervisor Agent (Equipped with Live Google Search Grounding)
        plan_response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=(
                f"You are the Lead Engineering Agent. You have access to Google Search. "
                f"First, search the web for the latest documentation, current events, or versions if needed. "
                f"Then, break this request into a strict 3-step technical plan for your coding agent to execute. "
                f"Request: {user_request}"
            ),
            config=types.GenerateContentConfig(
                temperature=0.2,
                tools=[{"google_search": {}}]  # Active web search grounding
            )
        )
        approved_plan = plan_response.text
        yield format_chunk(f"{approved_plan}\n\n")
        yield format_chunk("---\n\n")
        
        yield format_chunk("### 💻 Coder Sandbox Execution\n")
        yield format_chunk("Deploying cloud sandbox to build and verify execution...\n\n")
        await asyncio.sleep(0.1)
        
        # 2. Execution Agent (Equipped with isolated code execution sandbox)
        coder_response = gemini_client.models.generate_content(
            model=gemini_model,
            contents=(
                f"You are the Execution Agent. Write a Python script to fulfill this exact plan. "
                f"Once written, run it using your code execution tool to verify it works. "
                f"Return the final clean code and the execution results.\n\n"
                f"Plan:\n{approved_plan}"
            ),
            config=types.GenerateContentConfig(
                tools=[{"code_execution": {}}],  # Native Python code sandbox execution
                temperature=0.1
            )
        )
        yield format_chunk(f"{coder_response.text}\n")
        
        # Signal clean completion to the frontend
        final_payload = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(final_payload)}\n\n".encode('utf-8')
        yield b"data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"❌ Agent Team Exception: {str(e)}")
        yield format_chunk(f"\n\n❌ Error executing multi-agent loop: {str(e)}\n")
        yield b"data: [DONE]\n\n"

# ---------------------------------------------------------
# Dynamic Model Discovery Endpoint
# ---------------------------------------------------------
@app.get("/v1/models")
async def list_models():
    models = []
    
    # Strip the /v1 suffix to cleanly query Ollama's native management API
    OLLAMA_BASE = OLLAMA_URL.replace("/v1", "")
    
    # 1. Dynamic Discovery from local Ollama GPU instance
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{OLLASE_BASE}/api/tags" if 'OLLASE_BASE' in locals() else f"{OLLAMA_BASE}/api/tags")
            if resp.status_code == 200:
                ollama_data = resp.json()
                ollama_models = ollama_data.get("models", [])
                
                for m in ollama_models:
                    model_name = m.get("model") or m.get("name")
                    if model_name:
                        models.append({
                            "id": model_name,
                            "object": "model",
                            "owned_by": "local-gpu"
                        })
            else:
                logger.warning(f"⚠️ Ollama returned unexpected status {resp.status_code} at /api/tags")
        except Exception as e:
            logger.warning(f"⚠️ Could not resolve local Ollama models on startup: {e}")
            
    # 2. Virtual model mapping for Cloud Architecture
    models.append({
        "id": "gemma4-agent", 
        "object": "model", 
        "owned_by": "cloud-hybrid"
    })
            
    return {"object": "list", "data": models}

# ---------------------------------------------------------
# Central Routing Control Tower
# ---------------------------------------------------------
@app.post("/v1/chat/completions")
async def handle_routing(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    
    if not messages:
        raise HTTPException(status_code=400, detail="Conversation payload is empty.")
        
    last_prompt = messages[-1].get("content", "")
    requested_model = body.get("model", "")
    
    # ---------------------------------------------------------
    # Route A: Multi-Agent Cloud Sandbox Code Engine (#codeagent)
    # ---------------------------------------------------------
    if "#codeagent" in last_prompt.lower():
        logger.info("⚡ Code Agent system invoked. Scaling to multi-agent sandbox execution loop...")
        cleaned_prompt = last_prompt.lower().replace("#codeagent", "").strip()
        return StreamingResponse(
            run_agent_team_stream(cleaned_prompt), 
            media_type="text/event-stream"
        )

    # ---------------------------------------------------------
    # Route B: Direct Cloud Fallback Secondary Opinion (#gemini)
    # ---------------------------------------------------------
    if "#gemini" in last_prompt.lower():
        logger.info(f"☁️ Direct Cloud Fallback activated. Routing single-turn request straight to {gemini_model}...")
        cleaned_prompt = last_prompt.lower().replace("#gemini", "").strip()
        
        # Flatten chat history into context block, parsing out custom routing flags
        formatted_contents = []
        for msg in messages[:-1]:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "").replace("#gemini", "").replace("#codeagent", "").strip()
            formatted_contents.append(f"{role.capitalize()}: {content}")
            
        formatted_contents.append(f"User: {cleaned_prompt}")
        full_context = "\n".join(formatted_contents)

        async def stream_direct_gemini():
            try:
                response_stream = gemini_client.models.generate_content_stream(
                    model=gemini_model,
                    contents=f"You are a helpful, highly accurate cloud AI assistant. Answer directly and precisely.\n\nContext:\n{full_context}"
                )
                
                for chunk in response_stream:
                    if chunk.text:
                        yield format_chunk(chunk.text)
                        
                final_payload = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(final_payload)}\n\n".encode('utf-8')
                yield b"data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"❌ Direct Gemini Stream Failure: {str(e)}")
                yield format_chunk(f"\n\n❌ Direct Cloud Fallback failed to reach target model: {str(e)}\n")
                yield b"data: [DONE]\n\n"

        return StreamingResponse(stream_direct_gemini(), media_type="text/event-stream")

    # ---------------------------------------------------------
    # Route C: Bare Metal Local Processing (Ollama GPU Pipeline)
    # ---------------------------------------------------------
    logger.info(f"🚀 Routing request directly to Local GPU cluster for model: {requested_model}")
    
    async def stream_local():
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Safe fallback logic if virtual model placeholder slips through without a routing flag
            if requested_model == "gemma4-agent":
                try:
                    ollama_models_resp = await client.get(f"{OLLAMA_URL.replace('/v1', '')}/api/tags")
                    if ollama_models_resp.status_code == 200:
                        available_models = ollama_models_resp.json().get("models", [])
                        if available_models:
                            real_model_name = available_models[0].get("model") or available_models[0].get("name")
                            logger.info(f"🔄 Swapping virtual model tag for top local asset: '{real_model_name}'")
                            body["model"] = real_model_name
                except Exception as e:
                    logger.warning(f"⚠️ Dynamic fallback mapping exception: {e}")

            try:
                async with client.stream("POST", f"{OLLAMA_URL}/chat/completions", json=body) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield format_chunk(f"❌ Upstream Ollama Cluster Error: {error_text.decode()}\n")
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                yield format_chunk(f"❌ Connection link to local Ollama daemon failed: {str(e)}\n")

    return StreamingResponse(stream_local(), media_type="text/event-stream")

# ---------------------------------------------------------
# ASGI Lifespan Runner (Keeps script alive via direct command line)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("📡 Launching AI Gateway Control Tower on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
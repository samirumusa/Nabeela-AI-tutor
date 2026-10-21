"""JSON-only Vast transport; existing multipart endpoints remain unchanged."""
import asyncio
import base64
import binascii
import json
import time
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Nabeela worker transport")
gate = asyncio.Lock()


class VoiceRequest(BaseModel):
    audio_base64: str = Field(min_length=1, max_length=8_000_000)


def decode_audio(value):
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Invalid base64 audio")
    if not data or len(data) > 6_000_000:
        raise HTTPException(413, "Audio must be between 1 byte and 6 MB")
    return data


@app.get("/ready")
async def ready():
    # Supervisor starts this process only after warming all three models.
    async with httpx.AsyncClient(timeout=5) as client:
        for url in ("http://127.0.0.1:8000/health", "http://127.0.0.1:8001/health", "http://127.0.0.1:7860/health"):
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError:
                raise HTTPException(503, "Model service unavailable")
    return {"ready": True}


@app.post("/voice")
async def voice(request: VoiceRequest):
    data = decode_audio(request.audio_base64)
    if gate.locked():
        raise HTTPException(429, "Worker busy; retry through the endpoint queue")
    async with gate:
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post("http://127.0.0.1:8000/api/voice/conversation",
                files={"audio": ("speech.wav", data, "application/octet-stream")},
                data={"language": "en", "voice": "af_heart"})
        if response.status_code != 200:
            raise HTTPException(response.status_code, "Voice processing failed; inspect private worker logs")
        result = response.json()
        elapsed = time.perf_counter() - start
        result["worker_elapsed_seconds"] = elapsed
        logging.getLogger("worker.metrics").warning(json.dumps({"event": "voice_turn", "elapsed_seconds": elapsed, "input_bytes": len(data)}))
        return result

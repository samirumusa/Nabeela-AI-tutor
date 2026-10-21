"""Minimal Kokoro English HTTP adapter; isolated from the existing provider."""
import io
from contextlib import asynccontextmanager
import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from kokoro import KPipeline

pipeline = None


@asynccontextmanager
async def lifespan(app):
    global pipeline
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cuda")
    # Load voice and exercise synthesis before reporting readiness.
    list(pipeline("Hello.", voice="af_heart"))
    yield


app = FastAPI(lifespan=lifespan)


class Speech(BaseModel):
    input: str = Field(min_length=1, max_length=5000)
    model: str = "kokoro"
    voice: str = "af_heart"
    response_format: str = "wav"


@app.get("/health")
def health():
    return {"ready": pipeline is not None}


@app.post("/v1/audio/speech")
def speech(req: Speech):
    if req.voice != "af_heart" or req.model != "kokoro" or req.response_format != "wav":
        raise HTTPException(400, "This worker supports kokoro / af_heart / wav only")
    chunks = [audio.cpu().numpy() if hasattr(audio, "cpu") else np.asarray(audio)
              for _, _, audio in pipeline(req.input, voice=req.voice)]
    if not chunks:
        raise HTTPException(422, "No audio generated")
    output = io.BytesIO()
    sf.write(output, np.concatenate(chunks), 24000, format="WAV", subtype="PCM_16")
    return Response(output.getvalue(), media_type="audio/wav")

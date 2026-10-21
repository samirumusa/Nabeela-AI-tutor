import base64
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from app.models import ChatRequest, SpeakRequest, VoiceTurnRequest
from app.providers.tutor import MockTutorProvider
from app.providers.tts import KokoroTTSProvider
from app.providers.asr import FasterWhisperASRProvider

app = FastAPI(title="Nabeela Backend", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

tutor = MockTutorProvider()
tts = KokoroTTSProvider()
asr = FasterWhisperASRProvider()

@app.get("/")
async def root():
    return {"name": "Nabeela Backend", "version": "0.2.0", "docs": "/docs", "health": "/health"}

@app.get("/health")
async def health():
    return {"status": "healthy", "asr": "faster-whisper", "tutor": "mock-natlas", "tts": "kokoro"}

@app.post("/api/tutor/chat")
async def chat(req: ChatRequest):
    return await tutor.chat(req.message, req.language)

@app.post("/api/voice/speak")
async def speak(req: SpeakRequest):
    try:
        audio, ctype = await tts.synthesize(req.text, req.voice)
        return Response(audio, media_type=ctype)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Kokoro TTS unavailable: {e}")

@app.post("/api/voice/turn")
async def turn(req: VoiceTurnRequest):
    answer = await tutor.chat(req.message, req.language)
    try:
        audio, ctype = await tts.synthesize(answer.text, req.voice)
        # Do not place Hausa tutor text in HTTP headers; headers are not a safe Unicode transport.
        return Response(audio, media_type=ctype)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Kokoro TTS unavailable: {e}")

@app.post("/api/asr/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
):
    if language not in {"auto", "en", "ha"}:
        raise HTTPException(400, "language must be auto, en, or ha")
    data = await audio.read()
    if not data:
        raise HTTPException(400, "audio file is empty")
    try:
        return await asr.transcribe(data, audio.filename or "speech.wav", language)
    except Exception as e:
        raise HTTPException(500, f"ASR transcription failed: {e}")

@app.post("/api/voice/conversation")
async def voice_conversation(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
    voice: str | None = Form(None),
):
    if language not in {"auto", "en", "ha"}:
        raise HTTPException(400, "language must be auto, en, or ha")
    data = await audio.read()
    if not data:
        raise HTTPException(400, "audio file is empty")

    try:
        transcript = await asr.transcribe(data, audio.filename or "speech.wav", language)
        if not transcript["text"]:
            raise HTTPException(422, "No speech was detected")

        tutor_language = transcript["detected_language"] if transcript["detected_language"] in {"en", "ha"} else "auto"
        answer = await tutor.chat(transcript["text"], tutor_language)
        output_audio, ctype = await tts.synthesize(answer.text, voice)

        return {
            "transcript": transcript["text"],
            "detected_language": transcript["detected_language"],
            "language_probability": transcript["language_probability"],
            "tutor_text": answer.text,
            "tutor_language": answer.language,
            "audio_base64": base64.b64encode(output_audio).decode("ascii"),
            "audio_content_type": ctype,
            "asr_provider": "faster-whisper",
            "tutor_provider": "mock-natlas",
            "tts_provider": "kokoro",
        }
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Kokoro TTS unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Voice conversation failed: {e}")

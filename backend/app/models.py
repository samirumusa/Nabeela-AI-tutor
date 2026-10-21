from typing import Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["en", "ha", "auto"] = "auto"

class ChatResponse(BaseModel):
    text: str
    language: Literal["en", "ha"]
    provider: str = "mock-natlas"

class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str | None = None

class VoiceTurnRequest(ChatRequest):
    voice: str | None = None

class TranscriptionResponse(BaseModel):
    text: str
    detected_language: str
    language_probability: float
    duration_seconds: float | None = None
    provider: str = "faster-whisper"

class VoiceConversationResponse(BaseModel):
    transcript: str
    detected_language: str
    language_probability: float
    tutor_text: str
    tutor_language: str
    audio_base64: str
    audio_content_type: str
    asr_provider: str = "faster-whisper"
    tutor_provider: str = "mock-natlas"
    tts_provider: str = "kokoro"

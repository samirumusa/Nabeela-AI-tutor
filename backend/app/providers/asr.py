import asyncio
import os
import tempfile
from functools import lru_cache
from faster_whisper import WhisperModel
from app.config import settings

@lru_cache(maxsize=1)
def _load_model() -> WhisperModel:
    # Lazy load: the backend can still start even before Whisper has downloaded.
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        cpu_threads=settings.whisper_cpu_threads,
    )

class FasterWhisperASRProvider:
    async def transcribe(self, audio: bytes, filename: str = "speech.wav", language: str = "auto"):
        suffix = os.path.splitext(filename or "speech.wav")[1] or ".wav"
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(audio)
                path = f.name

            return await asyncio.to_thread(self._transcribe_sync, path, language)
        finally:
            if path and os.path.exists(path):
                os.remove(path)

    def _transcribe_sync(self, path: str, language: str):
        model = _load_model()
        requested_language = None if language == "auto" else language

        # Keep temperature at 0 and do not add a grammar-correcting prompt.
        # For an English tutor we want to preserve learner mistakes in the transcript.
        segments, info = model.transcribe(
            path,
            task="transcribe",
            language=requested_language,
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "detected_language": info.language,
            "language_probability": float(info.language_probability),
            "duration_seconds": getattr(info, "duration", None),
        }

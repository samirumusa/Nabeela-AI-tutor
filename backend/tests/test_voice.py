import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from app.main import app
from app.models import ChatResponse


class VoiceTests(unittest.TestCase):
    def test_original_transcript_reaches_tutor_and_response(self):
        transcript = {"text": "Yesterday I go market", "detected_language": "en", "language_probability": 0.9}
        with patch("app.main.asr.transcribe", new=AsyncMock(return_value=transcript)), \
             patch("app.main.tutor.chat", new=AsyncMock(return_value=ChatResponse(text="Try again", language="en"))) as tutor, \
             patch("app.main.tts.synthesize", new=AsyncMock(return_value=(b"wav", "audio/wav"))):
            response = TestClient(app).post("/api/voice/conversation", files={"audio": ("test.wav", b"audio")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], transcript["text"])
        self.assertEqual(response.json()["audio_base64"], "d2F2")
        tutor.assert_awaited_once_with(transcript["text"], "en")

    def test_audio_validation_on_both_endpoints(self):
        client = TestClient(app)
        for endpoint in ("/api/asr/transcribe", "/api/voice/conversation"):
            self.assertEqual(client.post(endpoint, files={"audio": ("test.wav", b"")}).status_code, 400)
            self.assertEqual(client.post(endpoint, files={"audio": ("test.wav", b"audio")}, data={"language": "xx"}).status_code, 400)

    def test_no_speech_does_not_call_tutor(self):
        with patch("app.main.asr.transcribe", new=AsyncMock(return_value={"text": ""})), \
             patch("app.main.tutor.chat", new=AsyncMock()) as tutor:
            response = TestClient(app).post("/api/voice/conversation", files={"audio": ("test.wav", b"audio")})
        self.assertEqual(response.status_code, 422)
        tutor.assert_not_awaited()

"""Optional self-hosted English tutor. No hosted/paid API defaults."""
import httpx
from app.config import settings
from app.models import ChatResponse

POLICY = """You are Nabeela, a patient English tutor. Respond only in simple English.
Give one short, accurate correction when useful, then ask one relevant question
or ask the learner to retry. Do not invent learner errors. Preserve their intended
meaning. Assess the first attempt before helping. Never award mastery, XP or CEFR
promotion. Keep responses below 80 words. Do not output reasoning or markup."""


class QwenTutorProvider:
    async def chat(self, message: str, language: str = "auto") -> ChatResponse:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(settings.qwen_base_url.rstrip("/") + "/chat/completions", json={
                "model": settings.qwen_model,
                "messages": [{"role": "system", "content": POLICY}, {"role": "user", "content": message}],
                "max_tokens": 200, "temperature": 0.7,
                "chat_template_kwargs": {"enable_thinking": False},
            })
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip() or "<think>" in text:
            raise ValueError("Invalid tutor response")
        return ChatResponse(text=text.strip(), language="en", provider="qwen")

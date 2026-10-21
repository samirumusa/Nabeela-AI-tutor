import httpx
from app.config import settings
class KokoroTTSProvider:
    async def synthesize(self,text:str,voice:str|None=None):
        payload={"model":settings.kokoro_model,"input":text,"voice":voice or settings.kokoro_voice,"response_format":"wav"}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as c:
            r=await c.post(settings.kokoro_base_url.rstrip("/")+"/v1/audio/speech",json=payload)
            r.raise_for_status()
            return r.content,r.headers.get("content-type","audio/wav")

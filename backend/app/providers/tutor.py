from app.models import ChatResponse
class MockTutorProvider:
    async def chat(self,message:str,language:str="auto")->ChatResponse:
        t=message.strip().lower()
        if "go to kano yesterday" in t:
            return ChatResponse(text="Almost correct. Say: I went to Kano yesterday. Saboda kana magana game da abin da ya faru a baya, go ya koma went. Now say the corrected sentence again.",language="en")
        if "past tense of go" in t:
            return ChatResponse(text="The past tense of go is went. For example: Yesterday, I went to school.",language="en")
        if any(x in t for x in ("menene","hausa","bayani")):
            return ChatResponse(text="To. Zan yi bayani a taƙaice da Hausa. Go na nufin zuwa, went shi ne past tense, kuma gone ana amfani da shi tare da have ko has. Now give me one English sentence using went.",language="ha")
        if t.startswith(("hello","hi","good morning")):
            return ChatResponse(text="Hello! I'm Nabeela, your English tutor. Tell me in English: what did you do today?",language="en")
        return ChatResponse(text="Good attempt. Tell me a little more in English using a complete sentence.",language="en")

"""Run on the GPU test host after services start; no third-party dependencies.

python infrastructure/docker/smoke.py
"""
import json
import urllib.request


def post(url, payload):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.headers, response.read()


def main():
    headers, body = post("http://127.0.0.1:8001/v1/chat/completions", {
        "model": "nabeela-qwen", "messages": [
            {"role": "system", "content": "You are an English tutor. Give one short correction and ask the learner to retry. Do not assign mastery or CEFR levels."},
            {"role": "user", "content": "Yesterday I go market."}],
        "max_tokens": 150, "temperature": 0.7,
        "chat_template_kwargs": {"enable_thinking": False},
    })
    answer = json.loads(body)["choices"][0]["message"]["content"]
    if not answer or "<think>" in answer:
        raise RuntimeError("Expected a non-empty non-thinking tutor response")
    print("Tutor response:", answer)
    headers, audio = post("http://127.0.0.1:7860/v1/audio/speech", {
        "model": "kokoro", "input": "Hello. Tell me what you did yesterday.",
        "voice": "af_heart", "response_format": "wav",
    })
    if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise RuntimeError("Kokoro did not return WAV audio")
    print("Kokoro WAV bytes:", len(audio))
    print("Next: upload an English recording to backend /api/asr/transcribe; check nvidia-smi peak memory.")


if __name__ == "__main__":
    main()

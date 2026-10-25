"""Check Kokoro's English tokenizer before spending time loading GPU models."""
import importlib.metadata
import platform
import io
import wave


PACKAGES = ("kokoro", "misaki", "spacy", "thinc", "cymem", "preshed",
            "murmurhash", "numpy", "en-core-web-sm", "faster-whisper", "av")


def check_audio_decoder():
    """Exercise the actual Whisper decoder without downloading ASR weights."""
    from faster_whisper.audio import decode_audio
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\0\0" * 2400)
    audio.seek(0)
    samples = decode_audio(audio, sampling_rate=16000)
    if samples.size == 0:
        raise RuntimeError("Whisper audio decoder produced no samples")
    print("[speech-preflight] Whisper audio decoder OK", flush=True)


def main():
    print(f"[speech-preflight] Python {platform.python_version()}", flush=True)
    for name in PACKAGES:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = "NOT INSTALLED"
        print(f"[speech-preflight] {name}={version}", flush=True)

    print("[speech-preflight] Loading English tokenizer (no GPU/model download)", flush=True)
    import spacy
    nlp = spacy.load("en_core_web_sm")
    tokens = list(nlp.make_doc("Hello. I'd like some chicken, please."))
    if not tokens:
        raise RuntimeError("English tokenizer produced no tokens")
    print("[speech-preflight] English tokenizer OK", flush=True)
    check_audio_decoder()


if __name__ == "__main__":
    main()

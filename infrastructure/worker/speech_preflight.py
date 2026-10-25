"""Check Kokoro's English tokenizer before spending time loading GPU models."""
import importlib.metadata
import platform


PACKAGES = ("kokoro", "misaki", "spacy", "thinc", "cymem", "preshed",
            "murmurhash", "numpy", "en-core-web-sm")


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


if __name__ == "__main__":
    main()

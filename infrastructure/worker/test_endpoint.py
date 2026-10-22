"""Manual paid-cloud test client; importing this file makes no network calls."""
import argparse
import asyncio
import base64
import getpass
import json
import os
from pathlib import Path
import time
import re


def safe_error(error, key):
    message = str(error).replace(key, "[REDACTED]") if key else str(error)
    message = re.sub(r"https?://[^\s]+", "[URL omitted]", message)
    message = re.sub(r"(?i)(bearer\s+)[^\s,}\"']+", r"\1[REDACTED]", message)
    message = re.sub(r'''(?i)((?:api_key|token|authorization|audio_base64)["']?\s*[:=]\s*["']?)[^\s,}\"']+''', r"\1[REDACTED]", message)
    return message[:1000] or "No error details supplied"


def extract_reply(response):
    result = response.get("response", response)
    if not isinstance(result, dict) or not isinstance(result.get("tutor_text"), str):
        raise ValueError("Endpoint did not return a successful voice response; inspect worker logs")
    audio = base64.b64decode(result["audio_base64"], validate=True)
    if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise ValueError("Endpoint returned invalid WAV audio")
    return result, audio


async def send(endpoint, data, timeout):
    return await asyncio.wait_for(endpoint.request("/voice",
        {"audio_base64": base64.b64encode(data).decode("ascii")},
        cost=1, retry=False, timeout=timeout), timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description="Send one short English recording to Vast; incurs cloud usage.")
    parser.add_argument("audio", type=Path, nargs="?")
    parser.add_argument("--list-endpoints", action="store_true", help="List accessible endpoint names without requesting GPU inference")
    parser.add_argument("--endpoint", default="qr6suj00")
    parser.add_argument("--output", type=Path, default=Path("tutor-reply.wav"))
    parser.add_argument("--timeout", type=float, default=360)
    args = parser.parse_args()
    if not args.list_endpoints and (args.audio is None or not args.audio.is_file() or not 0 < args.audio.stat().st_size <= 6_000_000):
        parser.error("Choose an existing recording between 1 byte and 6 MB")
    if not args.list_endpoints and args.output.exists():
        parser.error("Output already exists; choose a new --output filename")
    if args.timeout <= 0:
        parser.error("Timeout must be positive")
    try:
        from vastai import Serverless
    except ImportError:
        parser.error("Install the optional client: python -m pip install vastai")
    if Serverless is None:
        parser.error("Installed Vast SDK has no working Serverless client")
    key = (os.environ.get("VAST_API_KEY") or getpass.getpass("Vast API key (hidden): ")).strip()
    if not key.strip():
        parser.error("API key is required")
    async def run():
        async with Serverless(api_key=key) as client:
            if args.list_endpoints:
                endpoints = await client.get_endpoints()
                return [endpoint.name for endpoint in endpoints]
            print(f"Looking up endpoint {args.endpoint}...", flush=True)
            endpoint = await client.get_endpoint(args.endpoint)
            print(f"Sending one recording to {args.endpoint}; cloud charges may apply.", flush=True)
            return await send(endpoint, args.audio.read_bytes(), args.timeout)
    start = time.perf_counter()
    try:
        response = asyncio.run(asyncio.wait_for(run(), timeout=args.timeout))
        if args.list_endpoints:
            print("Accessible endpoint names:", json.dumps(response))
            return
        result, audio = extract_reply(response)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            output.write(audio)
    except Exception as error:
        # Avoid dumping SDK request headers or the complete audio response.
        print(f"Test failed ({type(error).__name__}): {safe_error(error, key)}")
        raise SystemExit(1)
    print(json.dumps({"transcript": result.get("transcript"), "tutor_text": result["tutor_text"],
        "tutor_provider": result.get("tutor_provider"), "worker_elapsed_seconds": result.get("worker_elapsed_seconds"),
        "client_elapsed_seconds": round(time.perf_counter() - start, 2), "audio_saved_to": str(args.output)}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

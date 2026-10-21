"""PID 1 supervisor: bounded startup, warmup, fail-fast children and shutdown."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import httpx

VOICE_PYTHON = "/opt/voice/bin/python"


def stop_children(children):
    for child in reversed(children):
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 15
    for child in reversed(children):
        try:
            child.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def wait_ready(url, children, deadline):
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("Model process exited during startup; inspect service logs")
        try:
            if httpx.get(url, timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise TimeoutError(f"Model startup timed out: {url}")


def main():
    if not os.environ.get("MASTER_TOKEN") or not os.environ.get("WORKER_PORT"):
        raise RuntimeError("Vast MASTER_TOKEN and WORKER_PORT must be injected at deployment")
    children, logs = [], []
    def shutdown(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    def launch(name, command):
        log = open(f"/tmp/nabeela-{name}.log", "a", buffering=1)
        logs.append(log)
        children.append(subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT))
    try:
        deadline = time.monotonic() + int(os.environ.get("STARTUP_TIMEOUT_SECONDS", "1800"))
        launch("qwen", [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
            "--model", "Qwen/Qwen3-8B-AWQ", "--served-model-name", "nabeela-qwen",
            "--quantization", "awq", "--dtype", "half", "--max-model-len", "4096",
            "--max-num-seqs", "1", "--gpu-memory-utilization", "0.50", "--enforce-eager",
            "--host", "127.0.0.1", "--port", "8001"])
        wait_ready("http://127.0.0.1:8001/health", children, deadline)
        launch("kokoro", [VOICE_PYTHON, "-m", "uvicorn", "infrastructure.worker.kokoro_server:app", "--host", "127.0.0.1", "--port", "7860"])
        wait_ready("http://127.0.0.1:7860/health", children, deadline)
        launch("backend", [VOICE_PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])
        wait_ready("http://127.0.0.1:8000/health", children, deadline)
        with httpx.Client(timeout=300) as client:
            result = client.post("http://127.0.0.1:7860/v1/audio/speech", json={"input": "Yesterday I went to the market.", "voice": "af_heart"})
            result.raise_for_status()
            Path("/tmp/nabeela-benchmark.wav").write_bytes(result.content)
            # Exercise all services before advertising readiness.
            result = client.post("http://127.0.0.1:8000/api/voice/conversation", files={"audio": ("warmup.wav", result.content)}, data={"language": "en"})
            result.raise_for_status()
        launch("gateway", [VOICE_PYTHON, "-m", "uvicorn", "infrastructure.worker.gateway:app", "--host", "127.0.0.1", "--port", "18000"])
        wait_ready("http://127.0.0.1:18000/ready", children, deadline)
        Path("/tmp/nabeela-ready.log").write_text("NABEELA_READY\n")
        launch("vast", [VOICE_PYTHON, "-m", "infrastructure.worker.worker"])
        print("Nabeela models warmed; Vast worker started", flush=True)
        while True:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A worker service exited; terminating the combined worker")
            time.sleep(1)
    finally:
        stop_children(children)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()

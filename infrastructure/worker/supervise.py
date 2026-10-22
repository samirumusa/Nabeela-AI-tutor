"""PID 1 supervisor: bounded startup, warmup, fail-fast children and shutdown."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import threading
from datetime import datetime, timezone
import httpx

VOICE_PYTHON = "/opt/voice/bin/python"


def progress(message):
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"{stamp} [supervisor] {message}", flush=True)


def secret_values():
    return tuple(value for key, value in os.environ.items()
                 if any(word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
                 and len(value) >= 8)


def relay_output(name, pipe, logfile, output, secrets):
    """Drain continuously so a verbose child cannot block on a full stdout pipe."""
    try:
        for raw in iter(pipe.readline, b""):
            line = raw.decode("utf-8", errors="replace")
            for value in secrets:
                line = line.replace(value, "[REDACTED]")
            logfile.write(line)
            logfile.flush()
            try:
                output.write(f"[{name}] {line}")
                output.flush()
            except (BrokenPipeError, OSError):
                # Continue draining and retaining the local log if stdout closes.
                pass
    finally:
        pipe.close()
        logfile.close()


def launch_service(name, command, children, relays):
    logfile = open(f"/tmp/nabeela-{name}.log", "a", encoding="utf-8", buffering=1)
    progress(f"Starting {name}")
    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except BaseException:
        logfile.close()
        raise
    children.append(child)
    thread = threading.Thread(target=relay_output,
        args=(name, child.stdout, logfile, sys.stdout, secret_values()), daemon=True)
    thread.start()
    relays.append(thread)
    return child


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


def wait_ready(url, children, deadline, stage="service"):
    next_update = 0
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("Model process exited during startup; inspect service logs")
        try:
            if httpx.get(url, timeout=5).status_code == 200:
                progress(f"{stage} ready")
                return
        except httpx.HTTPError:
            pass
        if time.monotonic() >= next_update:
            progress(f"Waiting for {stage}; startup budget remaining: {max(0, int(deadline - time.monotonic()))} seconds")
            next_update = time.monotonic() + 30
        time.sleep(2)
    raise TimeoutError(f"Model startup timed out: {url}")


def main():
    if not os.environ.get("MASTER_TOKEN") or not os.environ.get("WORKER_PORT"):
        raise RuntimeError("Vast MASTER_TOKEN and WORKER_PORT must be injected at deployment")
    children, relays = [], []
    def shutdown(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    def launch(name, command):
        launch_service(name, command, children, relays)
    try:
        deadline = time.monotonic() + int(os.environ.get("STARTUP_TIMEOUT_SECONDS", "1800"))
        launch("qwen", [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
            "--model", "Qwen/Qwen3-8B-AWQ", "--served-model-name", "nabeela-qwen",
            "--quantization", "awq", "--dtype", "half", "--max-model-len", "4096",
            "--max-num-seqs", "1", "--gpu-memory-utilization", "0.50", "--enforce-eager",
            "--host", "127.0.0.1", "--port", "8001"])
        wait_ready("http://127.0.0.1:8001/health", children, deadline, "Qwen")
        launch("kokoro", [VOICE_PYTHON, "-m", "uvicorn", "infrastructure.worker.kokoro_server:app", "--host", "127.0.0.1", "--port", "7860"])
        wait_ready("http://127.0.0.1:7860/health", children, deadline, "Kokoro")
        launch("backend", [VOICE_PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])
        wait_ready("http://127.0.0.1:8000/health", children, deadline, "backend")
        progress("Generating English warmup audio (request timeout: 300 seconds)")
        with httpx.Client(timeout=300) as client:
            result = client.post("http://127.0.0.1:7860/v1/audio/speech", json={"input": "Yesterday I went to the market.", "voice": "af_heart"})
            result.raise_for_status()
            Path("/tmp/nabeela-benchmark.wav").write_bytes(result.content)
            # Exercise all services before advertising readiness.
            progress("Warming Whisper -> Qwen -> Kokoro (request timeout: 300 seconds)")
            result = client.post("http://127.0.0.1:8000/api/voice/conversation", files={"audio": ("warmup.wav", result.content)}, data={"language": "en"})
            result.raise_for_status()
        launch("gateway", [VOICE_PYTHON, "-m", "uvicorn", "infrastructure.worker.gateway:app", "--host", "127.0.0.1", "--port", "18000"])
        wait_ready("http://127.0.0.1:18000/ready", children, deadline, "voice gateway")
        Path("/tmp/nabeela-ready.log").write_text("NABEELA_READY\n")
        launch("vast", [VOICE_PYTHON, "-m", "infrastructure.worker.worker"])
        print("Nabeela models warmed; Vast worker started", flush=True)
        while True:
            for child in children:
                code = child.poll()
                if code is not None:
                    raise RuntimeError(f"Worker subprocess PID {child.pid} exited with code {code}; terminating the combined worker")
            time.sleep(1)
    finally:
        progress("Stopping worker services")
        stop_children(children)
        for relay in relays:
            relay.join(timeout=5)


if __name__ == "__main__":
    main()

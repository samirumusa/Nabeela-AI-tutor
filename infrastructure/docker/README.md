# Cloud image builds: first stage

This packages Qwen3-8B-AWQ (4-bit), the existing FastAPI/faster-whisper backend,
and Kokoro as three isolated Linux amd64 GPU services. It does not yet implement
the combined Vast serverless worker. No paid resources are launched by these files.
The application still uses MockTutorProvider: Qwen is tested directly through its
OpenAI-compatible endpoint. Existing endpoints and local defaults are unchanged.
No database migrations apply. N-ATLaS and Hausa TTS are outside this image set.

## Build without local Docker

1. Push this project to a GitHub repository you control. Keep `.env`, audio,
   benchmark results, credentials, model weights and virtual environments out of Git.
2. In GitHub Actions select **Build Nabeela inference images**, then **Run workflow**.
   Leave **publish** disabled for a build-only run; this checks image construction,
   not GPU inference. GitHub Actions minutes/storage may have costs for your account.
3. Run again with publish enabled to publish to GHCR. The workflow uses the scoped
   GitHub token, not a token copied into an image. Verify each package is **Private**
   in GHCR before granting access or deployment. Existing package visibility is not
   changed by this workflow.
4. The tags are `ghcr.io/<lowercase-owner>/nabeela-backend:sha-<full-commit-sha>`,
   `nabeela-qwen` and `nabeela-kokoro`. Record published image digests and sizes from
   the build outputs. No image has been built or published until Actions succeeds.

Model weights for Qwen and Whisper download at runtime into separate caches.
Kokoro's upstream image may already contain model assets. This trades image size
against cold-start downloads. Registry image layers, extracted layers, model caches,
and temporary downloads all consume disk; measure them before choosing a final size.
The vLLM version is pinned; Kokoro is digest-pinned. Resolve the other base images
to digests after the initial build is verified, and record model revisions before a
repeatable performance benchmark. Python transitive dependencies are not yet locked.

Local checks (no Docker, model downloads or cloud required):

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s infrastructure/docker -p test_smoke.py -v
```

## GPU smoke test (cloud host only)

Use Linux with Docker Compose supporting `gpus: all`, NVIDIA Container Toolkit,
one 24 GB NVIDIA GPU, at least 32 GB RAM and 8 allocated CPU cores. Do not reinstall
Docker or download weights on the development PC for this test.

```bash
export NABEELA_IMAGE_PREFIX=ghcr.io/YOUR_LOWERCASE_OWNER
export NABEELA_IMAGE_TAG=sha-YOUR_FULL_COMMIT_SHA
# Authenticate with a registry read token through docker login --password-stdin.
docker compose -f infrastructure/docker/compose.yaml pull
docker compose -f infrastructure/docker/compose.yaml up -d
docker compose -f infrastructure/docker/compose.yaml logs -f
python3 infrastructure/docker/smoke.py
```

All published ports bind to localhost. Use an SSH tunnel for remote testing.
Qwen has no public authentication configured; do not change bindings to expose it.
The application /health means process liveness, not model readiness. Whisper loads
on its first request. Test ASR through Swagger with `language=en` and real English
learner recordings, and verify errors survive. Smoke checks alone do not establish
teaching quality, ASR accuracy, or concurrency. Start with one outstanding voice turn.

Qwen is limited to 50% GPU memory, one sequence and 4,096 context tokens, with eager
execution to reduce graph-capture memory. Every Qwen request must set
`chat_template_kwargs: {"enable_thinking": false}`. Keep replies short; this is
a serving prototype, not a session/history implementation. If OOM occurs, capture
`nvidia-smi` and service logs before changing limits. Measure cold/warm latency and
VRAM rather than assuming all services fit or that five users can speak concurrently.

```bash
docker compose -f infrastructure/docker/compose.yaml down
```

Named volumes remain after `down`. Keeping caches costs storage; deleting them
requires re-downloading models. Stop/destroy the rented cloud resources separately:
Compose shutdown does not stop Vast host billing.

## Vast template status

This Compose stack is for a Docker-capable cloud host. A normal Vast Docker
container does not automatically support running Compose inside it. Do not paste
one of these images into Vast Serverless expecting the entire stack to run.
The next stage needs a custom PyWorker and process supervisor (or a supported
multi-service VM deployment), readiness integration, secret injection and metering.
No fabricated template ID or worker launch command is supplied here.

References:
- https://huggingface.co/Qwen/Qwen3-8B-AWQ
- https://docs.vllm.ai/en/stable/deployment/docker/
- https://github.com/remsky/Kokoro-FastAPI/pkgs/container/kokoro-fastapi-gpu
- https://github.com/SYSTRAN/faster-whisper

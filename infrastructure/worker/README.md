# Combined Vast serverless worker (GPU validation pending)

The `nabeela-worker` image starts Qwen3-8B-AWQ, Kokoro-82M, the existing ASR/backend,
a JSON gateway, and Vast's authenticated PyWorker. It does not run Docker inside
Docker. All model services bind to loopback. Only the Vast worker port is exposed.
Local backend still defaults to the mock; the combined image explicitly selects Qwen.
The standalone Kokoro image is unchanged. This worker uses a new minimal HTTP adapter
for the same Kokoro model/voice. No database migration or cloud launch is performed.

## Build and publish

Push changes, run the existing Build Nabeela inference images workflow with publish
off first, then enable publish after success. It now has a fourth `worker` job.
That build checks the actual Vast SDK imports. The SDK is not pinned yet: record
the working version and lock it after verifying its compatibility with Vast's
current platform. Build success does not establish CUDA compatibility or memory fit.
Keep the package private. No tokens or learner recordings belong in the image.

Image: `ghcr.io/<owner>/nabeela-worker:sha-<full-commit-sha>`.
Use its published digest in the final template. This image can be large because
vLLM and speech runtime dependencies coexist; measure its extracted size and model
download footprint before renting disk. Model weights download at worker startup,
not during cloud build, into `/models/huggingface`.

The small `en_core_web_sm` 3.8.0 spaCy pipeline is an explicit image dependency
installed from its versioned upstream wheel (compatible with spaCy >=3.8,<3.9).
It is not committed to Git. The Docker build loads and exercises its tokenizer
using the same preflight as startup, without a GPU or Qwen/Kokoro weight download.
A missing model or tokenizer load failure now fails the build before publication.
This addresses the preflight E050 missing-model error; it does not establish that
the earlier tokenizer OverflowError or full GPU pipeline has been resolved.

## Vast template

- Docker ENTRYPOINT launch mode; use the new worker image, not the three old images.
- Private GHCR credentials with package read permission, entered only in Vast.
- Expose TCP `3000`; set `WORKER_PORT=3000` and `WORKER_HTTP_PORT=3001`.
- Keep `UNSECURED=false`; do not expose internal 8000/8001/7860/18000 ports.
- Vast must inject its worker `MASTER_TOKEN` and reporting configuration. Never use
  the account API key as MASTER_TOKEN. Merely renting the image is not equivalent
  to registering a worker with a serverless endpoint. Preserve Vast's required
  worker environment when attaching this custom template.
- `STARTUP_TIMEOUT_SECONDS=1800` bounds the polling portion of first startup;
  full-pipeline warmup additionally allows up to 300 seconds per HTTP request.
- 24 GB NVIDIA GPU, 32 GB RAM, 8 CPU cores is a test target, not measured capacity.
- Maximum one worker for the pilot, min load/workers/cold capacity zero, positive
  inactivity timeout (initially 300 seconds). Confirm current field names in Vast.

The supervisor loads Qwen first with half the GPU budget, 4K context, one sequence,
and eager mode. It then loads Kokoro and warms ASR -> Qwen -> Kokoro using generated
English audio. It starts the gateway and PyWorker only after success. A child exit
terminates all other services; SIGTERM/SIGINT stop children with a bounded grace
period. Service stdout and stderr are streamed to the main container log with
`[qwen]`, `[kokoro]`, `[backend]`, `[gateway]`, and `[vast]` prefixes. Copies remain
under `/tmp/nabeela-*.log`. Known secret environment values (tokens, passwords,
secrets and API keys at least eight characters long) are redacted in both copies;
this is not a guarantee that third-party logs contain no sensitive data. Inspect
logs before sharing. No SSH server or public diagnostic port is needed.

The supervisor prints a start/ready message per service, a waiting update every
30 seconds during readiness polling, warmup stage messages, and subprocess exit
codes. Long warmup requests can be quiet for up to their 300-second timeout.
Look at container/application logs rather than only the host's image-pull logs.
These messages begin only after Docker has downloaded and started the image;
they cannot diagnose a stalled image pull. The final models-warmed message means
the Vast process was launched, not that the endpoint has accepted authentication.

Rebuild and publish after pushing these changes, then update the template to the
new commit tag. Existing containers keep the old logging behavior until recreated.

## Diagnosing speech startup without a shell

The image entrypoint now prints `[speech-preflight]` dependency versions and loads
the English spaCy tokenizer before Qwen starts. A tokenizer failure exits immediately
with its traceback, avoiding repeated Qwen loading before the same Kokoro failure.
This check does not fix dependencies or download models. Rebuild/publish and select
the new image digest to use it.

For an existing image, put the following in a Vast startup-script facility that
runs shell commands **before** the image entrypoint. Confirm that facility's execution
order; do not launch a second supervisor if the entrypoint already runs one:

```bash
#!/bin/bash
/opt/voice/bin/python -u - <<'PY'
import importlib.metadata as metadata
import platform
print('[speech-diagnostic] Python', platform.python_version(), flush=True)
for name in ('kokoro', 'misaki', 'spacy', 'thinc', 'cymem', 'preshed', 'murmurhash', 'numpy', 'en-core-web-sm'):
    try:
        version = metadata.version(name)
    except metadata.PackageNotFoundError:
        version = 'NOT INSTALLED'
    print(f'[speech-diagnostic] {name}={version}', flush=True)
import spacy
spacy.load('en_core_web_sm')
print('[speech-diagnostic] English tokenizer OK', flush=True)
PY
```

Read container/application logs for these lines and the traceback. The inline
script works with older images without the new preflight module. It deliberately
does not install or upgrade packages at startup. Installed versions are needed
before selecting a reproducible dependency fix.

## Calling the endpoint

From repository root on Windows, install only the client SDK and send one short,
consented English recording (this incurs cloud usage):

```powershell
.\backend\.venv\Scripts\python.exe -m pip install vastai
.\backend\.venv\Scripts\python.exe infrastructure/worker/test_endpoint.py backend/benchmarks/audio/error-001.wav --endpoint qr6suj00 --output tutor-reply.wav
```

The client prompts for the Vast account API key with hidden input (or reads
VAST_API_KEY). No model weights download to this PC. It prints transcript, tutor
reply and timings, and saves WAV audio without overwriting an existing file.
It sends one request, with retries disabled and a 360-second overall deadline.
Client timeout does not shut down the GPU or guarantee cancellation of inference.
Stop the endpoint separately when finished. Keep returned learner information private.

The initial Vast route is POST `/voice` with JSON:

```json
{"audio_base64": "<base64-encoded short English recording>"}
```

Send it through the Vast Serverless client from a trusted backend using its account
key, not directly from a mobile app. Do not paste keys into Git or template text.
The transport forces English and af_heart for this pilot. Maximum decoded audio is
6 MB; use short turns. Existing multipart `/api/voice/conversation` remains available
internally without a contract change. PyWorker serializes the route; the gateway
also returns 429 for overlapping calls. Errors do not silently switch to mock.

The response contains the normal voice fields plus `worker_elapsed_seconds`.
Private logs record turn duration and input bytes, not a transcript or audio payload.
The constant per-turn workload estimate and two synthetic full-pipeline benchmark
requests are initial capacity estimates only. They consume GPU time. Real speaking
turn duration, concurrency, first-audio latency, billed startup/idle time and VRAM
must be measured during a capped GPU test. This is a single-turn prototype without
conversation history, curriculum state, or mastery promotion. Existing English/Hausa
local behavior is preserved; the new live Qwen worker intentionally responds in English.

## Checks without GPUs or model downloads

From repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s infrastructure/worker -p test_worker.py -v
```

Run backend tests from `backend/` as usual. The tests mock network/model services;
they do not prove that the combined image starts on a GPU. Required deployment gate:
build -> private publish -> authenticated single-worker GPU smoke test -> measure
readiness, output audio, transcript preservation, shutdown, peak VRAM and actual bill.

References used for the adapter:
- https://github.com/vast-ai/pyworker
- https://github.com/vast-ai/vast-sdk/blob/main/vastai/serverless/server/worker.py
- https://github.com/hexgrad/kokoro

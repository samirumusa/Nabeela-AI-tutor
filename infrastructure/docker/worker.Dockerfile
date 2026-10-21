FROM vllm/vllm-openai:v0.10.2
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-venv espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
# Reuse GPU PyTorch from vLLM, but isolate speech/SDK package changes.
RUN python3 -m venv --system-site-packages /opt/voice
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN /opt/voice/bin/pip install --no-cache-dir -r /tmp/backend-requirements.txt \
    kokoro==0.9.4 soundfile==0.13.1 vastai nvidia-cudnn-cu12
WORKDIR /app
COPY backend/app /app/app
COPY infrastructure/worker /app/infrastructure/worker
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME=/models/huggingface \
    TUTOR_PROVIDER=qwen QWEN_BASE_URL=http://127.0.0.1:8001/v1 \
    KOKORO_BASE_URL=http://127.0.0.1:7860 WHISPER_DEVICE=cuda \
    WHISPER_COMPUTE_TYPE=int8_float16 WHISPER_CPU_THREADS=8
# Resolve cuDNN/cuBLAS paths in the voice environment before launching services.
COPY infrastructure/worker/entrypoint.sh /usr/local/bin/nabeela-start
RUN sed -i 's/\r$//' /usr/local/bin/nabeela-start && chmod +x /usr/local/bin/nabeela-start \
    && /opt/voice/bin/python -c "from vastai import Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig; assert all(x is not None for x in (Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig)), 'Vast serverless imports unavailable'; from kokoro import KPipeline; import faster_whisper"
EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/nabeela-start"]
CMD []

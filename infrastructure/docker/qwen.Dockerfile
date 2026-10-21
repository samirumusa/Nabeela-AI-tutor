FROM vllm/vllm-openai:v0.10.2
# Weights are downloaded at runtime, never embedded in this image.
ENV HF_HOME=/root/.cache/huggingface
CMD ["--model", "Qwen/Qwen3-8B-AWQ", "--served-model-name", "nabeela-qwen", "--quantization", "awq", "--dtype", "half", "--max-model-len", "4096", "--max-num-seqs", "1", "--gpu-memory-utilization", "0.50", "--enforce-eager", "--host", "0.0.0.0", "--port", "8000"]

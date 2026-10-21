# Infrastructure
Current development is local. Kokoro runs as a separate Docker service on port 7860 and FastAPI on port 8000. Future deployment should keep model providers separable and support CPU/local development plus GPU production inference where required.

Cloud image definitions, a manual GHCR build workflow, and GPU test instructions
are now in [docker/README.md](docker/README.md). The Vast serverless worker integration
is implemented in [worker/README.md](worker/README.md) and awaits GPU validation.

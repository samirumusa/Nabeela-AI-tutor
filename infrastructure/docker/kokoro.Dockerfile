FROM ghcr.io/remsky/kokoro-fastapi-gpu:v0.9.0-cu126@sha256:c6036341ec71d2d2c5bdffb339f7985ab9e7a7f7e6694c3f7f172258247de939
# Preserve upstream model files, startup command, and HTTP speech API.
EXPOSE 8880

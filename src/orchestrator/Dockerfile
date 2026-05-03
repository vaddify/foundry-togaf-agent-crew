FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

WORKDIR /app

# Install deps first for cache friendliness
COPY pyproject.toml ./
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir .

# App code
COPY src ./src

# Foundry hosted-agent contract: /invocations + /health on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "src.orchestrator.server:app", "--host", "0.0.0.0", "--port", "8080"]

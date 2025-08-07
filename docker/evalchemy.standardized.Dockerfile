# VLLM Evaluation Container - Evalchemy Framework
# Standardized version with consistent parameters and structure
FROM python:3.11-slim

# Standardized metadata
LABEL maintainer="Thaki Cloud MLOps Team"
LABEL framework="evalchemy"
LABEL version="1.1.0"
LABEL description="VLLM evaluation container with embedded evalchemy configs and tasks"
LABEL gpu.required="false"

# Standardized environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    TOKENIZERS_PARALLELISM=false

# System packages installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    jq \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Standardized working directory
WORKDIR /app

# Python dependencies
COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

# Framework-specific files
COPY datasets/ /app/datasets/
COPY eval/evalchemy/ /app/eval/evalchemy/
COPY configs/evalchemy.json /app/configs/eval_config.json
COPY scripts/standardize_evalchemy.py /app/scripts/standardize_evalchemy.py

# Create standardized directories
RUN mkdir -p /app/results /app/parsed /app/cache

# Set execution permissions
RUN chmod +x /app/eval/evalchemy/run_evalchemy.sh

# Create non-root user with standardized name
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app

USER evaluser

# Standardized environment variables
ENV EVAL_FRAMEWORK="evalchemy" \
    EVAL_CONFIG_PATH="/app/configs/eval_config.json" \
    MODEL_ENDPOINT="http://localhost:8000/v1/completions" \
    OUTPUT_DIR="/app/results" \
    PARSED_DIR="/app/parsed" \
    LOG_LEVEL="INFO" \
    BATCH_SIZE="1" \
    MAX_TOKENS="14000" \
    NUM_FEWSHOT="1" \
    LIMIT="1" \
    BACKEND_API="http://model-benchmark-backend-svc:8000" \
    PYTHONPATH="/app"

# Standardized volumes
VOLUME ["/app/results", "/app/parsed", "/app/cache"]

# Standardized healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set working directory to framework location
WORKDIR /app/eval/evalchemy

# Standardized entrypoint
ENTRYPOINT ["./run_evalchemy.sh"]
CMD []

# Standardized usage documentation
# docker build -f docker/evalchemy.standardized.Dockerfile -t vllm-eval/evalchemy:latest .
#
# docker run --rm \
#   -v $(pwd)/results:/app/results \
#   -v $(pwd)/parsed:/app/parsed \
#   -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e MODEL_NAME="qwen3-8b" \
#   -e LOG_LEVEL="DEBUG" \
#   vllm-eval/evalchemy:latest
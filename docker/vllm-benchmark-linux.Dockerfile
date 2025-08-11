# VLLM Evaluation Container - VLLM Benchmark Framework
# Standardized version with consistent parameters and structure

# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Standardized environment variables for build
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VLLM_TARGET_DEVICE=cpu

# Build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git curl libnuma-dev \
    gcc-12 g++-12 python3-dev && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 20 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-12 && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel packaging cmake ninja setuptools-scm>=8 numpy pandas datasets

# Clone and build VLLM
RUN git clone https://github.com/vllm-project/vllm.git /tmp/vllm
WORKDIR /tmp/vllm

# RUN pip install -v -r requirements/cpu.txt \
#     --extra-index-url https://download.pytorch.org/whl/cpu && \
#     VLLM_TARGET_DEVICE=cpu python setup.py install

# Use below for linux/amd
RUN pip install vllm[cpu] --extra-index-url https://download.pytorch.org/whl/cpu

# Copy benchmarks directory
RUN mkdir -p /app && \
    cp -r /tmp/vllm/benchmarks /app/benchmarks

# Stage 2: Runtime stage
FROM python:3.11-slim

# Standardized metadata
LABEL maintainer="Thaki Cloud MLOps Team"
LABEL framework="vllm-benchmark"
LABEL version="1.1.0"
LABEL description="VLLM performance benchmarking container with serving benchmarks"
LABEL gpu.required="false"

# Standardized environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

# System packages installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Standardized working directory
WORKDIR /app

# Copy from build stage
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/benchmarks /app/benchmarks

# Framework-specific files
COPY configs/vllm_benchmark.json /app/configs/eval_config.json
COPY eval/vllm-benchmark/ /app/scripts/
COPY scripts/standardize_vllm_benchmark.py /app/scripts/standardize_vllm_benchmark.py

# Copy framework scripts and setup directories (exactly matching working version)
RUN cp /app/scripts/*.sh /app/ && \
    cp /app/scripts/*.py /app/ && \
    chmod +x /app/*.sh /app/*.py && \
    chmod +x /app/benchmarks/benchmark_serving.py && \
    printf '#!/bin/bash\npython -c "import requests; print(\\"Ready\\")"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

RUN mkdir -p /app/results && chmod 777 /app/results
RUN mkdir -p /app/parsed && chmod 777 /app/parsed

# Create non-root user (standardized)
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app /opt/venv

USER evaluser

# Standardized environment variables
ENV EVAL_FRAMEWORK="vllm-benchmark" \
    EVAL_CONFIG_PATH="/app/configs/eval_config.json" \
    MODEL_ENDPOINT="http://localhost:8000" \
    ENDPOINT_PATH="/v1/chat/completions" \
    OUTPUT_DIR="/app/results" \
    PARSED_DIR="/app/parsed" \
    LOG_LEVEL="INFO" \
    BATCH_SIZE="1" \
    NUM_PROMPTS="100" \
    REQUEST_RATE="1.0" \
    MAX_CONCURRENCY="1" \
    RANDOM_INPUT_LEN="512" \
    RANDOM_OUTPUT_LEN="128" \
    BACKEND="vllm" \
    DATASET_TYPE="random" \
    BACKEND_API="http://model-benchmark-backend-svc:8000" \
    PYTHONPATH="/app"

# Standardized volumes
VOLUME ["/app/results", "/app/parsed", "/app/cache"]

# Standardized healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Standardized entrypoint
ENTRYPOINT ["/app/run_vllm_benchmark.sh"]
CMD []

# Standardized usage documentation
# docker build -f docker/vllm-benchmark.Dockerfile -t vllm-eval/vllm-benchmark:latest .
#
# docker run --rm \
#   -v $(pwd)/results:/app/results \
#   -v $(pwd)/parsed:/app/parsed \
#   -e MODEL_ENDPOINT="http://host.docker.internal:8000" \
#   -e MODEL_NAME="qwen3-8b" \
#   -e NUM_PROMPTS="100" \
#   -e REQUEST_RATE="2.0" \
#   vllm-eval/vllm-benchmark:latest
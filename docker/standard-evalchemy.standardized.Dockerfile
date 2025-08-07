# VLLM Evaluation Container - Standard Evalchemy Framework
# Standardized version with consistent parameters and structure
FROM python:3.11-slim

# Standardized metadata
LABEL maintainer="Thaki Cloud MLOps Team"
LABEL framework="standard-evalchemy"
LABEL version="1.1.0"
LABEL description="VLLM evaluation container with ThakiCloud/evalchemy fork for standard benchmarks"
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
    python3-dev \
    cmake \
    ninja-build \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libnuma-dev \
    vim \
    less \
    htop \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Standardized working directory
WORKDIR /app

# Python dependencies
COPY requirements-dev.txt* /app/
RUN pip install --upgrade pip setuptools wheel && \
    pip install "IPython<8.0.0" && \
    if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# Install torch and vllm
RUN pip install --no-cache-dir torch vllm

# Clone and install evalchemy
ARG CACHEBUST=1
RUN echo "Caching disabled at: $CACHEBUST" && \
    rm -rf evalchemy-src && \
    git clone --recurse-submodules https://github.com/ThakiCloud/evalchemy.git /app/evalchemy-src

# Install evalchemy and dependencies
WORKDIR /app/evalchemy-src
RUN sed -i 's|.*penfever/PyExt.*|# &|' pyproject.toml && \
    pip install --no-cache-dir --no-deps -e . && \
    pip install --no-cache-dir --no-deps -e eval/chat_benchmarks/alpaca_eval && \
    pip install --no-cache-dir datasets transformers accelerate bespokelabs-curator

# Framework-specific files
RUN mkdir -p /app/configs /app/scripts /app/results /app/parsed /app/cache
COPY eval/standard_evalchemy/ /app/eval/standard_evalchemy/
COPY configs/standard_evalchemy.json /app/configs/eval_config.json
COPY scripts/standardize_evalchemy.py /app/scripts/standardize_evalchemy.py

# Create non-root user with standardized name
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app

USER evaluser

# Standardized environment variables
ENV EVAL_FRAMEWORK="standard-evalchemy" \
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
    PYTHONPATH="/app/evalchemy-src:/app"

# Standardized volumes
VOLUME ["/app/results", "/app/parsed", "/app/cache"]

# Standardized healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import eval.eval; print('evalchemy healthy')" || exit 1

# Set execution permissions
RUN chmod +x /app/eval/standard_evalchemy/run_evalchemy.sh

# Set working directory to framework location
WORKDIR /app/evalchemy-src

# Standardized entrypoint
ENTRYPOINT ["/app/eval/standard_evalchemy/run_evalchemy.sh"]
CMD []

# Standardized usage documentation
# docker build --build-arg CACHEBUST="$(date +%s)" -f docker/standard-evalchemy.standardized.Dockerfile -t vllm-eval/standard-evalchemy:latest .
#
# docker run --rm \
#   -v $(pwd)/results:/app/results \
#   -v $(pwd)/parsed:/app/parsed \
#   -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e MODEL_NAME="qwen3-8b" \
#   -e LOG_LEVEL="DEBUG" \
#   vllm-eval/standard-evalchemy:latest
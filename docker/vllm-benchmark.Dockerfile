# Stage 1: 빌드 스테이지
FROM python:3.11-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VLLM_TARGET_DEVICE=cpu

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential cmake ninja-build git curl libnuma-dev \
      gcc-12 g++-12 python3-dev && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 20 \
                        --slave /usr/bin/g++ g++ /usr/bin/g++-12 && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel packaging cmake ninja setuptools-scm>=8 numpy

RUN git clone https://github.com/vllm-project/vllm.git /tmp/vllm
WORKDIR /tmp/vllm

RUN pip install -v -r requirements/cpu.txt \
      --extra-index-url https://download.pytorch.org/whl/cpu && \
    VLLM_TARGET_DEVICE=cpu python setup.py install

# 전체 benchmarks 디렉토리 복사 (모든 의존성 포함)
RUN mkdir -p /app && \
    cp -r /tmp/vllm/benchmarks /app/benchmarks

# Stage 2: 런타임 스테이지
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/benchmarks /app/benchmarks

COPY configs/ /app/configs/
COPY scripts/ /app/scripts/

RUN cp /app/scripts/*.sh /app/ && \
    cp /app/scripts/*.py /app/ && \
    chmod +x /app/*.sh /app/*.py && \
    chmod +x /app/benchmarks/benchmark_serving.py && \
    printf '#!/bin/bash\npython -c "import requests; print(\\"Ready\\")"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

RUN useradd --create-home --shell /bin/bash benchuser && \
    chown -R benchuser:benchuser /app /opt/venv

USER benchuser

ENV VLLM_ENDPOINT="http://localhost:8000" \
    ENDPOINT_PATH="/v1/chat/completions" \
    MODEL_NAME="Qwen/Qwen3-8B" \
    SERVED_MODEL_NAME="qwen3-8b" \
    OUTPUT_DIR="/results" \
    PARSED_DIR="/parsed" \
    NUM_PROMPTS="100" \
    REQUEST_RATE="1.0" \
    MAX_CONCURRENCY="1" \
    RANDOM_INPUT_LEN="512" \
    RANDOM_OUTPUT_LEN="128" \
    BACKEND="vllm" \
    DATASET_TYPE="random" \
    PERCENTILE_METRICS="ttft,tpot,itl,e2el" \
    METRIC_PERCENTILES="25,50,75,90,95,99" \
    LOG_LEVEL="INFO"

VOLUME ["/results", "/parsed"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

ENTRYPOINT ["/app/run_vllm_benchmark.sh"]

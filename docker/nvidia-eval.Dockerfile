# VLLM Evaluation Container - NVIDIA Eval Framework  
# Standardized version with consistent parameters and structure
FROM python:3.11-slim

# Standardized metadata
LABEL maintainer="Thaki Cloud MLOps Team"
LABEL framework="nvidia-eval"
LABEL version="1.1.0"
LABEL description="VLLM evaluation container for NVIDIA AIME and LiveCodeBench benchmarks"
LABEL gpu.required="false"

# Environment variables (adding SSL/network vars from working version)
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    CLASSPATH="/usr/local/lib/antlr-4.11.1-complete.jar:$CLASSPATH" \
    PYTHONHTTPSVERIFY=0 \
    CURL_CA_BUNDLE="" \
    REQUESTS_CA_BUNDLE="" \
    HF_HUB_DISABLE_PROGRESS_BARS=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# Standardized working directory
WORKDIR /app

# System packages installation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    jq \
    build-essential \
    ca-certificates \
    openjdk-17-jre-headless \
    dnsutils \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# pip upgrade with SSL fixes (from working version)
RUN pip install --no-cache-dir --upgrade pip \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org

# Python dependencies with trusted hosts (from working version)
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    requests \
    urllib3 \
    tqdm \
    datasets==2.17.0 \
    transformers \
    numpy \
    pandas \
    sympy \
    antlr4-python3-runtime==4.11.1

# ANTLR JAR installation
RUN wget https://www.antlr.org/download/antlr-4.11.1-complete.jar -O /usr/local/lib/antlr-4.11.1-complete.jar

# Network connectivity test script (enhanced version from working dockerfile)
RUN echo '#!/bin/bash\n\
echo "=== Network Connectivity Test ==="\n\
echo "Testing basic internet connectivity..."\n\
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then\n\
    echo "✓ Internet connectivity: OK"\n\
else\n\
    echo "✗ Internet connectivity: FAILED"\n\
fi\n\
echo "Testing DNS resolution..."\n\
if nslookup google.com > /dev/null 2>&1; then\n\
    echo "✓ DNS resolution: OK"\n\
else\n\
    echo "✗ DNS resolution: FAILED"\n\
fi\n\
echo "Testing HuggingFace connectivity..."\n\
if curl -s --connect-timeout 10 --insecure https://huggingface.co > /dev/null; then\n\
    echo "✓ HuggingFace connectivity: OK"\n\
else\n\
    echo "✗ HuggingFace connectivity: FAILED"\n\
fi\n\
echo "=== Test Complete ==="\n' > /usr/local/bin/test-network \
    && chmod +x /usr/local/bin/test-network

# Framework-specific files (copy to /app but maintain structure like working version)
COPY eval/nvidia_eval/*.sh /app/
COPY eval/nvidia_eval/*.py /app/
COPY eval/nvidia_eval/data/ /app/data/
COPY eval/nvidia_eval/tools/ /app/tools/

# Standardization scripts directory
RUN mkdir -p /app/scripts
COPY scripts/standardize_aime_results.py /app/scripts/
COPY scripts/standardize_livecodebench_results.py /app/scripts/

# Copy ANTLR JAR if exists in tools (from working version)
RUN if [ -f /app/tools/latex2sympy/antlr-4.11.1-complete.jar ]; then \
    cp /app/tools/latex2sympy/antlr-4.11.1-complete.jar /usr/local/lib/; \
    fi

# CRITICAL: Script modifications for API mode (from working version)
RUN sed -i '/python inference.py/a\    ${MODEL_ENDPOINT:+--api-base "${MODEL_ENDPOINT}"} \\' /app/generate_aime.sh && \
    sed -i '/python inference.py/a\    ${MODEL_ENDPOINT:+--api-base "${MODEL_ENDPOINT}"} \\' /app/generate_livecodebench.sh && \
    sed -i 's/for (( gpu=0; gpu<GPUS; gpu++ )); do/# API mode - single execution/' /app/generate_aime.sh && \
    sed -i 's/for (( gpu=0; gpu<GPUS; gpu++ )); do/# API mode - single execution/' /app/generate_livecodebench.sh && \
    sed -i 's/--device-id "${gpu}" &/# --device-id removed for API mode/' /app/generate_aime.sh && \
    sed -i 's/--device-id "${gpu}" &/# --device-id removed for API mode/' /app/generate_livecodebench.sh && \
    sed -i 's/seed=$(( seed + 1 ))/# seed increment removed/' /app/generate_aime.sh && \
    sed -i 's/seed=$(( seed + 1 ))/# seed increment removed/' /app/generate_livecodebench.sh && \
    sed -i 's/done/# done/' /app/generate_aime.sh && \
    sed -i 's/done/# done/' /app/generate_livecodebench.sh && \
    sed -i 's/wait/# wait/' /app/generate_aime.sh && \
    sed -i 's/wait/# wait/' /app/generate_livecodebench.sh

# MAX_TOKENS default values (from working version)
RUN sed -i 's/--max-output-len "${MAX_TOKENS}"/--max-output-len "${MAX_TOKENS:-32768}"/' /app/generate_aime.sh && \
    sed -i 's/--max-output-len "${MAX_TOKENS}"/--max-output-len "${MAX_TOKENS:-14000}"/' /app/generate_livecodebench.sh

# Set execution permissions
RUN chmod +x /app/*.sh

# Create directories (standardized)
RUN mkdir -p /app/cache /app/results /app/parsed

# Create non-root user (standardized)
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app

USER evaluser

# Environment variables (standardized with results/parsed)
ENV EVAL_FRAMEWORK="nvidia-eval" \
    MODEL_ENDPOINT="http://localhost:8000/v1" \
    OUTPUT_DIR="/app/results" \
    PARSED_DIR="/app/parsed" \
    MAX_TOKENS="32768" \
    EVAL_TYPE="both" \
    LOG_LEVEL="INFO" \
    BACKEND_API="http://model-benchmark-backend-svc:8000" \
    PYTHONPATH="/app"

# Standardized volumes
VOLUME ["/app/results", "/app/parsed", "/app/cache"]

# Standardized healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -x /usr/local/bin/test-network || exit 1

# CMD section (matching working version logic but adapted for /app)
CMD echo "=== Starting AceReason Evaluation Toolkit ===" && \
    test-network && \
    echo "" && \
    if [ "$EVAL_TYPE" = "aime" ]; then \
        bash /app/run_aime.sh "$MODEL_NAME" "$OUTPUT_DIR" 1 "${MAX_TOKENS:-32768}"; \
    elif [ "$EVAL_TYPE" = "lcb" ]; then \
        bash /app/run_livecodebench.sh "$MODEL_NAME" "$OUTPUT_DIR" 1 "${MAX_TOKENS:-14000}"; \
    elif [ "$EVAL_TYPE" = "both" ]; then \
        bash /app/run_aime.sh "$MODEL_NAME" "$OUTPUT_DIR" 1 "${MAX_TOKENS:-32768}" && \
        bash /app/run_livecodebench.sh "$MODEL_NAME" "$OUTPUT_DIR" 1 "${MAX_TOKENS:-14000}"; \
    else \
        echo "Usage: docker run -e MODEL_ENDPOINT=http://server:8000/v1 -e MODEL_NAME=model -e OUTPUT_DIR=output -e EVAL_TYPE=[aime|lcb|both] image"; \
        echo "Optional: -e MAX_TOKENS=32768"; \
    fi

# Labels (from working version)
LABEL description="Optimized lightweight Docker image for AceReason Toolkit - API mode only with network fixes"

# Usage documentation (updated to new filename)
# docker build -f docker/nvidia-eval.Dockerfile -t vllm-eval/nvidia-eval:latest .
#
# Run both AIME and LiveCodeBench:
# docker run --rm \
#   -v $(pwd)/results:/app/results \
#   -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1" \
#   -e MODEL_NAME="qwen3-8b" \
#   -e OUTPUT_DIR="/app/results" \
#   -e EVAL_TYPE="both" \
#   -e MAX_TOKENS="32768" \
#   vllm-eval/nvidia-eval:latest
#
# Run only AIME:
# docker run --rm \
#   -v $(pwd)/results:/app/results \
#   -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1" \
#   -e MODEL_NAME="qwen3-8b" \
#   -e OUTPUT_DIR="/app/results" \
#   -e EVAL_TYPE="aime" \
#   -e MAX_TOKENS="32768" \
#   vllm-eval/nvidia-eval:latest
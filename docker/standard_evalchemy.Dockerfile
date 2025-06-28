# VLLM Evaluation Container (Evalchemy)
# Evalchemy 평가를 위한 컨테이너
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="VLLM Eval Team"
LABEL description="VLLM evalchemy evaluation container with ThakiCloud/evalchemy fork"
LABEL version="2.1.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    TOKENIZERS_PARALLELISM=false

# 시스템 패키지 설치 (evalchemy와 vllm 빌드에 필요한 도구들 포함)
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

# 비특권 사용자 생성 및 HOME 디렉토리 설정
RUN groupadd -r evaluser && useradd -r -g evaluser -m -d /home/evaluser evaluser

WORKDIR /app

# requirements-dev.txt가 있다면 복사
COPY requirements-dev.txt* /app/

# IPython 버전을 제한하여 호환성 문제 해결
RUN pip install --upgrade pip setuptools wheel
RUN pip install "IPython<8.0.0"

# 기본 패키지들 설치 (requirements-dev.txt가 있다면)
RUN if [ -f requirements-dev.txt ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

# torch와 vllm 설치
RUN pip install --no-cache-dir torch
RUN pip install --no-cache-dir vllm

# evalchemy 소스 클론 및 설치
ARG CACHEBUST=1
RUN echo "Caching disabled at: $CACHEBUST" \
    && rm -rf evalalchemy-src \
    && git clone --recurse-submodules https://github.com/ThakiCloud/evalchemy.git /app/evalchemy-src

RUN echo "==================== AIME24 DEBUG START ====================" && \
    if [ -f /app/evalchemy-src/eval/chat_benchmarks/AIME24/data/aime24.json ]; then \
        echo "FILE FOUND: aime24.json" && \
        wc -l /app/evalchemy-src/eval/chat_benchmarks/AIME24/data/aime24.json && \
        head -10 /app/evalchemy-src/eval/chat_benchmarks/AIME24/data/aime24.json && \
        echo "... (truncated)" && \
        tail -5 /app/evalchemy-src/eval/chat_benchmarks/AIME24/data/aime24.json ; \
    else \
        echo "FILE NOT FOUND: aime24.json" && \
        find /app/evalchemy-src -name "*.json" | grep -i aime || echo "No AIME JSON files found" ; \
    fi && \
    echo "==================== AIME24 DEBUG END ======================"

# 작업 디렉토리를 evalchemy 소스로 변경
WORKDIR /app/evalchemy-src

# 문제가 되는 pyext 의존성 주석 처리
RUN sed -i 's|.*penfever/PyExt.*|# &|' pyproject.toml

# evalchemy 설치 (--no-deps로 의존성 충돌 방지)
RUN pip install --no-cache-dir --no-deps -e .

# 필요한 추가 의존성들 개별 설치
RUN pip install --no-cache-dir --no-deps -e eval/chat_benchmarks/alpaca_eval

# 필요한 추가 의존성들 개별 설치
RUN pip install --no-cache-dir datasets transformers accelerate

# bespokelabs curator 패키지 설치 (curator_lm.py에서 필요)
RUN pip install --no-cache-dir bespokelabs-curator

# 평가 설정 파일들을 올바른 위치에 복사
RUN mkdir -p /app/evalchemy-src/results
COPY eval/standard_evalchemy/ /app/eval/standard_evalchemy/
COPY configs/standard_evalchemy.json /app/configs/eval_config.json
COPY scripts/standardize_evalchemy.py /app/scripts/standardize_evalchemy.py

# 디렉토리 권한 설정
RUN chown -R evaluser:evaluser /app /home/evaluser

# 비특권 사용자로 전환
USER evaluser

# 기본 환경 변수 설정
ENV EVAL_CONFIG_PATH="/app/configs/eval_config.json" \
    VLLM_MODEL_ENDPOINT="http://vllm:8000/v1/completions" \
    OUTPUT_DIR="/app/evalchemy-src/results" \
    MAX_TOKENS="14000" \
    LIMIT="1" \
    LOG_LEVEL="INFO" \
    MODEL_NAME="qwen3-8b" \
    TOKENIZER="Qwen/Qwen3-8B" \
    TOKENIZER_BACKEND="huggingface" \
    PYTHONPATH="/app/evalchemy-src:/app" \
    BACKEND_API="http://model-benchmark-backend-svc:8000"

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import eval.eval; print('evalchemy healthy')" || exit 1

# 실행 스크립트 권한 설정 및 기본 명령어
RUN chmod +x /app/eval/standard_evalchemy/run_evalchemy.sh

# ENTRYPOINT와 CMD 설정 - 인자 전달 가능하도록
ENTRYPOINT ["/app/eval/standard_evalchemy/run_evalchemy.sh"]

#
# Example docker run command:
# docker run --rm \
#   -v $(pwd)/results:/app/evalchemy-src/results \
#   -e VLLM_MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e LOG_LEVEL="DEBUG" \
#   evalchemy-runner
#
# 빌드 및 실행 명령어들:
#
# 1. 이미지 빌드:
# docker build --build-arg CACHEBUST="$(date +%s)" -f docker/evalchemy.Dockerfile -t vllm-eval/evalchemy:latest .
#-v $(pwd)/parsed:/app/eval/standard_evalchemy/parsed
# 2. 기본 실행 (결과를 호스트에 마운트):
# docker run --rm \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   -e VLLM_MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e LOG_LEVEL="DEBUG" \
#   vllm-eval/evalchemy:latest
#
# 7. 커스텀 모델로 실행:
# docker run --rm \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   -e VLLM_MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e MODEL_NAME="llama3-8b" \
#   -e TOKENIZER="meta-llama/Llama-3-8B" \
#   -e TOKENIZER_BACKEND="huggingface" \
#   vllm-eval/evalchemy:latest
#
# 3. 네트워크 모드로 실행 (VLLM 서버와 직접 연결):
# docker run --rm \
#   --network host \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   -e VLLM_MODEL_ENDPOINT="http://vllm:8000/v1/completions" \
#   vllm-eval/evalchemy:latest
#
# 4. 디버깅 모드 (인터랙티브):
# docker run --rm -it \
#   --entrypoint /bin/bash \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   vllm-eval/evalchemy:latest
#
# 5. 설정 검증만 실행:
# docker run --rm \
#   vllm-eval/evalchemy:latest --validate-config
#
# 6. 사용 가능한 벤치마크 목록 확인:
# docker run --rm \
#   vllm-eval/evalchemy:latest --list-benchmarks
#
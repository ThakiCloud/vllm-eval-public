# VLLM Evaluation Container (Standard Evalchemy)
# 표준 Evalchemy 평가를 위한 컨테이너
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="VLLM Eval Team"
LABEL description="VLLM standard evalchemy evaluation container with enhanced debugging"
LABEL version="2.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    TOKENIZERS_PARALLELISM=false

# 시스템 패키지 설치 (디버깅 도구 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    jq \
    build-essential \
    vim \
    less \
    htop \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성
WORKDIR /app

# Python 의존성 파일 복사 및 설치
COPY requirements-dev.txt /app/requirements-dev.txt

# Python 패키지 설치 (lm-eval 최신 버전과 추가 패키지)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt && \
    pip install --no-cache-dir \
        lm-eval[api] \
        openai \
        anthropic \
        torch \
        transformers \
        accelerate \
        datasets \
        huggingface-hub \
        tokenizers \
        numpy \
        scipy \
        scikit-learn \
        requests \
        aiohttp

# 평가 시스템 파일 복사
COPY datasets/ /app/datasets/
COPY eval/standard_evalchemy/ /app/eval/standard_evalchemy/
COPY scripts/standardize_evalchemy.py /app/scripts/standardize_evalchemy.py
COPY configs/standard_evalchemy.json /app/configs/standard_evalchemy.json

# 스크립트 실행 권한 부여
RUN chmod +x /app/eval/standard_evalchemy/run_evalchemy.sh && \
    chmod +x /app/scripts/*.py 2>/dev/null || true

# 결과 디렉토리 생성
RUN mkdir -p /app/eval/standard_evalchemy/results && \
    mkdir -p /app/logs

# 비root 사용자 생성 및 권한 설정
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app && \
    usermod -aG staff evaluser

USER evaluser

# 기본 환경 변수
ENV EVAL_CONFIG_PATH="/app/configs/standard_evalchemy.json" \
    VLLM_MODEL_ENDPOINT="http://vllm:8000/v1/completions" \
    OUTPUT_DIR="/app/eval/standard_evalchemy/results" \
    LOG_LEVEL="INFO" \
    BATCH_SIZE="1" \
    MAX_LENGTH="2048" \
    TEMPERATURE="0.0" \
    TOP_P="1.0" \
    GPU_DEVICE="cpu"

# 작업 디렉토리를 standard_evalchemy로 설정
WORKDIR /app/eval/standard_evalchemy

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 기본 실행 명령 (환경변수와 기본 config 사용)
ENTRYPOINT ["./run_evalchemy.sh"]
CMD []

#
# 빌드 및 실행 명령어들:
#
# 1. 이미지 빌드:
# docker build -f docker/standard_evalchemy.Dockerfile -t vllm-eval/standard-evalchemy:latest .
#
# 2. 기본 실행 (결과를 호스트에 마운트):
# docker run --rm \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   -e VLLM_MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
#   -e LOG_LEVEL="DEBUG" \
#   vllm-eval/standard-evalchemy:latest
#
# 3. 네트워크 모드로 실행 (VLLM 서버와 직접 연결):
# docker run --rm \
#   --network host \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   -e VLLM_MODEL_ENDPOINT="http://localhost:8000/v1/completions" \
#   vllm-eval/standard-evalchemy:latest
#
# 4. 디버깅 모드 (인터랙티브):
# docker run --rm -it \
#   --entrypoint /bin/bash \
#   -v $(pwd)/results:/app/eval/standard_evalchemy/results \
#   vllm-eval/standard-evalchemy:latest
#
# 5. 설정 검증만 실행:
# docker run --rm \
#   vllm-eval/standard-evalchemy:latest --validate-config
#
# 6. 사용 가능한 벤치마크 목록 확인:
# docker run --rm \
#   vllm-eval/standard-evalchemy:latest --list-benchmarks
#


# VLLM Evaluation Container (All-in-One)
# 설정과 태스크가 모두 내장된 간단한 평가 컨테이너
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="VLLM Eval Team"
LABEL description="VLLM evaluation container with embedded configs and tasks"
LABEL version="1.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    jq \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성
WORKDIR /app

# Python 의존성 파일 복사
COPY requirements-dev.txt /app/requirements-dev.txt

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements-dev.txt

# 평가 시스템 파일 복사 (설정과 태스크 포함)
COPY datasets/ /app/datasets/
COPY eval/evalchemy/ /app/eval/evalchemy/
COPY configs/evalchemy.json /app/configs/eval_config.json
COPY scripts/standardize_evalchemy.py /app/scripts/standardize_evalchemy.py

# run_evalchemy.sh 실행 권한 부여
RUN chmod +x /app/eval/evalchemy/run_evalchemy.sh

# 비root 사용자 생성
RUN useradd --create-home --shell /bin/bash evaluser && \
    chown -R evaluser:evaluser /app

USER evaluser

# 기본 환경 변수
ENV EVAL_CONFIG_PATH="/app/configs/evalchemy.json" \
    VLLM_MODEL_ENDPOINT="http://vllm:8000/v1/completions" \
    LOG_LEVEL="INFO" \
    MODEL_NAME="qwen3-8b" \
    TOKENIZER="Qwen/Qwen3-8B" \
    TOKENIZER_BACKEND="huggingface" \
    BACKEND_API="http://model-benchmark-backend-svc:8000"

# 작업 디렉토리를 evalchemy로 설정
WORKDIR /app/eval/evalchemy

# 기본 실행 명령 (환경변수와 기본 config 사용)
ENTRYPOINT ["./run_evalchemy.sh"]
CMD [] 
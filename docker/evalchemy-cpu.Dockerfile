# Evalchemy Container for VLLM Evaluation System (API-only version)
# Optimized for API-based model evaluation without local model downloads
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="ThakiCloud <tech@company.com>"
LABEL description="Evalchemy evaluation container (API-only) for VLLM models"
LABEL version="2.0.0-api"
LABEL source="https://github.com/EleutherAI/lm-evaluation-harness"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 시스템 패키지 업데이트 및 필수 패키지 설치
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN python3 -m pip install --upgrade pip setuptools wheel

# 작업 디렉토리 생성
WORKDIR /app

# LM Evaluation Harness 저장소 클론 (API 지원)
RUN git clone https://github.com/EleutherAI/lm-evaluation-harness.git /app/lm-eval && \
    cd /app/lm-eval && \
    git checkout main

# API 전용 평가 패키지 설치 (모델 로딩 패키지 제외)
# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
    lm-eval[api]>=0.4.0 \
    scikit-learn>=1.3.0 \
    scipy>=1.11.0 \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    requests>=2.31.0 \
    pyyaml>=6.0.0 \
    tqdm>=4.65.0 \
    jsonlines>=4.0.0 \
    nltk>=3.8.0 \
    rouge-score>=0.1.2 \
    sacrebleu>=2.3.0 \
    openai>=1.0.0 \
    anthropic>=0.25.0 \
    tiktoken>=0.5.0 \
    protobuf>=4.21.0

# NLTK 데이터 다운로드
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# 평가 스크립트 및 설정 파일 복사
COPY eval/evalchemy/ /app/eval/evalchemy/
COPY scripts/ /app/scripts/

# API 기반 Evalchemy 래퍼 스크립트 복사
COPY docker/evalchemy_api_wrapper.py /app/evalchemy_api_wrapper.py
RUN chmod +x /app/evalchemy_api_wrapper.py

# 헬스체크 스크립트 복사
COPY docker/evalchemy_healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# 비root 사용자 생성 (보안)
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# 기본 환경 변수 (API 전용)
ENV MODEL_ENDPOINT="" \
    OPENAI_API_KEY="" \
    ANTHROPIC_API_KEY="" \
    CONFIG_FILE="/app/eval/evalchemy/configs/eval_config.json" \
    RESULTS_PATH="/results" \
    LOG_LEVEL=INFO \
    API_TIMEOUT=300 \
    MAX_RETRIES=3 \
    BATCH_SIZE=1

# 볼륨 마운트 포인트
VOLUME ["/data", "/results", "/configs"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# 기본 실행 명령
ENTRYPOINT ["python3", "/app/evalchemy_api_wrapper.py"]
CMD ["--config", "/app/eval/evalchemy/configs/eval_config.json", "--model-endpoint", "${MODEL_ENDPOINT}", "--output", "/results/evalchemy_results.json"] 
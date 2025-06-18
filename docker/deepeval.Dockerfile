# Deepeval Container for VLLM Evaluation System
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="ThakiCloud <tech@company.com>"
LABEL description="Deepeval evaluation container for VLLM models"
LABEL version="1.0.0"

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

# 작업 디렉토리 생성
WORKDIR /app

# Python 의존성 설치
COPY requirements-deepeval.txt .
RUN pip install --no-cache-dir -r requirements-deepeval.txt

# NumPy 최신 안정 버전 설치
# hadolint ignore=DL3013
RUN pip install --no-cache-dir "numpy>=1.24.0,<3.0"

# Deepeval 및 추가 패키지 설치 (PyTorch 제외)
# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
    deepeval[all]==1.1.7 \
    openai==1.58.1 \
    anthropic==0.40.0 \
    pytest==8.3.4 \
    pytest-asyncio==0.24.0 \
    pytest-xdist==3.6.0 \
    pytest-html==4.1.1 \
    pytest-json-report==1.5.0 \
    pandas==2.2.3 \
    scikit-learn==1.5.2 \
    nltk==3.9.1 \
    spacy==3.8.2 \
    transformers==4.47.1 \
    sentence-transformers==3.3.1 \
    rouge-score==0.1.2 \
    bert-score==0.3.13 \
    requests==2.32.3 \
    pyyaml==6.0.2 \
    tqdm==4.67.1 \
    datasets==3.2.0 \
    huggingface-hub==0.26.5

# PyTorch CPU 버전 별도 설치
# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
    torch==2.5.1 \
    torchvision==0.20.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu

# BLEURT 별도 설치 (Git 저장소에서)
# hadolint ignore=DL3013
RUN pip install --no-cache-dir git+https://github.com/google-research/bleurt.git

# NLTK 데이터 다운로드
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# spaCy 모델 다운로드
RUN python -m spacy download en_core_web_sm

# 평가 코드 복사
COPY eval/deepeval_tests/ /app/eval/deepeval_tests/
COPY scripts/ /app/scripts/

# 설정 파일 복사
COPY configs/ /app/configs/

# 헬스체크 스크립트 생성
RUN printf '#!/bin/bash\npython -c "import deepeval; print(\\"Deepeval ready\\")"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# 비root 사용자 생성 (보안)
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# 기본 환경 변수
ENV DEEPEVAL_TELEMETRY_OPT_OUT=YES \
    OPENAI_API_KEY="" \
    ANTHROPIC_API_KEY="" \
    MODEL_ENDPOINT="" \
    DATASET_PATH="/data" \
    RESULTS_PATH="/results" \
    LOG_LEVEL=INFO

# 볼륨 마운트 포인트
VOLUME ["/data", "/results", "/configs"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# 기본 실행 명령
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["eval/deepeval_tests/", "-v", "--json-report", "--json-report-file=/results/deepeval_results.json"]

# 컨테이너 실행 예시:
# docker run -v $(pwd)/data:/data -v $(pwd)/results:/results \
#   -e OPENAI_API_KEY=your_key \
#   -e MODEL_ENDPOINT=http://vllm-server:8000/v1 \
#   ghcr.io/your-org/vllm-eval-deepeval:latest

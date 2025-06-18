# Evalchemy Container for VLLM Evaluation System
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# 메타데이터
LABEL maintainer="ThakiCloud <tech@company.com>"
LABEL description="Evalchemy evaluation container for VLLM models with GPU support"
LABEL version="1.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda

ENV PATH=${CUDA_HOME}/bin:${PATH} \
    LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    curl \
    wget \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 3.11을 기본으로 설정
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# pip 업그레이드
RUN python3 -m pip install --upgrade pip setuptools wheel

# 작업 디렉토리 생성
WORKDIR /app

# PyTorch 및 GPU 관련 패키지 설치 (CUDA 11.8 지원)
RUN pip install --no-cache-dir \
    torch==2.1.2+cu118 \
    torchvision==0.16.2+cu118 \
    torchaudio==2.1.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# Evalchemy 및 lm-evaluation-harness 설치 (all extras 없이 설치)
RUN pip install --no-cache-dir lm-eval==0.4.2

# 추가 패키지 설치 (lm-eval 의존성과 호환되는 버전들)
RUN pip install --no-cache-dir \
    accelerate==0.21.0 \
    transformers==4.33.3 \
    bitsandbytes==0.41.1 \
    scipy==1.11.4 \
    pandas==2.0.3 \
    scikit-learn==1.3.2 \
    requests==2.31.0 \
    pyyaml==6.0.1 \
    tqdm==4.66.1 \
    wandb==0.15.12 \
    tensorboard==2.14.1 \
    jsonlines==4.0.0 \
    nltk==3.8.1 \
    rouge-score==0.1.2 \
    sacrebleu==2.3.1

# 추가 평가 관련 패키지
RUN pip install --no-cache-dir \
    openai==1.40.0 \
    anthropic==0.34.0 \
    google-generativeai==0.3.2 \
    tiktoken==0.5.2 \
    sentencepiece==0.1.99 \
    protobuf==4.25.1

# Korean evaluation 지원을 위한 패키지
RUN pip install --no-cache-dir \
    konlpy==0.6.0 \
    kiwipiepy==0.17.0 \
    soynlp==0.0.493

# NLTK 데이터 다운로드
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# HuggingFace cache 디렉토리 설정
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers

# 평가 스크립트 및 설정 파일 복사
COPY eval/evalchemy/ /app/eval/evalchemy/
COPY scripts/ /app/scripts/

# lm-eval 래퍼 스크립트 생성
RUN cat > /app/eval_wrapper.py << 'EOF'
#!/usr/bin/env python3
"""
Evalchemy evaluation wrapper script
lm-evaluation-harness를 사용하여 표준 벤치마크를 실행합니다.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evaluation(config_file: str, model_endpoint: str, output_file: str) -> Dict:
    """평가 실행."""
    logger.info(f"평가 시작: {config_file}")
    
    # 설정 파일 로드
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    results = {}
    
    for task_name, task_config in config.get('tasks', {}).items():
        if not task_config.get('enabled', False):
            logger.info(f"태스크 스킵: {task_name}")
            continue
            
        logger.info(f"태스크 실행: {task_name}")
        
        # lm-eval 명령 구성
        cmd = [
            'lm_eval',
            '--model', 'openai-completions',
            '--model_args', f'base_url={model_endpoint},model={task_config.get("model", "gpt-3.5-turbo")}',
            '--tasks', task_name,
            '--batch_size', str(task_config.get('batch_size', 1)),
            '--num_fewshot', str(task_config.get('shots', 0)),
            '--output_path', f'/tmp/{task_name}_results.json'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 결과 파싱
            with open(f'/tmp/{task_name}_results.json', 'r') as f:
                task_results = json.load(f)
                results[task_name] = task_results.get('results', {})
                
        except subprocess.CalledProcessError as e:
            logger.error(f"태스크 {task_name} 실행 실패: {e}")
            results[task_name] = {'error': str(e)}
    
    # 결과 저장
    final_results = {
        'timestamp': datetime.utcnow().isoformat(),
        'model_endpoint': model_endpoint,
        'config_file': config_file,
        'benchmarks': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    logger.info(f"평가 완료: {output_file}")
    return final_results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='설정 파일 경로')
    parser.add_argument('--model-endpoint', required=True, help='모델 엔드포인트')
    parser.add_argument('--output', default='/results/evalchemy_results.json', help='출력 파일')
    
    args = parser.parse_args()
    
    try:
        run_evaluation(args.config, args.model_endpoint, args.output)
    except Exception as e:
        logger.error(f"평가 실패: {e}")
        sys.exit(1)
EOF

RUN chmod +x /app/eval_wrapper.py

# 헬스체크 스크립트 생성
RUN cat > /app/healthcheck.sh << 'EOF'
#!/bin/bash
python3 -c "
import torch
import transformers
import lm_eval
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU count: {torch.cuda.device_count()}')
print(f'Transformers: {transformers.__version__}')
print('Evalchemy ready')
"
EOF

RUN chmod +x /app/healthcheck.sh

# 비root 사용자 생성 (보안)
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/.cache && \
    chown -R appuser:appuser /app/.cache

USER appuser

# 기본 환경 변수
ENV MODEL_ENDPOINT="" \
    CONFIG_FILE="/app/eval/evalchemy/configs/eval_config.json" \
    RESULTS_PATH="/results" \
    LOG_LEVEL=INFO \
    CUDA_VISIBLE_DEVICES="" \
    TORCH_HOME=/app/.cache/torch \
    HF_DATASETS_CACHE=/app/.cache/huggingface/datasets

# 볼륨 마운트 포인트
VOLUME ["/data", "/results", "/configs", "/app/.cache"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD /app/healthcheck.sh

# 기본 실행 명령
ENTRYPOINT ["python3", "/app/eval_wrapper.py"]
CMD ["--config", "/app/eval/evalchemy/configs/eval_config.json", "--model-endpoint", "${MODEL_ENDPOINT}", "--output", "/results/evalchemy_results.json"]

# 컨테이너 실행 예시:
# docker run --gpus all \
#   -v $(pwd)/data:/data \
#   -v $(pwd)/results:/results \
#   -e MODEL_ENDPOINT=http://vllm-server:8000/v1 \
#   -e CUDA_VISIBLE_DEVICES=0 \
#   ghcr.io/your-org/vllm-eval-evalchemy:latest

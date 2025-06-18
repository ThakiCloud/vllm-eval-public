# VLLM Official Benchmark Container - Using Pre-built VLLM Image
FROM vllm/vllm-openai:latest

# 메타데이터
LABEL maintainer="ThakiCloud <tech@company.com>"
LABEL description="VLLM official benchmark_serving.py container using pre-built image"
LABEL version="2.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 작업 디렉토리 생성
WORKDIR /app

# VLLM 소스코드 클론 (benchmark_serving.py 포함)
RUN git clone https://github.com/vllm-project/vllm.git /app/vllm-source && \
    cd /app/vllm-source && \
    git checkout main

# VLLM benchmarks 디렉토리를 메인 위치로 복사
RUN cp -r /app/vllm-source/benchmarks /app/benchmarks && \
    chmod +x /app/benchmarks/benchmark_serving.py

# 벤치마킹에 필요한 추가 의존성 설치
# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
    datasets==3.2.0 \
    matplotlib==3.9.2 \
    seaborn==0.13.2 \
    memory-profiler==0.61.0 \
    jsonlines==4.0.0 \
    asyncio-throttle==1.0.2 \
    PyYAML==6.0.2

# 설정 파일 및 스크립트 복사 (먼저 복사)
COPY configs/ /app/configs/
COPY scripts/ /app/scripts/

# 외부 스크립트 사용 (업데이트된 버전)
RUN cp /app/scripts/run_vllm_benchmark.sh /app/run_vllm_benchmark.sh && \
    chmod +x /app/run_vllm_benchmark.sh
RUN cp /app/scripts/standardize_vllm_benchmark.py /app/standardize_vllm_benchmark.py && \
    chmod +x /app/standardize_vllm_benchmark.py

# 샘플 데이터셋 생성 스크립트
RUN cat > /app/create_sample_dataset.py << 'EOF' && chmod +x /app/create_sample_dataset.py
#!/usr/bin/env python3
"""
VLLM 벤치마크용 샘플 데이터셋 생성 (VLLM 형식)
"""
import json
import os

def create_vllm_sample_dataset(output_path: str, num_samples: int = 100):
    """VLLM benchmark_serving.py 호환 데이터셋 생성"""
    
    # 다양한 길이와 복잡도의 프롬프트들
    sample_prompts = [
        "한국의 수도는 어디인가요?",
        "파이썬에서 리스트를 정렬하는 방법을 설명해주세요.",
        "인공지능의 발전이 사회에 미치는 영향에 대해 논의해주세요.",
        "기후 변화의 주요 원인과 해결 방안을 제시해주세요.",
        "블록체인 기술의 원리와 활용 분야를 설명해주세요.",
        "머신러닝과 딥러닝의 차이점을 비교해주세요.",
        "지속 가능한 발전을 위한 재생 에너지의 중요성을 설명해주세요.",
        "빅데이터 분석의 과정과 활용 사례를 소개해주세요.",
        "사물인터넷(IoT)이 일상생활에 미치는 변화를 설명해주세요.",
        "양자컴퓨팅의 원리와 미래 전망에 대해 논의해주세요."
    ]
    
    dataset = []
    for i in range(num_samples):
        prompt = sample_prompts[i % len(sample_prompts)]
        # 프롬프트에 번호 추가로 다양성 확보
        if i >= len(sample_prompts):
            prompt = f"[{i+1}] {prompt}"
        
        # VLLM benchmark_serving.py 호환 형식
        dataset.append({
            "prompt": prompt,
            "output_len": 128  # 예상 출력 길이
        })
    
    # JSONL 형식으로 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ VLLM 호환 데이터셋 생성 완료: {output_path}")
    print(f"📊 총 {len(dataset)}개 프롬프트")

if __name__ == "__main__":
    create_vllm_sample_dataset("/app/sample_dataset.jsonl", 100)
EOF

# VLLM 결과 분석 스크립트 (외부 파일 사용)
RUN cp /app/scripts/analyze_vllm_results.py /app/analyze_vllm_results.py && \
    chmod +x /app/analyze_vllm_results.py


# 설정 파일 및 스크립트는 이미 위에서 복사됨

# 헬스체크 스크립트 생성
RUN printf '#!/bin/bash\npython -c "import requests; print(\\"VLLM Benchmark ready\\")"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# 비root 사용자 생성 (보안)
RUN useradd --create-home --shell /bin/bash benchuser && \
    chown -R benchuser:benchuser /app

USER benchuser

# 기본 환경 변수 (최신 파라미터 반영)
ENV VLLM_ENDPOINT="http://vllm:8000" \
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
    BACKEND="openai-chat" \
    DATASET_TYPE="random" \
    PERCENTILE_METRICS="ttft,tpot,itl,e2el" \
    METRIC_PERCENTILES="25,50,75,90,95,99" \
    LOG_LEVEL="INFO"

# 볼륨 마운트 포인트
VOLUME ["/results", "/parsed"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# 기본 실행 명령
ENTRYPOINT ["/app/run_vllm_benchmark.sh"]

# 컨테이너 실행 예시:
# 기본 실행
# docker run -v $(pwd)/vllm-eval/results:/results -v $(pwd)/vllm-eval/parsed:/parsed vllm-benchmark:latest
#
# 고성능 벤치마크
# docker run -v $(pwd)/vllm-eval/results:/results -v $(pwd)/vllm-eval/parsed:/parsed \
#   -e VLLM_ENDPOINT=http://gpu-cluster:8000 \
#   -e MODEL_NAME=Qwen/Qwen3-8B \
#   -e SERVED_MODEL_NAME=qwen3-8b \
#   -e MAX_CONCURRENCY=10 \
#   -e RANDOM_INPUT_LEN=2048 \
#   -e RANDOM_OUTPUT_LEN=512 \
#   vllm-benchmark:latest
#
# 스트레스 테스트
# docker run -v $(pwd)/vllm-eval/results:/results -v $(pwd)/vllm-eval/parsed:/parsed \
#   -e MAX_CONCURRENCY=50 \
#   -e METRIC_PERCENTILES=50,90,95,99,99.9 \
#   vllm-benchmark:latest
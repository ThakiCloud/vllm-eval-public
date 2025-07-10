# 경량 Python 베이스 이미지
FROM python:3.10-slim

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TOKENIZERS_PARALLELISM=false
ENV OMP_NUM_THREADS=1
ENV CLASSPATH="/usr/local/lib/antlr-4.11.1-complete.jar:$CLASSPATH"

# 네트워크 관련 환경 변수 (SSL/TLS 이슈 해결)
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
ENV HF_HUB_DISABLE_TELEMETRY=1

# 작업 디렉토리
WORKDIR /workspace

# 필수 시스템 패키지 설치 (네트워크 도구 추가)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    ca-certificates \
    openjdk-17-jre-headless \
    dnsutils \
    iputils-ping \
    net-tools \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# pip 업그레이드 (SSL 이슈 해결)
RUN pip install --no-cache-dir --upgrade pip \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org

# 필요 최소한의 Python 패키지만 설치 (GPU/시각화 불필요한 것 제거)
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    requests \
    urllib3 \
    tqdm \
    datasets \
    transformers \
    numpy \
    pandas \
    sympy \
    antlr4-python3-runtime==4.11.1

# ANTLR JAR 설치 (LaTeX2SymPy 용)
RUN wget https://www.antlr.org/download/antlr-4.11.1-complete.jar -O /usr/local/lib/antlr-4.11.1-complete.jar

# 네트워크 연결 테스트 스크립트 추가
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

# nvidia_eval 폴더에서 필요한 파일들 복사
COPY eval/nvidia_eval/*.sh ./
COPY eval/nvidia_eval/*.py ./
COPY eval/nvidia_eval/data/ ./data/
COPY eval/nvidia_eval/tools/ ./tools/

# 표준화 스크립트를 위한 디렉토리 생성 및 복사
RUN mkdir -p /workspace/scripts
COPY scripts/standardize_aime_results.py /workspace/scripts/
COPY scripts/standardize_livecodebench_results.py /workspace/scripts/

# tools/latex2sympy 내부 JAR 복사 (있는 경우만)
RUN if [ -f /workspace/tools/latex2sympy/antlr-4.11.1-complete.jar ]; then \
    cp /workspace/tools/latex2sympy/antlr-4.11.1-complete.jar /usr/local/lib/; \
    fi

# 스크립트들에 API 모드 파라미터 및 GPU 제거
RUN sed -i '/python inference.py/a\    ${API_BASE:+--api-base "${API_BASE}"} \\' generate_aime.sh && \
    sed -i '/python inference.py/a\    ${API_BASE:+--api-base "${API_BASE}"} \\' generate_livecodebench.sh && \
    sed -i 's/for (( gpu=0; gpu<GPUS; gpu++ )); do/# API mode - single execution/' generate_aime.sh && \
    sed -i 's/for (( gpu=0; gpu<GPUS; gpu++ )); do/# API mode - single execution/' generate_livecodebench.sh && \
    sed -i 's/--device-id "${gpu}" &/# --device-id removed for API mode/' generate_aime.sh && \
    sed -i 's/--device-id "${gpu}" &/# --device-id removed for API mode/' generate_livecodebench.sh && \
    sed -i 's/seed=$(( seed + 1 ))/# seed increment removed/' generate_aime.sh && \
    sed -i 's/seed=$(( seed + 1 ))/# seed increment removed/' generate_livecodebench.sh && \
    sed -i 's/done/# done/' generate_aime.sh && \
    sed -i 's/done/# done/' generate_livecodebench.sh && \
    sed -i 's/wait/# wait/' generate_aime.sh && \
    sed -i 's/wait/# wait/' generate_livecodebench.sh

# OUT_SEQ_LEN 기본값 설정
RUN sed -i 's/--max-output-len "${OUT_SEQ_LEN}"/--max-output-len "${OUT_SEQ_LEN:-32768}"/' generate_aime.sh && \
    sed -i 's/--max-output-len "${OUT_SEQ_LEN}"/--max-output-len "${OUT_SEQ_LEN:-14000}"/' generate_livecodebench.sh

# 실행 권한 부여
RUN chmod +x /workspace/*.sh

# 기본 디렉토리 생성
RUN mkdir -p /workspace/cache /workspace/output

# 기본 명령어 설정 (네트워크 테스트 추가)
CMD echo "=== Starting AceReason Evaluation Toolkit ===" && \
    test-network && \
    echo "" && \
    if [ "$EVAL_TYPE" = "aime" ]; then \
        bash run_aime.sh "$MODEL_NAME" "$OUTPUT_FOLDER" 1 "${OUT_SEQ_LEN:-32768}"; \
    elif [ "$EVAL_TYPE" = "lcb" ]; then \
        bash run_livecodebench.sh "$MODEL_NAME" "$OUTPUT_FOLDER" 1 "${OUT_SEQ_LEN:-14000}"; \
    elif [ "$EVAL_TYPE" = "both" ]; then \
        bash run_aime.sh "$MODEL_NAME" "$OUTPUT_FOLDER" 1 "${OUT_SEQ_LEN:-32768}" && \
        bash run_livecodebench.sh "$MODEL_NAME" "$OUTPUT_FOLDER" 1 "${OUT_SEQ_LEN:-14000}"; \
    else \
        echo "Usage: docker run -e API_BASE=http://server:8000/v1 -e MODEL_NAME=model -e OUTPUT_FOLDER=output -e EVAL_TYPE=[aime|lcb|both] image"; \
        echo "Optional: -e OUT_SEQ_LEN=32768"; \
    fi

# 라벨
LABEL description="Optimized lightweight Docker image for AceReason Toolkit - API mode only with network fixes"
LABEL gpu.required="false"

# 도커 빌드
# docker build -f docker/nvidia_eval.Dockerfile  -t nvidia-eval-standard --no-cache
#
# 실행 예시 [AIME, LCB 모두 평가]
#   docker run -e API_BASE=http://host.docker.internal:port/v1 \
#   -e MODEL_NAME=qwen3-8b \
#   -e OUTPUT_FOLDER=output \
#   -e EVAL_TYPE=both \
#   -e OUT_SEQ_LEN=14000 \
#   -v $(pwd)/output:/workspace/output \
#   nvidia-eval-nvidia-eval-standard  
#
# 실행 예시 [AIME 평가]
#   docker run -e API_BASE=http://host.docker.internal:port/v1 \
#   -e MODEL_NAME=qwen3-8b \
#   -e OUTPUT_FOLDER=output \
#   -e EVAL_TYPE=aime \
#   -e OUT_SEQ_LEN=14000 \
#   -v $(pwd)/output:/workspace/output \
#   nvidia-eval-nvidia-eval-standard  
#
# 실행 예시 [LCB 평가]
#   docker run -e API_BASE=http://host.docker.internal:port/v1 \
#   -e MODEL_NAME=qwen3-8b \
#   -e OUTPUT_FOLDER=output \
#   -e EVAL_TYPE=lcb \
#   -e OUT_SEQ_LEN=14000 \
#   -v $(pwd)/output:/workspace/output \
#   nvidia-eval-nvidia-eval-standard  
#

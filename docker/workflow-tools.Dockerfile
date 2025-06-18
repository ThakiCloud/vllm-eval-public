# Workflow Tools Container for VLLM Evaluation System
FROM alpine:3.19

# 메타데이터
LABEL maintainer="ThakiCloud <tech@company.com>"
LABEL description="Workflow tools container with yq, awscli, mc and other utilities"
LABEL version="1.0.0"

# 환경 변수 설정
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# 시스템 패키지 업데이트 및 필수 패키지 설치
# hadolint ignore=DL3008,DL3009
RUN apk update && apk add --no-cache \
    bash \
    curl \
    wget \
    git \
    jq \
    python3 \
    py3-pip \
    openssh-client \
    ca-certificates \
    openssl \
    tar \
    gzip \
    unzip \
    && rm -rf /var/cache/apk/*

# yq 설치 (YAML 처리 도구)
# hadolint ignore=DL3009
RUN wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && \
    chmod +x /usr/local/bin/yq

# AWS CLI v2 설치
# hadolint ignore=DL3009
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

# MinIO Client (mc) 설치
# hadolint ignore=DL3009
RUN wget -O /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc && \
    chmod +x /usr/local/bin/mc

# kubectl 설치
# hadolint ignore=DL3009
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# Helm 설치
# hadolint ignore=DL3009
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Argo CLI 설치
# hadolint ignore=DL3009
RUN curl -sLO https://github.com/argoproj/argo-workflows/releases/latest/download/argo-linux-amd64.gz && \
    gunzip argo-linux-amd64.gz && \
    mv argo-linux-amd64 /usr/local/bin/argo && \
    chmod +x /usr/local/bin/argo

# Python 가상환경 생성 및 패키지 설치
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    click==8.1.7 \
    rich==13.7.0 \
    typer==0.9.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1

# 작업 디렉토리 생성
WORKDIR /app

# 데이터셋 동기화 스크립트 생성
RUN echo '#!/bin/bash' > /app/dataset-sync.sh && \
    echo '# 데이터셋 동기화 스크립트' >> /app/dataset-sync.sh && \
    echo '' >> /app/dataset-sync.sh && \
    echo 'set -euo pipefail' >> /app/dataset-sync.sh && \
    echo '' >> /app/dataset-sync.sh && \
    echo 'MINIO_ENDPOINT=${MINIO_ENDPOINT:-"http://minio:9000"}' >> /app/dataset-sync.sh && \
    echo 'MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-""}' >> /app/dataset-sync.sh && \
    echo 'MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-""}' >> /app/dataset-sync.sh && \
    echo 'BUCKET_NAME=${BUCKET_NAME:-"llm-eval-ds"}' >> /app/dataset-sync.sh && \
    echo '' >> /app/dataset-sync.sh && \
    echo 'echo "📦 MinIO 클라이언트 설정..."' >> /app/dataset-sync.sh && \
    echo 'mc alias set minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"' >> /app/dataset-sync.sh && \
    echo '' >> /app/dataset-sync.sh && \
    echo 'echo "🔄 데이터셋 동기화 시작..."' >> /app/dataset-sync.sh && \
    echo 'mc mirror --remove minio/$BUCKET_NAME /data/' >> /app/dataset-sync.sh && \
    echo '' >> /app/dataset-sync.sh && \
    echo 'echo "✅ 데이터셋 동기화 완료"' >> /app/dataset-sync.sh

# 결과 업로드 스크립트 생성
RUN echo '#!/bin/bash' > /app/results-upload.sh && \
    echo '# 결과 업로드 스크립트' >> /app/results-upload.sh && \
    echo '' >> /app/results-upload.sh && \
    echo 'set -euo pipefail' >> /app/results-upload.sh && \
    echo '' >> /app/results-upload.sh && \
    echo 'MINIO_ENDPOINT=${MINIO_ENDPOINT:-"http://minio:9000"}' >> /app/results-upload.sh && \
    echo 'MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-""}' >> /app/results-upload.sh && \
    echo 'MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-""}' >> /app/results-upload.sh && \
    echo 'BUCKET_NAME=${BUCKET_NAME:-"llm-eval-results"}' >> /app/results-upload.sh && \
    echo 'RUN_ID=${RUN_ID:-$(date +%s)}' >> /app/results-upload.sh && \
    echo '' >> /app/results-upload.sh && \
    echo 'echo "📦 MinIO 클라이언트 설정..."' >> /app/results-upload.sh && \
    echo 'mc alias set minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"' >> /app/results-upload.sh && \
    echo '' >> /app/results-upload.sh && \
    echo 'echo "📤 결과 업로드 시작..."' >> /app/results-upload.sh && \
    echo 'mc cp --recursive /results/ minio/$BUCKET_NAME/$RUN_ID/' >> /app/results-upload.sh && \
    echo '' >> /app/results-upload.sh && \
    echo 'echo "✅ 결과 업로드 완료"' >> /app/results-upload.sh

# Python 스크립트 생성 (echo 방식으로)
RUN echo '#!/usr/bin/env python3' > /app/manifest-processor.py && \
    echo '"""Manifest processor for dataset management"""' >> /app/manifest-processor.py && \
    echo '' >> /app/manifest-processor.py && \
    echo 'import argparse' >> /app/manifest-processor.py && \
    echo 'import hashlib' >> /app/manifest-processor.py && \
    echo 'import json' >> /app/manifest-processor.py && \
    echo 'import sys' >> /app/manifest-processor.py && \
    echo 'import yaml' >> /app/manifest-processor.py && \
    echo 'from pathlib import Path' >> /app/manifest-processor.py && \
    echo 'from typing import Dict, Any' >> /app/manifest-processor.py && \
    echo '' >> /app/manifest-processor.py && \
    echo 'def calculate_checksum(file_path: str) -> str:' >> /app/manifest-processor.py && \
    echo '    """파일의 SHA-256 체크섬 계산"""' >> /app/manifest-processor.py && \
    echo '    sha256_hash = hashlib.sha256()' >> /app/manifest-processor.py && \
    echo '    with open(file_path, "rb") as f:' >> /app/manifest-processor.py && \
    echo '        for byte_block in iter(lambda: f.read(4096), b""):' >> /app/manifest-processor.py && \
    echo '            sha256_hash.update(byte_block)' >> /app/manifest-processor.py && \
    echo '    return sha256_hash.hexdigest()' >> /app/manifest-processor.py && \
    echo '' >> /app/manifest-processor.py && \
    echo 'def validate_manifest(manifest_path: str) -> bool:' >> /app/manifest-processor.py && \
    echo '    """매니페스트 파일 검증"""' >> /app/manifest-processor.py && \
    echo '    try:' >> /app/manifest-processor.py && \
    echo '        with open(manifest_path, "r") as f:' >> /app/manifest-processor.py && \
    echo '            manifest = yaml.safe_load(f)' >> /app/manifest-processor.py && \
    echo '        required_fields = ["apiVersion", "kind", "metadata", "spec"]' >> /app/manifest-processor.py && \
    echo '        for field in required_fields:' >> /app/manifest-processor.py && \
    echo '            if field not in manifest:' >> /app/manifest-processor.py && \
    echo '                print(f"❌ 필수 필드 누락: {field}")' >> /app/manifest-processor.py && \
    echo '                return False' >> /app/manifest-processor.py && \
    echo '        print("✅ 매니페스트 검증 통과")' >> /app/manifest-processor.py && \
    echo '        return True' >> /app/manifest-processor.py && \
    echo '    except Exception as e:' >> /app/manifest-processor.py && \
    echo '        print(f"❌ 매니페스트 검증 실패: {e}")' >> /app/manifest-processor.py && \
    echo '        return False' >> /app/manifest-processor.py && \
    echo '' >> /app/manifest-processor.py && \
    echo 'if __name__ == "__main__":' >> /app/manifest-processor.py && \
    echo '    parser = argparse.ArgumentParser(description="매니페스트 처리 도구")' >> /app/manifest-processor.py && \
    echo '    parser.add_argument("command", choices=["validate", "update-checksum"])' >> /app/manifest-processor.py && \
    echo '    parser.add_argument("--manifest", required=True, help="매니페스트 파일 경로")' >> /app/manifest-processor.py && \
    echo '    args = parser.parse_args()' >> /app/manifest-processor.py && \
    echo '    if args.command == "validate":' >> /app/manifest-processor.py && \
    echo '        if not validate_manifest(args.manifest):' >> /app/manifest-processor.py && \
    echo '            sys.exit(1)' >> /app/manifest-processor.py

# 워크플로 알림 스크립트 생성
RUN echo '#!/usr/bin/env python3' > /app/workflow-notifier.py && \
    echo '"""Workflow notification script for Teams"""' >> /app/workflow-notifier.py && \
    echo '' >> /app/workflow-notifier.py && \
    echo 'import argparse' >> /app/workflow-notifier.py && \
    echo 'import json' >> /app/workflow-notifier.py && \
    echo 'import sys' >> /app/workflow-notifier.py && \
    echo 'import requests' >> /app/workflow-notifier.py && \
    echo 'from datetime import datetime' >> /app/workflow-notifier.py && \
    echo '' >> /app/workflow-notifier.py && \
    echo 'def send_teams_notification(webhook_url: str, title: str, message: str) -> bool:' >> /app/workflow-notifier.py && \
    echo '    """Teams 알림 전송"""' >> /app/workflow-notifier.py && \
    echo '    card = {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": {"type": "AdaptiveCard", "body": [{"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title}, {"type": "TextBlock", "text": message, "wrap": True}], "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.2"}}]}' >> /app/workflow-notifier.py && \
    echo '    try:' >> /app/workflow-notifier.py && \
    echo '        response = requests.post(webhook_url, json=card, timeout=30)' >> /app/workflow-notifier.py && \
    echo '        return response.status_code == 200' >> /app/workflow-notifier.py && \
    echo '    except Exception as e:' >> /app/workflow-notifier.py && \
    echo '        print(f"알림 전송 실패: {e}")' >> /app/workflow-notifier.py && \
    echo '        return False' >> /app/workflow-notifier.py && \
    echo '' >> /app/workflow-notifier.py && \
    echo 'if __name__ == "__main__":' >> /app/workflow-notifier.py && \
    echo '    parser = argparse.ArgumentParser(description="워크플로 알림 도구")' >> /app/workflow-notifier.py && \
    echo '    parser.add_argument("--webhook-url", required=True, help="Webhook URL")' >> /app/workflow-notifier.py && \
    echo '    parser.add_argument("--title", required=True, help="알림 제목")' >> /app/workflow-notifier.py && \
    echo '    parser.add_argument("--message", required=True, help="알림 메시지")' >> /app/workflow-notifier.py && \
    echo '    args = parser.parse_args()' >> /app/workflow-notifier.py && \
    echo '    success = send_teams_notification(args.webhook_url, args.title, args.message)' >> /app/workflow-notifier.py && \
    echo '    if not success:' >> /app/workflow-notifier.py && \
    echo '        sys.exit(1)' >> /app/workflow-notifier.py && \
    echo '    print("✅ 알림 전송 완료")' >> /app/workflow-notifier.py

# 스크립트 실행 권한 부여
RUN chmod +x /app/*.sh /app/*.py

# 비root 사용자 생성
RUN adduser -D -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# 환경 변수
ENV MINIO_ENDPOINT="" \
    MINIO_ACCESS_KEY="" \
    MINIO_SECRET_KEY="" \
    AWS_REGION="us-east-1" \
    KUBECONFIG="/app/.kube/config"

# 볼륨 마운트 포인트
VOLUME ["/data", "/results", "/app/.kube", "/app/.aws"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD yq --version && aws --version && mc --version

# 기본 작업 디렉토리
WORKDIR /app

# 기본 명령
CMD ["bash"] 
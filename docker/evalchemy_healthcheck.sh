#!/bin/bash
set -euo pipefail  # 보안: 엄격한 오류 처리

echo "=== Evalchemy API Health Check ==="

# 환경 변수 검증
if [[ -z "${MODEL_ENDPOINT:-}" ]]; then
    echo "❌ MODEL_ENDPOINT environment variable is required"
    exit 1
fi

# Python 및 패키지 버전 확인
python3 -c "
import sys
import requests
import json
import os
print(f'Python: {sys.version}')
print(f'Requests: {requests.__version__}')
"

# lm-eval 설치 확인
cd /app/lm-eval || {
    echo "❌ lm-eval directory not found"
    exit 1
}

python -c "
import lm_eval
print('✅ lm-eval import successful')
"

# 설정 파일 확인
CONFIG_FILE="/app/eval/evalchemy/configs/eval_config.json"
if [[ -f "$CONFIG_FILE" ]]; then
    echo "✅ Configuration file found"
    python -c "
import json
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    
    # 설정 검증
    if not isinstance(config, dict):
        print('❌ Invalid config format')
        sys.exit(1)
    
    tasks = config.get('tasks', {})
    if not isinstance(tasks, dict):
        print('❌ Invalid tasks configuration')
        sys.exit(1)
    
    enabled_tasks = [
        name for name, task in tasks.items() 
        if isinstance(task, dict) and task.get('enabled', False)
    ]
    
    print(f'✅ Enabled tasks: {enabled_tasks}')
    print(f'✅ Evaluation mode: {config.get(\"evaluation_mode\", \"unknown\")}')
    
    # API 설정 확인
    api_configs = config.get('api_configs', {})
    if api_configs:
        print(f'✅ API configurations found: {list(api_configs.keys())}')
    
except Exception as e:
    print(f'❌ Config validation failed: {e}')
    sys.exit(1)
"
else
    echo "❌ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# API 연결성 테스트 (보안: URL 검증)
echo "🔗 Testing API connectivity..."
python3 -c "
import requests
import os
import sys
from urllib.parse import urlparse

model_endpoint = os.environ.get('MODEL_ENDPOINT', '')
if not model_endpoint:
    print('❌ MODEL_ENDPOINT not set')
    sys.exit(1)

# URL 검증
try:
    parsed = urlparse(model_endpoint)
    if not parsed.scheme or not parsed.netloc:
        print(f'❌ Invalid URL format: {model_endpoint}')
        sys.exit(1)
    
    if parsed.scheme not in ['http', 'https']:
        print(f'❌ Unsupported scheme: {parsed.scheme}')
        sys.exit(1)
        
    print(f'✅ Valid endpoint format: {model_endpoint}')
    
    # 기본 연결성 테스트 (타임아웃 설정)
    if model_endpoint.startswith('http'):
        try:
            response = requests.get(
                f'{model_endpoint}/health' if not model_endpoint.endswith('/') else f'{model_endpoint}health',
                timeout=10,
                verify=True  # SSL 검증 활성화
            )
            print(f'✅ Health endpoint accessible (status: {response.status_code})')
        except requests.exceptions.RequestException as e:
            print(f'⚠️  Health endpoint not accessible: {e}')
            # 헬스체크 실패해도 계속 진행 (선택적)
    
except Exception as e:
    print(f'❌ Endpoint validation failed: {e}')
    sys.exit(1)
"

# API 키 존재 확인 (값은 출력하지 않음)
echo "🔑 Checking API keys..."
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    echo "✅ OPENAI_API_KEY is set"
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "✅ ANTHROPIC_API_KEY is set"
fi

if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "⚠️  No API keys found (using local endpoint)"
fi

# 디스크 공간 확인
echo "💾 Checking disk space..."
AVAILABLE_SPACE=$(df /tmp | tail -1 | awk '{print $4}')
if [[ "$AVAILABLE_SPACE" -lt 1048576 ]]; then  # 1GB in KB
    echo "⚠️  Low disk space in /tmp: ${AVAILABLE_SPACE}KB"
else
    echo "✅ Sufficient disk space: ${AVAILABLE_SPACE}KB"
fi

# 메모리 확인
echo "🧠 Checking memory..."
AVAILABLE_MEM=$(free | grep '^Mem:' | awk '{print $7}')
if [[ "$AVAILABLE_MEM" -lt 1048576 ]]; then  # 1GB in KB
    echo "⚠️  Low available memory: ${AVAILABLE_MEM}KB"
else
    echo "✅ Sufficient memory: ${AVAILABLE_MEM}KB"
fi

# 네트워크 연결성 확인
echo "🌐 Testing network connectivity..."
if ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ Internet connectivity available"
else
    echo "⚠️  Limited internet connectivity"
fi

# 권한 확인
echo "🔐 Checking permissions..."
if [[ -w "/tmp" ]]; then
    echo "✅ Write permission to /tmp"
else
    echo "❌ No write permission to /tmp"
    exit 1
fi

if [[ -w "/results" ]] || mkdir -p "/results" 2>/dev/null; then
    echo "✅ Write permission to /results"
else
    echo "❌ No write permission to /results"
    exit 1
fi

echo "✅ Health check completed successfully"
echo "🚀 Ready for API-based evaluation" 
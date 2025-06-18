# 로컬 테스트 가이드 (macOS)

이 문서는 GitHub에 푸시하기 전에 macOS 환경에서 VLLM 평가 시스템을 단계별로 테스트하는 방법을 설명합니다.

## 📋 목차

1. [사전 준비](#사전-준비)
2. [환경 설정](#환경-설정)
3. [단계별 테스트](#단계별-테스트)
4. [통합 테스트](#통합-테스트)
5. [문제 해결](#문제-해결)
6. [성능 최적화](#성능-최적화)

## 🛠 사전 준비

### 필수 도구 설치

#### 옵션 1: OrbStack 사용 (권장)

```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# OrbStack 설치 (Docker Desktop 대신 권장)
brew install --cask orbstack

# 필수 도구들 설치
brew install python@3.11 kubectl helm jq yq

# PostgreSQL 관련 라이브러리 설치 (pytest 의존성)
brew install postgresql@14 libpq

# Python 패키지 관리자 업그레이드
pip3 install --upgrade pip setuptools wheel
```

#### 옵션 2: Docker Desktop 사용

```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 필수 도구들 설치
brew install python@3.11 docker docker-compose kind kubectl helm jq yq
brew install --cask docker

# PostgreSQL 관련 라이브러리 설치 (pytest 의존성)
brew install postgresql@14 libpq

# Python 패키지 관리자 업그레이드
pip3 install --upgrade pip setuptools wheel
```

### OrbStack 설정 (권장)

```bash
# OrbStack 시작
open -a OrbStack

# OrbStack이 실행될 때까지 대기
while ! docker info > /dev/null 2>&1; do
    echo "OrbStack 시작 대기 중..."
    sleep 3
done

echo "OrbStack이 성공적으로 시작되었습니다."

# Kubernetes 클러스터 활성화 (OrbStack 내장)
orb start k8s

# kubectl 컨텍스트 확인
kubectl config current-context
kubectl get nodes
```

### Docker Desktop 설정 (대안)

```bash
# Docker Desktop 시작
open -a Docker

# Docker가 실행될 때까지 대기
while ! docker info > /dev/null 2>&1; do
    echo "Docker 시작 대기 중..."
    sleep 5
done

echo "Docker가 성공적으로 시작되었습니다."
```

### 프로젝트 클론 및 이동

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/your/vllm-eval

# 현재 위치 확인
pwd
ls -la
```

## ⚙️ 환경 설정

### 1. Python 가상환경 설정

```bash
# Python 3.11 가상환경 생성
python3.11 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 가상환경 확인
which python
python --version  # Python 3.11.x 확인
```

### 2. 의존성 설치

```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt
pip install -r requirements-test.txt

# PostgreSQL 관련 Python 패키지 설치 (테스트 의존성)
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libpq/lib/pkgconfig"
pip install "psycopg[binary]"

# 추가 패키지 설치 (필요한 경우)
pip install deepeval lm-eval torch transformers datasets
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << 'EOF'
# 테스트 환경 변수
PYTHONPATH=.
LOG_LEVEL=DEBUG
EVAL_CONFIG_PATH=eval/evalchemy/configs/eval_config.json
OUTPUT_DIR=./test_results
RUN_ID=local_test_$(date +%Y%m%d_%H%M%S)

# 테스트용 모델 엔드포인트 (실제 서비스 대신 Mock 사용)
VLLM_MODEL_ENDPOINT=http://localhost:8000/v1

# MinIO 테스트 설정
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=llm-eval-ds-test

# ClickHouse 테스트 설정
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=vllm_eval_test
EOF

# 환경 변수 로드
source .env
```

## 🧪 단계별 테스트

### 1단계: 코드 품질 검사

```bash
pip install ruff black isort mypy

echo "=== 1단계: 코드 품질 검사 ==="

# Ruff 린팅
echo "Ruff 린팅 실행 중..."
ruff check . --fix
echo "✅ Ruff 린팅 완료"

# Black 포맷팅
echo "Black 포맷팅 실행 중..."
black . --check --diff
echo "✅ Black 포맷팅 확인 완료"

# isort import 정렬
echo "isort import 정렬 확인 중..."
isort . --check-only --diff
echo "✅ isort 확인 완료"

# MyPy 타입 검사
echo "MyPy 타입 검사 실행 중..."
mypy scripts/ eval/ --ignore-missing-imports
echo "✅ MyPy 타입 검사 완료"
```

### 2단계: 스키마 및 설정 검증

```bash
echo "=== 2단계: 스키마 및 설정 검증 ==="

# 스키마 검증
echo "스키마 검증 실행 중..."
python scripts/validate_schemas.py
echo "✅ 스키마 검증 완료"

# 설정 파일 검증
echo "Evalchemy 설정 검증 중..."
python -c "
import json
with open('eval/evalchemy/configs/eval_config.json', 'r') as f:
    config = json.load(f)
    print(f'✅ 설정 파일 유효: {len(config[\"benchmarks\"])}개 벤치마크 발견')
"

# 데이터셋 매니페스트 검증
echo "데이터셋 매니페스트 검증 중..."
if [ -f "datasets/dataset_manifest.json" ]; then
    python -c "
import json
with open('datasets/dataset_manifest.json', 'r') as f:
    manifest = json.load(f)
    print(f'✅ 데이터셋 매니페스트 유효: {len(manifest.get(\"datasets\", []))}개 데이터셋')
"
else
    echo "⚠️  데이터셋 매니페스트 파일이 없습니다. 테스트용으로 생성합니다."
    mkdir -p datasets
    cat > datasets/dataset_manifest.json << 'EOF'
{
  "version": "1.0.0",
  "datasets": [
    {
      "name": "test_rag_dataset",
      "version": "sha256:test123",
      "path": "test_rag_dataset.jsonl",
      "size": 1000,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
EOF
    echo "✅ 테스트용 데이터셋 매니페스트 생성 완료"
fi
```

### 3단계: 단위 테스트

```bash
echo "=== 3단계: 단위 테스트 ==="

# pytest 실행 (빠른 테스트만)
echo "단위 테스트 실행 중..."
python -m pytest eval/deepeval_tests/test_llm_rag.py -v --tb=short -x

# 테스트 커버리지 확인
echo "테스트 커버리지 확인 중..."
python -m pytest eval/deepeval_tests/test_llm_rag.py --cov=eval --cov-report=term-missing --cov-report=html

echo "✅ 단위 테스트 완료"
echo "📊 커버리지 리포트: htmlcov/index.html"
```

### 4단계: 스크립트 기능 테스트

```bash
echo "=== 4단계: 스크립트 기능 테스트 ==="

# 중복 제거 스크립트 테스트
echo "중복 제거 스크립트 테스트 중..."
mkdir -p test_datasets
cat > test_datasets/test_data.jsonl << 'EOF'
{"input": "What is AI?", "output": "AI is artificial intelligence."}
{"input": "What is AI?", "output": "AI is artificial intelligence."}
{"input": "What is ML?", "output": "ML is machine learning."}
EOF

python scripts/dedup_datasets.py \
    --input-dir test_datasets \
    --output-dir test_datasets/deduped \
    --threshold 0.2 \
    --dry-run

echo "✅ 중복 제거 스크립트 테스트 완료"

# Evalchemy 스크립트 검증 테스트
echo "Evalchemy 스크립트 검증 테스트 중..."
chmod +x eval/evalchemy/run_evalchemy.sh
./eval/evalchemy/run_evalchemy.sh --help
./eval/evalchemy/run_evalchemy.sh --validate-config
./eval/evalchemy/run_evalchemy.sh --list-benchmarks

echo "✅ Evalchemy 스크립트 테스트 완료"
```

### 5단계: Docker 이미지 빌드 테스트

```bash
echo "=== 5단계: Docker 이미지 빌드 테스트 ==="

# Deepeval 이미지 빌드
echo "Deepeval 이미지 빌드 중..."
docker build -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test .
echo "✅ Deepeval 이미지 빌드 완료"

# Evalchemy 이미지 빌드 (GPU 없이 CPU 버전)
echo "Evalchemy 이미지 빌드 중..."
docker build -f docker/evalchemy-cpu.Dockerfile -t vllm-eval/evalchemy:test .
echo "✅ Evalchemy 이미지 빌드 완료"

# Workflow Tools 이미지 빌드
echo "Workflow Tools 이미지 빌드 중..."
docker build -f docker/workflow-tools.Dockerfile -t vllm-eval/workflow-tools:test .
echo "✅ Workflow Tools 이미지 빌드 완료"

# 이미지 크기 확인
echo "빌드된 이미지 크기:"
docker images | grep vllm-eval
```

### 6단계: 컨테이너 실행 테스트

```bash
echo "=== 6단계: 컨테이너 실행 테스트 ==="

# Deepeval 컨테이너 테스트
echo "Deepeval 컨테이너 테스트 중..."
docker run --rm vllm-eval/deepeval:test python -c "
import deepeval
from deepeval.test_case import LLMTestCase
print('✅ Deepeval 컨테이너 정상 작동')
"

# Workflow Tools 컨테이너 테스트
echo "Workflow Tools 컨테이너 테스트 중..."
docker run --rm vllm-eval/workflow-tools:test sh -c "
yq --version && \
jq --version && \
kubectl version --client && \
helm version --client
echo '✅ Workflow Tools 컨테이너 정상 작동'
"

echo "✅ 컨테이너 실행 테스트 완료"
```

## 🔗 통합 테스트

### OrbStack Kubernetes 클러스터 테스트 (권장)

```bash
echo "=== 통합 테스트: OrbStack Kubernetes ==="

# OrbStack Kubernetes 클러스터 생성/활성화
echo "OrbStack Kubernetes 클러스터 설정 중..."
orb start k8s

# 클러스터 상태 확인
kubectl config use-context orbstack
kubectl cluster-info
kubectl get nodes

# 네임스페이스 생성
kubectl create namespace vllm-eval-test --dry-run=client -o yaml | kubectl apply -f -

echo "✅ OrbStack Kubernetes 클러스터 준비 완료"
```

### Kind 클러스터를 이용한 로컬 Kubernetes 테스트 (대안)

```bash
echo "=== 통합 테스트: Kind 클러스터 ==="

# Kind 클러스터 생성
echo "Kind 클러스터 생성 중..."
cat > kind-config.yaml << 'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
EOF

kind create cluster --name vllm-eval-test --config kind-config.yaml

# 클러스터 상태 확인
kubectl cluster-info --context kind-vllm-eval-test
kubectl get nodes

echo "✅ Kind 클러스터 생성 완료"
```

### Helm 차트 검증

```bash
echo "Helm 차트 검증 중..."

# Argo Workflows 차트 검증
helm lint charts/argo-workflows/
helm template test-argo charts/argo-workflows/ --debug --dry-run

# ClickHouse 차트 검증
helm lint charts/clickhouse/
helm template test-clickhouse charts/clickhouse/ --debug --dry-run

# Grafana 차트 검증
helm lint charts/grafana/
helm template test-grafana charts/grafana/ --debug --dry-run

echo "✅ Helm 차트 검증 완료"
```

### 로컬 MinIO 및 ClickHouse 테스트

#### OrbStack 사용 (권장)

```bash
echo "로컬 서비스 테스트 환경 구성 중 (OrbStack)..."

# OrbStack에서 직접 컨테이너 실행
echo "MinIO 컨테이너 시작 중..."
docker run -d --name minio-test \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio:latest server /data --console-address ":9001"

echo "ClickHouse 컨테이너 시작 중..."
docker run -d --name clickhouse-test \
  -p 8123:8123 -p 9009:9009 \
  -e CLICKHOUSE_DB=vllm_eval_test \
  clickhouse/clickhouse-server:latest

# 서비스 준비 대기
echo "서비스 시작 대기 중..."
sleep 20

# MinIO 연결 테스트
echo "MinIO 연결 테스트 중..."
curl -f http://localhost:9000/minio/health/live || echo "MinIO 연결 실패"

# ClickHouse 연결 테스트
echo "ClickHouse 연결 테스트 중..."
curl -f http://localhost:8123/ping || echo "ClickHouse 연결 실패"

echo "✅ 로컬 서비스 테스트 완료"

# 정리
echo "테스트 컨테이너 정리 중..."
docker stop minio-test clickhouse-test 2>/dev/null || true
docker rm minio-test clickhouse-test 2>/dev/null || true
```

#### Docker Compose 사용 (대안)

```bash
echo "로컬 서비스 테스트 환경 구성 중 (Docker Compose)..."

# Docker Compose로 테스트 서비스 시작
cat > docker-compose.test.yml << 'EOF'
version: '3.8'
services:
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "8123:8123"
      - "9009:9009"
    environment:
      CLICKHOUSE_DB: vllm_eval_test
    volumes:
      - clickhouse_data:/var/lib/clickhouse

volumes:
  minio_data:
  clickhouse_data:
EOF

docker-compose -f docker-compose.test.yml up -d

# 서비스 준비 대기
echo "서비스 시작 대기 중..."
sleep 30

# MinIO 연결 테스트
echo "MinIO 연결 테스트 중..."
curl -f http://localhost:9000/minio/health/live || echo "MinIO 연결 실패"

# ClickHouse 연결 테스트
echo "ClickHouse 연결 테스트 중..."
curl -f http://localhost:8123/ping || echo "ClickHouse 연결 실패"

echo "✅ 로컬 서비스 테스트 완료"
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Python 의존성 충돌

```bash
# 가상환경 재생성
deactivate
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### 2. Docker 빌드 실패

```bash
# Docker 캐시 정리
docker system prune -f
docker builder prune -f

# 빌드 로그 상세 확인
docker build -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test . --no-cache --progress=plain
```

#### 3. OrbStack 클러스터 문제

```bash
# OrbStack Kubernetes 클러스터 재시작
orb delete k8s
orb start k8s

# 컨텍스트 재설정
kubectl config use-context orbstack
```

#### 4. Kind 클러스터 문제 (대안)

```bash
# 클러스터 삭제 후 재생성
kind delete cluster --name vllm-eval-test
kind create cluster --name vllm-eval-test --config kind-config.yaml
```

#### 5. 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :9000
lsof -i :8123

# 프로세스 종료
kill -9 <PID>

# OrbStack 컨테이너 확인 및 정리
docker ps | grep -E "(minio|clickhouse)"
docker stop $(docker ps -q --filter "name=minio-test")
docker stop $(docker ps -q --filter "name=clickhouse-test")
```

#### 6. PostgreSQL 의존성 문제 (pytest 실행 시)

```bash
# 증상: pytest 실행 시 다음과 같은 오류 발생
# ImportError: no pq wrapper available.
# - couldn't import psycopg 'c' implementation: No module named 'psycopg_c'
# - couldn't import psycopg 'binary' implementation: No module named 'psycopg_binary'
# - couldn't import psycopg 'python' implementation: libpq library not found

# 해결 방법 1: PostgreSQL 및 libpq 설치
brew install postgresql@14 libpq

# 해결 방법 2: 환경변수 설정 및 psycopg 재설치
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libpq/lib/pkgconfig"

# psycopg[binary] 재설치
pip install "psycopg[binary]" --force-reinstall

# 검증: pytest 실행 테스트
python -m pytest eval/deepeval_tests/test_llm_rag.py -v --tb=short -x

echo "✅ PostgreSQL 의존성 문제 해결 완료"
```

#### 7. OrbStack 관련 문제

```bash
# OrbStack 재시작
orb restart

# OrbStack 상태 확인
orb status

# Docker 컨텍스트 확인
docker context ls
docker context use orbstack

# Kubernetes 컨텍스트 확인
kubectl config get-contexts
kubectl config use-context orbstack
```

### 로그 확인 방법

```bash
# 테스트 로그 확인
tail -f test_results/*/evalchemy_*.log

# Docker 컨테이너 로그
docker logs <container_id>

# Kubernetes 로그
kubectl logs -f <pod_name>
```

## ⚡ 성능 최적화

### 빌드 시간 단축

```bash
# OrbStack에서 Docker 빌드 캐시 활용 (자동으로 최적화됨)
export DOCKER_BUILDKIT=1

# OrbStack의 빠른 빌드 활용
docker build -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test .

# 병렬 빌드 (OrbStack에서 자동 최적화)
docker build --parallel -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test .

# OrbStack 빌드 캐시 확인
docker system df
```

### 테스트 실행 시간 단축

```bash
# 빠른 테스트만 실행
python -m pytest -m "not slow" -x

# 병렬 테스트 실행
python -m pytest -n auto
```

### 리소스 사용량 모니터링

```bash
# 시스템 리소스 모니터링
top -pid $(pgrep -f python)

# OrbStack 리소스 사용량 확인
orb status
docker stats

# OrbStack 디스크 사용량
orb info
docker system df

# 프로젝트 디스크 사용량 확인
du -sh test_results/
du -sh venv/

# OrbStack VM 리소스 확인
orb config get resources
```

## 📝 테스트 체크리스트

### 푸시 전 필수 확인사항

- [ ] PostgreSQL/libpq 설치 및 환경변수 설정 완료
- [ ] 모든 린트 검사 통과
- [ ] 단위 테스트 100% 통과
- [ ] 스키마 검증 통과
- [ ] Docker 이미지 빌드 성공
- [ ] 컨테이너 실행 테스트 통과
- [ ] Helm 차트 검증 통과
- [ ] 통합 테스트 통과
- [ ] 문서 업데이트 완료

### 성능 기준

- [ ] 단위 테스트 실행 시간 < 2분
- [ ] Docker 이미지 빌드 시간 < 5분
- [ ] 전체 테스트 실행 시간 < 10분
- [ ] 메모리 사용량 < 4GB
- [ ] 디스크 사용량 < 2GB

## 🚀 최종 실행 스크립트

모든 테스트를 한 번에 실행하는 스크립트:

```bash
#!/bin/bash
# 전체 테스트 실행 스크립트

set -e

echo "🚀 VLLM 평가 시스템 로컬 테스트 시작"

# 환경 설정
source venv/bin/activate
source .env

# PostgreSQL 환경변수 설정 (macOS)
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libpq/lib/pkgconfig"

# 1단계: 코드 품질 검사
echo "1️⃣ 코드 품질 검사..."
ruff check . --fix
black . --check
isort . --check-only
mypy scripts/ eval/ --ignore-missing-imports

# 2단계: 스키마 검증
echo "2️⃣ 스키마 검증..."
python scripts/validate_schemas.py

# 3단계: 단위 테스트
echo "3️⃣ 단위 테스트..."
python -m pytest eval/deepeval_tests/test_llm_rag.py -v

# 4단계: 스크립트 테스트
echo "4️⃣ 스크립트 테스트..."
./eval/evalchemy/run_evalchemy.sh --validate-config

# 5단계: Docker 빌드
echo "5️⃣ Docker 이미지 빌드..."
docker build -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test .
docker build -f docker/workflow-tools.Dockerfile -t vllm-eval/workflow-tools:test .

# 6단계: Helm 검증
echo "6️⃣ Helm 차트 검증..."
helm lint charts/argo-workflows/
helm lint charts/clickhouse/
helm lint charts/grafana/

echo "✅ 모든 테스트 완료! GitHub에 푸시할 준비가 되었습니다."
```

이 스크립트를 `test-all.sh`로 저장하고 실행하면 모든 테스트를 자동으로 수행할 수 있습니다.

```bash
chmod +x test-all.sh
./test-all.sh
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. [문제 해결](#문제-해결) 섹션
2. 로그 파일 (`test_results/` 디렉토리)
3. GitHub Issues 템플릿 사용하여 버그 리포트 작성

## 🌟 OrbStack 특별 기능 활용

### OrbStack의 장점

1. **빠른 시작 시간**: Docker Desktop 대비 2-3배 빠른 시작
2. **낮은 리소스 사용량**: 메모리 사용량 50% 절약
3. **내장 Kubernetes**: 별도 설치 없이 즉시 사용 가능
4. **네이티브 성능**: Apple Silicon 최적화
5. **자동 포트 포워딩**: 복잡한 네트워크 설정 불필요

### OrbStack 고급 설정

```bash
# OrbStack 리소스 설정 최적화
orb config set resources.cpu 4
orb config set resources.memory 8GB
orb config set resources.disk 100GB

# Kubernetes 버전 관리
orb list k8s-versions
orb start k8s vllm-eval-prod --version=1.29

# 도메인 설정 (자동 DNS 해결)
orb config set domains.enabled true

# 파일 공유 최적화
orb config set mount.type virtiofs
```

### OrbStack 네트워킹 활용

```bash
# 자동 도메인 접근 (OrbStack 고유 기능)
# http://minio-test.orb.local:9000 으로 접근 가능
# http://clickhouse-test.orb.local:8123 으로 접근 가능

# 컨테이너 간 통신 테스트
docker run --rm --name test-client alpine:latest \
  sh -c "ping -c 3 minio-test && ping -c 3 clickhouse-test"

# Kubernetes 서비스 접근
kubectl port-forward svc/grafana 3000:3000 &
# http://localhost:3000 또는 http://grafana.orb.local:3000
```

### OrbStack 성능 최적화 팁

```bash
# 빌드 성능 향상을 위한 설정
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# OrbStack 캐시 최적화
docker builder prune --filter until=24h
orb prune --all

# 개발 환경 스냅샷 생성
orb snapshot create vllm-eval-baseline
orb snapshot restore vllm-eval-baseline  # 필요시 복원
```

---

**참고**: 
- 이 가이드는 macOS 환경을 기준으로 작성되었습니다. 
- OrbStack은 macOS 전용이므로, Linux나 Windows에서는 Docker Desktop이나 다른 대안을 사용하세요.
- OrbStack 사용 시 더 빠르고 효율적인 개발 환경을 경험할 수 있습니다. 
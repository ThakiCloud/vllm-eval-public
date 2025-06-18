# OrbStack 전체 테스트 스크립트 사용 가이드

## 📋 개요

`scripts/test-all-orbstack.sh`는 macOS + OrbStack 환경에서 VLLM 평가 시스템의 모든 테스트를 자동화하는 스크립트입니다. GitHub에 푸시하기 전 모든 검증을 한 번에 수행할 수 있습니다.

## 🚀 빠른 시작

### 1. 사전 준비

```bash
# OrbStack 설치 (Homebrew 사용)
brew install --cask orbstack

# 필수 도구 설치
brew install python@3.11 kubectl helm jq yq postgresql@14 libpq

# 프로젝트 루트 디렉토리에서 실행
cd /path/to/your/vllm-eval
```

### 2. 스크립트 실행

```bash
# 전체 테스트 실행
./scripts/test-all-orbstack.sh

# 또는 bash로 직접 실행
bash scripts/test-all-orbstack.sh
```

## 🔄 테스트 단계

스크립트는 다음 10단계를 순차적으로 실행합니다:

### 🔧 환경 설정 단계
1. **OrbStack 환경 확인** - OrbStack 설치 및 상태 확인
2. **OrbStack Kubernetes 설정** - 내장 K8s 클러스터 시작
3. **개발 환경 설정** - Python 가상환경, 의존성 설치

### ✅ 코드 품질 검사 단계
4. **코드 품질 검사** - Ruff, Black, isort, MyPy 실행
5. **스키마 및 설정 검증** - 설정 파일 유효성 검사

### 🧪 테스트 실행 단계
6. **단위 테스트** - pytest 실행 및 커버리지 측정
7. **스크립트 기능 테스트** - 개별 스크립트 동작 확인

### 🐳 Docker 관련 테스트
8. **Docker 이미지 빌드** - 병렬 빌드로 시간 단축
9. **컨테이너 실행 테스트** - 빌드된 이미지 동작 확인

### 🔗 통합 테스트 단계
10. **Helm 차트 검증** - 차트 lint 및 템플릿 렌더링
11. **OrbStack 서비스 통합** - MinIO, ClickHouse, PostgreSQL 테스트
12. **Kubernetes 통합** - Pod 배포 및 리소스 관리 테스트
13. **성능 벤치마크** - 리소스 사용량 측정

## 📊 출력 및 결과

### 실행 중 출력
- 🚀 **단계 표시**: 각 테스트 단계의 진행 상황
- ✅ **성공 메시지**: 완료된 작업에 대한 확인
- ⚠️ **경고 메시지**: 선택사항 또는 비필수 실패
- ❌ **오류 메시지**: 중요한 실패 및 해결 방법

### 생성되는 파일
```
test_results/
├── unit_tests.xml              # JUnit 형식 테스트 결과
├── coverage.xml                # 코드 커버리지 XML
├── coverage_html/              # HTML 커버리지 리포트
│   └── index.html
└── test_report_YYYYMMDD_HHMMSS.md  # 최종 테스트 보고서
```

## ⚡ OrbStack 최적화 기능

### 자동화된 환경 설정
- **자동 시작**: OrbStack이 실행되지 않은 경우 자동 시작
- **Kubernetes 활성화**: 내장 K8s 클러스터 자동 활성화
- **컨텍스트 전환**: Docker 및 kubectl 컨텍스트 자동 설정

### 성능 최적화
- **병렬 빌드**: Docker 이미지 동시 빌드로 시간 단축
- **BuildKit 활용**: OrbStack의 최적화된 빌드 엔진 사용
- **자동 도메인**: `.orb.local` 도메인을 통한 서비스 접근

### 리소스 모니터링
- **실시간 상태**: OrbStack 리소스 사용량 모니터링
- **컨테이너 통계**: 실행 중인 컨테이너의 CPU/메모리 사용량
- **디스크 사용량**: 프로젝트 및 Docker 시스템 공간 확인

## 🛠 고급 사용법

### 환경 변수 커스터마이징

스크립트 실행 전 환경 변수를 설정하여 동작을 조정할 수 있습니다:

```bash
# 테스트 네임스페이스 변경
export TEST_NAMESPACE="my-test-namespace"

# 실행 ID 커스터마이징
export RUN_ID="my-custom-test-$(date +%s)"

# 특정 단계 스킵 (고급 사용자용)
export SKIP_DOCKER_BUILD=true
export SKIP_KUBERNETES_TEST=true

./scripts/test-all-orbstack.sh
```

### 부분 실행

특정 단계만 실행하고 싶은 경우 스크립트를 수정하거나 함수를 직접 호출할 수 있습니다:

```bash
# 스크립트를 source로 로드
source scripts/test-all-orbstack.sh

# 특정 함수만 실행
check_code_quality
run_unit_tests
build_docker_images
```

## 🚨 문제 해결

### 일반적인 오류

#### 1. OrbStack 시작 실패
```
❌ OrbStack 시작 시간 초과
```
**해결책**:
```bash
# OrbStack 재시작
orb restart
# 또는 수동으로 앱 재시작
open -a OrbStack
```

#### 2. Python 의존성 오류
```
❌ PostgreSQL 의존성 문제
```
**해결책**:
```bash
# PostgreSQL 라이브러리 재설치
brew reinstall postgresql@14 libpq
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
pip install "psycopg[binary]" --force-reinstall
```

#### 3. Docker 이미지 빌드 실패
```
❌ Docker 이미지 빌드 실패
```
**해결책**:
```bash
# Docker 캐시 정리
docker system prune -f
docker builder prune -f

# 빌드 재시도
docker build --no-cache -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test .
```

#### 4. Kubernetes 클러스터 문제
```
❌ Kubernetes Pod 배포 실패
```
**해결책**:
```bash
# 클러스터 재시작
orb delete k8s
orb start k8s
kubectl config use-context orbstack
```

### 디버깅 모드

상세한 디버깅 정보가 필요한 경우:

```bash
# Bash 디버그 모드로 실행
bash -x scripts/test-all-orbstack.sh

# 또는 환경 변수 설정
export DEBUG=true
export VERBOSE=true
./scripts/test-all-orbstack.sh
```

## 📈 성능 지표

### 예상 실행 시간 (Apple Silicon 기준)
- **전체 테스트**: 8-12분
- **코드 품질 검사**: 30초
- **단위 테스트**: 1-2분
- **Docker 빌드**: 3-5분 (병렬 빌드)
- **통합 테스트**: 2-3분

### 리소스 요구사항
- **RAM**: 최소 8GB, 권장 16GB
- **디스크**: 최소 5GB 여유 공간
- **CPU**: 멀티코어 권장 (병렬 처리 최적화)

## 🔄 CI/CD 통합

### GitHub Actions와 연계

```yaml
# .github/workflows/local-test.yml
name: Local Test Validation

on:
  pull_request:
    branches: [ main ]

jobs:
  validate-local-test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install OrbStack
        run: |
          brew install --cask orbstack
          
      - name: Run OrbStack Tests
        run: |
          ./scripts/test-all-orbstack.sh
          
      - name: Upload Test Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test_results/
```

### Pre-commit Hook 설정

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "🚀 로컬 테스트 실행 중..."
./scripts/test-all-orbstack.sh

if [ $? -eq 0 ]; then
    echo "✅ 모든 테스트 통과! 커밋을 진행합니다."
else
    echo "❌ 테스트 실패! 문제를 수정한 후 다시 커밋하세요."
    exit 1
fi
```

## 🎯 베스트 프랙티스

### 1. 정기적인 실행
- **개발 중**: 주요 변경사항 후 실행
- **PR 전**: 반드시 실행하여 문제 사전 발견
- **릴리스 전**: 최종 검증으로 실행

### 2. 결과 분석
- **커버리지 리포트**: `test_results/coverage_html/index.html` 확인
- **테스트 보고서**: 생성된 마크다운 보고서 검토
- **성능 지표**: 실행 시간 및 리소스 사용량 모니터링

### 3. 환경 관리
- **가상환경 격리**: 프로젝트별 독립적인 Python 환경 유지
- **정기적인 정리**: `docker system prune` 주기적 실행
- **의존성 업데이트**: requirements 파일 정기적 검토

## 📞 지원 및 문의

### 문제 보고
1. **로그 수집**: `test_results/` 디렉토리의 모든 파일
2. **시스템 정보**: `orb status`, `docker info` 출력
3. **오류 메시지**: 정확한 오류 내용과 발생 단계

### 추가 리소스
- **OrbStack 공식 문서**: https://docs.orbstack.dev/
- **프로젝트 문서**: `docs/local-testing-guide.md`
- **아키텍처 가이드**: 프로젝트 규칙의 Architecture 섹션

---

**참고**: 이 스크립트는 macOS + OrbStack 환경에 최적화되어 있습니다. 다른 환경에서는 `docs/local-testing-guide.md`의 해당 섹션을 참조하세요. 
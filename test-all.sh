#!/bin/bash

#
# VLLM 평가 시스템 전체 테스트 실행 스크립트
#
# 이 스크립트는 GitHub에 푸시하기 전에 모든 테스트를 자동으로 실행합니다.
# macOS 환경에서 실행하도록 설계되었습니다.
#
# 사용법:
#   ./test-all.sh [OPTIONS]
#
# 옵션:
#   --skip-docker    Docker 이미지 빌드 건너뛰기
#   --skip-k8s       Kubernetes 테스트 건너뛰기
#   --quick          빠른 테스트만 실행
#   --verbose        상세 로그 출력
#   --help           도움말 표시
#

set -euo pipefail

# 스크립트 설정
SCRIPT_NAME="test-all.sh"
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 기본 설정
SKIP_DOCKER=false
SKIP_K8S=false
QUICK_MODE=false
VERBOSE=false
START_TIME=$(date +%s)

# 로그 함수
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${timestamp}: $message" >&2
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${timestamp}: $message"
            ;;
        INFO)
            echo -e "${GREEN}[INFO]${NC} ${timestamp}: $message"
            ;;
        DEBUG)
            if [[ "$VERBOSE" == "true" ]]; then
                echo -e "${CYAN}[DEBUG]${NC} ${timestamp}: $message"
            fi
            ;;
        STEP)
            echo -e "${BLUE}[STEP]${NC} ${timestamp}: $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp}: $message"
            ;;
        *)
            echo -e "${PURPLE}[${level}]${NC} ${timestamp}: $message"
            ;;
    esac
}

show_usage() {
    cat << EOF
사용법: $SCRIPT_NAME [OPTIONS]

VLLM 평가 시스템 전체 테스트 실행 스크립트

OPTIONS:
    --skip-docker       Docker 이미지 빌드 테스트 건너뛰기
    --skip-k8s          Kubernetes 관련 테스트 건너뛰기
    --quick             빠른 테스트만 실행 (린트, 단위테스트만)
    --verbose           상세 로그 출력
    -h, --help          이 도움말 표시

EXAMPLES:
    # 전체 테스트 실행
    $SCRIPT_NAME

    # Docker 빌드 제외하고 실행
    $SCRIPT_NAME --skip-docker

    # 빠른 테스트만 실행
    $SCRIPT_NAME --quick

    # 상세 로그와 함께 실행
    $SCRIPT_NAME --verbose

EOF
}

# 명령줄 인수 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-k8s)
            SKIP_K8S=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            SKIP_DOCKER=true
            SKIP_K8S=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log ERROR "알 수 없는 옵션: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 정리 함수
cleanup() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    log INFO "정리 작업 중..."
    
    # 테스트 서비스 정리
    if [[ -f "docker-compose.test.yml" ]]; then
        docker-compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true
    fi
    
    # OrbStack 테스트 컨테이너 정리
    docker stop minio-test clickhouse-test 2>/dev/null || true
    docker rm minio-test clickhouse-test 2>/dev/null || true
    
    # Kind 클러스터 정리
    if command -v kind &> /dev/null; then
        kind delete cluster --name vllm-eval-test 2>/dev/null || true
    fi
    
    # OrbStack 클러스터 정리 (필요시)
    if command -v orb &> /dev/null; then
        orb delete k8s vllm-eval-cluster 2>/dev/null || true
    fi
    
    # 임시 파일 정리
    rm -f kind-config.yaml docker-compose.test.yml 2>/dev/null || true
    
    if [[ $exit_code -eq 0 ]]; then
        log SUCCESS "모든 테스트가 성공적으로 완료되었습니다! (소요시간: ${duration}초)"
        log SUCCESS "GitHub에 푸시할 준비가 되었습니다. 🚀"
    else
        log ERROR "테스트 실행 중 오류가 발생했습니다. (종료 코드: $exit_code)"
        log ERROR "로그를 확인하고 문제를 해결한 후 다시 시도하세요."
    fi
    
    exit $exit_code
}

# 신호 핸들러 설정
trap cleanup EXIT INT TERM

# 사전 조건 확인
check_prerequisites() {
    log STEP "사전 조건 확인 중..."
    
    local missing_tools=()
    
    # 필수 도구 확인
    local required_tools=(
        "python3"
        "pip3"
        "docker"
        "jq"
    )
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    # 선택적 도구 확인
    if [[ "$SKIP_DOCKER" == "false" ]]; then
        if ! command -v "docker" &> /dev/null; then
            missing_tools+=("docker")
        fi
    fi
    
    if [[ "$SKIP_K8S" == "false" ]]; then
        local k8s_tools=("kubectl" "helm" "kind")
        for tool in "${k8s_tools[@]}"; do
            if ! command -v "$tool" &> /dev/null; then
                missing_tools+=("$tool")
            fi
        done
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log ERROR "다음 도구들이 설치되지 않았습니다: ${missing_tools[*]}"
        log ERROR "docs/local-testing-guide.md를 참조하여 필수 도구를 설치하세요."
        return 1
    fi
    
    # Python 버전 확인
    local python_version=$(python3 --version | cut -d' ' -f2)
    local major_version=$(echo "$python_version" | cut -d'.' -f1)
    local minor_version=$(echo "$python_version" | cut -d'.' -f2)
    
    if [[ "$major_version" -lt 3 ]] || [[ "$major_version" -eq 3 && "$minor_version" -lt 9 ]]; then
        log ERROR "Python 3.9 이상이 필요합니다. 현재 버전: $python_version"
        return 1
    fi
    
    # Docker 상태 확인
    if [[ "$SKIP_DOCKER" == "false" ]]; then
        if ! docker info &> /dev/null; then
            log ERROR "Docker가 실행되지 않았습니다."
            if command -v orb &> /dev/null; then
                log ERROR "OrbStack을 시작하세요: open -a OrbStack"
            else
                log ERROR "Docker Desktop을 시작하세요: open -a Docker"
            fi
            return 1
        fi
        
        # OrbStack 사용 여부 확인
        if command -v orb &> /dev/null && docker context show | grep -q "orbstack"; then
            log INFO "OrbStack 환경에서 실행 중"
        else
            log INFO "Docker Desktop 환경에서 실행 중"
        fi
    fi
    
    log SUCCESS "사전 조건 확인 완료"
    return 0
}

# 환경 설정
setup_environment() {
    log STEP "환경 설정 중..."
    
    # 가상환경 확인 및 생성
    if [[ ! -d "venv" ]]; then
        log INFO "Python 가상환경 생성 중..."
        python3 -m venv venv
    fi
    
    # 가상환경 활성화
    source venv/bin/activate
    log DEBUG "가상환경 활성화됨: $(which python)"
    
    # pip 업그레이드
    pip install --upgrade pip setuptools wheel --quiet
    
    # 의존성 설치
    if [[ -f "requirements-dev.txt" ]]; then
        log INFO "개발 의존성 설치 중..."
        pip install -r requirements-dev.txt --quiet
    fi
    
    if [[ -f "requirements-test.txt" ]]; then
        log INFO "테스트 의존성 설치 중..."
        pip install -r requirements-test.txt --quiet
    fi
    
    # 환경 변수 설정
    export PYTHONPATH="$SCRIPT_DIR"
    export LOG_LEVEL="INFO"
    if [[ "$VERBOSE" == "true" ]]; then
        export LOG_LEVEL="DEBUG"
    fi
    
    log SUCCESS "환경 설정 완료"
}

# 1단계: 코드 품질 검사
run_code_quality_checks() {
    log STEP "1단계: 코드 품질 검사 실행 중..."
    
    # Ruff 린팅
    log INFO "Ruff 린팅 실행 중..."
    if ruff check . --fix; then
        log SUCCESS "Ruff 린팅 통과"
    else
        log ERROR "Ruff 린팅 실패"
        return 1
    fi
    
    # Black 포맷팅 확인
    log INFO "Black 포맷팅 확인 중..."
    if black . --check --diff; then
        log SUCCESS "Black 포맷팅 통과"
    else
        log ERROR "Black 포맷팅 실패. 'black .'을 실행하여 수정하세요."
        return 1
    fi
    
    # isort import 정렬 확인
    log INFO "isort import 정렬 확인 중..."
    if isort . --check-only --diff; then
        log SUCCESS "isort 확인 통과"
    else
        log ERROR "import 정렬 실패. 'isort .'을 실행하여 수정하세요."
        return 1
    fi
    
    # MyPy 타입 검사 (선택적)
    if command -v mypy &> /dev/null; then
        log INFO "MyPy 타입 검사 실행 중..."
        if mypy scripts/ eval/ --ignore-missing-imports; then
            log SUCCESS "MyPy 타입 검사 통과"
        else
            log WARN "MyPy 타입 검사에서 경고가 발생했습니다."
        fi
    else
        log DEBUG "MyPy가 설치되지 않아 타입 검사를 건너뜁니다."
    fi
    
    log SUCCESS "1단계: 코드 품질 검사 완료"
}

# 2단계: 스키마 및 설정 검증
run_schema_validation() {
    log STEP "2단계: 스키마 및 설정 검증 실행 중..."
    
    # 스키마 검증 스크립트 실행
    if [[ -f "scripts/validate_schemas.py" ]]; then
        log INFO "스키마 검증 실행 중..."
        if python scripts/validate_schemas.py; then
            log SUCCESS "스키마 검증 통과"
        else
            log ERROR "스키마 검증 실패"
            return 1
        fi
    else
        log WARN "스키마 검증 스크립트를 찾을 수 없습니다."
    fi
    
    # Evalchemy 설정 검증
    if [[ -f "eval/evalchemy/configs/eval_config.json" ]]; then
        log INFO "Evalchemy 설정 검증 중..."
        if jq empty eval/evalchemy/configs/eval_config.json; then
            local benchmark_count=$(jq '.benchmarks | length' eval/evalchemy/configs/eval_config.json)
            log SUCCESS "Evalchemy 설정 유효 ($benchmark_count개 벤치마크)"
        else
            log ERROR "Evalchemy 설정 파일이 유효하지 않습니다."
            return 1
        fi
    else
        log WARN "Evalchemy 설정 파일을 찾을 수 없습니다."
    fi
    
    # 데이터셋 매니페스트 확인
    if [[ -f "datasets/dataset_manifest.json" ]]; then
        log INFO "데이터셋 매니페스트 검증 중..."
        if jq empty datasets/dataset_manifest.json; then
            local dataset_count=$(jq '.datasets | length' datasets/dataset_manifest.json)
            log SUCCESS "데이터셋 매니페스트 유효 ($dataset_count개 데이터셋)"
        else
            log ERROR "데이터셋 매니페스트가 유효하지 않습니다."
            return 1
        fi
    else
        log INFO "데이터셋 매니페스트가 없습니다. 테스트용으로 생성합니다."
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
        log SUCCESS "테스트용 데이터셋 매니페스트 생성 완료"
    fi
    
    log SUCCESS "2단계: 스키마 및 설정 검증 완료"
}

# 3단계: 단위 테스트
run_unit_tests() {
    log STEP "3단계: 단위 테스트 실행 중..."
    
    # pytest 실행
    local pytest_args=("-v" "--tb=short")
    
    if [[ "$QUICK_MODE" == "true" ]]; then
        pytest_args+=("-x" "--maxfail=1")
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-s")
    fi
    
    # RAG 테스트 실행
    if [[ -f "eval/deepeval_tests/test_llm_rag.py" ]]; then
        log INFO "RAG 평가 테스트 실행 중..."
        if python -m pytest eval/deepeval_tests/test_llm_rag.py "${pytest_args[@]}"; then
            log SUCCESS "RAG 평가 테스트 통과"
        else
            log ERROR "RAG 평가 테스트 실패"
            return 1
        fi
    else
        log WARN "RAG 평가 테스트 파일을 찾을 수 없습니다."
    fi
    
    # 추가 테스트 파일들 실행
    local test_files=($(find . -name "test_*.py" -not -path "./venv/*" -not -path "./.git/*"))
    
    for test_file in "${test_files[@]}"; do
        if [[ "$test_file" != "./eval/deepeval_tests/test_llm_rag.py" ]]; then
            log INFO "테스트 실행 중: $test_file"
            if python -m pytest "$test_file" "${pytest_args[@]}"; then
                log SUCCESS "테스트 통과: $test_file"
            else
                log ERROR "테스트 실패: $test_file"
                return 1
            fi
        fi
    done
    
    # 테스트 커버리지 (선택적)
    if command -v coverage &> /dev/null && [[ "$QUICK_MODE" == "false" ]]; then
        log INFO "테스트 커버리지 확인 중..."
        python -m pytest eval/deepeval_tests/test_llm_rag.py --cov=eval --cov-report=term-missing --cov-report=html --quiet
        log SUCCESS "커버리지 리포트 생성됨: htmlcov/index.html"
    fi
    
    log SUCCESS "3단계: 단위 테스트 완료"
}

# 4단계: 스크립트 기능 테스트
run_script_tests() {
    log STEP "4단계: 스크립트 기능 테스트 실행 중..."
    
    # 중복 제거 스크립트 테스트
    if [[ -f "scripts/dedup_datasets.py" ]]; then
        log INFO "중복 제거 스크립트 테스트 중..."
        
        # 테스트 데이터 생성
        mkdir -p test_datasets
        cat > test_datasets/test_data.jsonl << 'EOF'
{"input": "What is AI?", "output": "AI is artificial intelligence."}
{"input": "What is AI?", "output": "AI is artificial intelligence."}
{"input": "What is ML?", "output": "ML is machine learning."}
EOF
        
        if python scripts/dedup_datasets.py \
            --input-dir test_datasets \
            --output-dir test_datasets/deduped \
            --threshold 0.2 \
            --dry-run; then
            log SUCCESS "중복 제거 스크립트 테스트 통과"
        else
            log ERROR "중복 제거 스크립트 테스트 실패"
            return 1
        fi
        
        # 테스트 데이터 정리
        rm -rf test_datasets
    else
        log WARN "중복 제거 스크립트를 찾을 수 없습니다."
    fi
    
    # Evalchemy 스크립트 테스트
    if [[ -f "eval/evalchemy/run_evalchemy.sh" ]]; then
        log INFO "Evalchemy 스크립트 테스트 중..."
        
        chmod +x eval/evalchemy/run_evalchemy.sh
        
        # 도움말 테스트
        if ./eval/evalchemy/run_evalchemy.sh --help > /dev/null; then
            log SUCCESS "Evalchemy 스크립트 도움말 테스트 통과"
        else
            log ERROR "Evalchemy 스크립트 도움말 테스트 실패"
            return 1
        fi
        
        # 설정 검증 테스트
        if ./eval/evalchemy/run_evalchemy.sh --validate-config; then
            log SUCCESS "Evalchemy 설정 검증 테스트 통과"
        else
            log ERROR "Evalchemy 설정 검증 테스트 실패"
            return 1
        fi
        
        # 벤치마크 목록 테스트
        if ./eval/evalchemy/run_evalchemy.sh --list-benchmarks > /dev/null; then
            log SUCCESS "Evalchemy 벤치마크 목록 테스트 통과"
        else
            log ERROR "Evalchemy 벤치마크 목록 테스트 실패"
            return 1
        fi
    else
        log WARN "Evalchemy 실행 스크립트를 찾을 수 없습니다."
    fi
    
    log SUCCESS "4단계: 스크립트 기능 테스트 완료"
}

# 5단계: Docker 이미지 빌드 테스트
run_docker_tests() {
    if [[ "$SKIP_DOCKER" == "true" ]]; then
        log INFO "Docker 테스트를 건너뜁니다."
        return 0
    fi
    
    log STEP "5단계: Docker 이미지 빌드 테스트 실행 중..."
    
    # Docker 상태 확인
    if ! docker info &> /dev/null; then
        log ERROR "Docker가 실행되지 않았습니다."
        return 1
    fi
    
    # Deepeval 이미지 빌드
    if [[ -f "docker/deepeval.Dockerfile" ]]; then
        log INFO "Deepeval 이미지 빌드 중..."
        if docker build -f docker/deepeval.Dockerfile -t vllm-eval/deepeval:test . --quiet; then
            log SUCCESS "Deepeval 이미지 빌드 완료"
        else
            log ERROR "Deepeval 이미지 빌드 실패"
            return 1
        fi
    fi
    
    # Evalchemy 이미지 빌드 (새 버전 - mlfoundations/Evalchemy 기반)
    if [[ -f "docker/evalchemy.Dockerfile" ]]; then
        log INFO "Evalchemy 이미지 빌드 중... (mlfoundations/Evalchemy 기반)"
        if docker build -f docker/evalchemy.Dockerfile -t vllm-eval/evalchemy:test . --quiet; then
            log SUCCESS "Evalchemy 이미지 빌드 완료"
        else
            log ERROR "Evalchemy 이미지 빌드 실패"
            return 1
        fi
    fi
    
    # Legacy Evalchemy 이미지 빌드 (기존 lm-eval 기반)
    if [[ -f "docker/legacy-evalchemy.Dockerfile" ]]; then
        log INFO "Legacy Evalchemy 이미지 빌드 중... (lm-eval 기반)"
        if docker build -f docker/legacy-evalchemy.Dockerfile -t vllm-eval/legacy-evalchemy:test . --quiet; then
            log SUCCESS "Legacy Evalchemy 이미지 빌드 완료"
        else
            log ERROR "Legacy Evalchemy 이미지 빌드 실패"
            return 1
        fi
    fi
    
    # Workflow Tools 이미지 빌드
    if [[ -f "docker/workflow-tools.Dockerfile" ]]; then
        log INFO "Workflow Tools 이미지 빌드 중..."
        if docker build -f docker/workflow-tools.Dockerfile -t vllm-eval/workflow-tools:test . --quiet; then
            log SUCCESS "Workflow Tools 이미지 빌드 완료"
        else
            log ERROR "Workflow Tools 이미지 빌드 실패"
            return 1
        fi
    fi
    
    # 컨테이너 실행 테스트
    log INFO "컨테이너 실행 테스트 중..."
    
    # Deepeval 컨테이너 테스트
    if docker run --rm vllm-eval/deepeval:test python -c "
import deepeval
from deepeval.test_case import LLMTestCase
print('Deepeval 컨테이너 정상 작동')
" > /dev/null 2>&1; then
        log SUCCESS "Deepeval 컨테이너 테스트 통과"
    else
        log ERROR "Deepeval 컨테이너 테스트 실패"
        return 1
    fi
    
    # Workflow Tools 컨테이너 테스트
    if docker run --rm vllm-eval/workflow-tools:test sh -c "
yq --version && jq --version && kubectl version --client && helm version --client
" > /dev/null 2>&1; then
        log SUCCESS "Workflow Tools 컨테이너 테스트 통과"
    else
        log ERROR "Workflow Tools 컨테이너 테스트 실패"
        return 1
    fi
    
    # 이미지 크기 확인
    log INFO "빌드된 이미지 크기:"
    docker images | grep vllm-eval | while read -r line; do
        log INFO "  $line"
    done
    
    log SUCCESS "5단계: Docker 이미지 빌드 테스트 완료"
}

# 6단계: Kubernetes 테스트
run_kubernetes_tests() {
    if [[ "$SKIP_K8S" == "true" ]]; then
        log INFO "Kubernetes 테스트를 건너뜁니다."
        return 0
    fi
    
    log STEP "6단계: Kubernetes 테스트 실행 중..."
    
    # Helm 차트 검증
    log INFO "Helm 차트 검증 중..."
    
    local charts=("argo-workflows" "clickhouse" "grafana")
    
    for chart in "${charts[@]}"; do
        if [[ -d "charts/$chart" ]]; then
            log INFO "Helm 차트 검증 중: $chart"
            
            if helm lint "charts/$chart/" > /dev/null 2>&1; then
                log SUCCESS "Helm 차트 린트 통과: $chart"
            else
                log ERROR "Helm 차트 린트 실패: $chart"
                return 1
            fi
            
            if helm template "test-$chart" "charts/$chart/" --debug --dry-run > /dev/null 2>&1; then
                log SUCCESS "Helm 템플릿 테스트 통과: $chart"
            else
                log ERROR "Helm 템플릿 테스트 실패: $chart"
                return 1
            fi
        else
            log WARN "Helm 차트를 찾을 수 없습니다: $chart"
        fi
    done
    
    log SUCCESS "6단계: Kubernetes 테스트 완료"
}

# 메인 함수
main() {
    log INFO "🚀 VLLM 평가 시스템 전체 테스트 시작"
    log INFO "스크립트: $SCRIPT_NAME v$SCRIPT_VERSION"
    log INFO "실행 모드: $(if [[ "$QUICK_MODE" == "true" ]]; then echo "빠른 테스트"; else echo "전체 테스트"; fi)"
    
    # 사전 조건 확인
    check_prerequisites
    
    # 환경 설정
    setup_environment
    
    # 테스트 단계별 실행
    run_code_quality_checks
    run_schema_validation
    run_unit_tests
    run_script_tests
    
    if [[ "$QUICK_MODE" == "false" ]]; then
        run_docker_tests
        run_kubernetes_tests
    fi
    
    log SUCCESS "모든 테스트 단계가 성공적으로 완료되었습니다!"
}

# 스크립트가 직접 실행될 때만 main 함수 호출
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 
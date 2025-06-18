#!/bin/bash
set -e

echo "🚀 macOS OrbStack VLLM 로컬 평가 통합 실행"
echo "============================================="

# 환경 변수 설정
export OUTPUT_DIR="./test_results"
export RUN_ID="local_eval_$(date +%Y%m%d_%H%M%S)"

# 색상 코드 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. 환경 확인
print_step "1. 환경 확인"

# Python 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "가상환경이 활성화되지 않았습니다. 자동으로 활성화합니다."
    source venv/bin/activate
fi

# 필수 패키지 확인
print_step "2. 필수 패키지 확인"
if ! python -c "import deepeval" 2>/dev/null; then
    print_warning "deepeval이 설치되지 않았습니다. 설치 중..."
    pip install "deepeval[all]"
fi

if ! python -c "import requests" 2>/dev/null; then
    print_warning "requests가 설치되지 않았습니다. 설치 중..."
    pip install requests
fi

print_success "필수 패키지 확인 완료"

# 3. 결과 디렉토리 생성
print_step "3. 결과 디렉토리 생성"
mkdir -p $OUTPUT_DIR
print_success "결과 디렉토리 생성: $OUTPUT_DIR"

# 4. VLLM 서버 상태 확인
print_step "4. VLLM 서버 상태 확인"

VLLM_ENDPOINTS=("http://localhost:8000" "http://localhost:1234" "http://localhost:7860")
VLLM_FOUND=false
VLLM_ENDPOINT=""

for endpoint in "${VLLM_ENDPOINTS[@]}"; do
    if curl -s -f "$endpoint/health" > /dev/null 2>&1 || curl -s -f "$endpoint/v1/models" > /dev/null 2>&1; then
        VLLM_FOUND=true
        VLLM_ENDPOINT="$endpoint"
        break
    fi
done

if [ "$VLLM_FOUND" = true ]; then
    print_success "VLLM 서버 발견: $VLLM_ENDPOINT"
    export VLLM_MODEL_ENDPOINT="$VLLM_ENDPOINT/v1"
    
    # 5. 실제 VLLM 서버 테스트
    print_step "5. 실제 VLLM 서버로 평가 실행"
    python scripts/run_vllm_deepeval_test.py
    
else
    print_warning "VLLM 서버를 찾을 수 없습니다. Mock 테스트를 실행합니다."
    
    # 5. Mock 테스트 실행
    print_step "5. Mock 모델로 평가 실행"
    python scripts/run_simple_deepeval_test.py
fi

# 6. 결과 요약
print_step "6. 평가 결과 요약"

echo ""
echo "📊 평가 완료!"
echo "============"
echo "실행 ID: $RUN_ID"
echo "결과 디렉토리: $OUTPUT_DIR"
echo ""

# 생성된 결과 파일 나열
if [ -d "$OUTPUT_DIR" ]; then
    echo "📁 생성된 결과 파일:"
    for file in "$OUTPUT_DIR"/*.json; do
        if [ -f "$file" ]; then
            echo "  - $(basename "$file")"
        fi
    done
    echo ""
fi

# 7. 결과 미리보기
print_step "7. 결과 미리보기"

# 가장 최근 결과 파일 찾기
LATEST_RESULT=$(ls -t "$OUTPUT_DIR"/*.json 2>/dev/null | head -1)

if [ -n "$LATEST_RESULT" ]; then
    echo "최신 결과 파일: $(basename "$LATEST_RESULT")"
    echo ""
    
    # 요약 정보 출력
    if command -v jq >/dev/null 2>&1; then
        echo "📈 요약 정보:"
        jq -r '
            if .summary then
                "  모델: " + .summary.model_name +
                "\n  총 테스트: " + (.summary.total_tests | tostring) +
                (if .summary.average_score then "\n  평균 점수: " + (.summary.average_score | tostring) else "" end) +
                (if .summary.status then "\n  상태: " + .summary.status else "" end)
            else
                "  요약 정보를 찾을 수 없습니다."
            end
        ' "$LATEST_RESULT"
    else
        echo "jq가 설치되지 않아 요약 정보를 표시할 수 없습니다."
        echo "결과 파일을 직접 확인해주세요: $LATEST_RESULT"
    fi
else
    print_warning "생성된 결과 파일을 찾을 수 없습니다."
fi

echo ""
print_success "로컬 VLLM 평가가 완료되었습니다!"

# 8. 다음 단계 안내
print_step "8. 다음 단계"
echo "결과를 확인하려면:"
echo "  1. JSON 파일 직접 보기: cat $OUTPUT_DIR/*.json"
echo "  2. 브라우저에서 보기: open $OUTPUT_DIR"
if [ "$VLLM_FOUND" = false ]; then
    echo ""
    echo "실제 VLLM 서버로 테스트하려면:"
    echo "  1. VLLM 서버 시작:"
    echo "     docker run -d --name vllm-server --gpus all -p 8000:8000 \\"
    echo "       vllm/vllm-openai:latest --model Qwen/Qwen2-7B-Instruct \\"
    echo "       --served-model-name qwen3-8b"
    echo "  2. 이 스크립트 다시 실행: ./scripts/run_complete_local_evaluation.sh"
fi
echo "" 
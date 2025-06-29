#!/bin/bash
set -euo pipefail

# 성능 벤치마크 실행 스크립트
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/configs/vllm_benchmark.json"

# 기본 설정
VLLM_ENDPOINT="${VLLM_ENDPOINT:-http://localhost:8000}"
RESULTS_DIR="${PROJECT_ROOT}/results/performance"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🚀 VLLM 성능 벤치마크 시작"
echo "📡 엔드포인트: $VLLM_ENDPOINT"
echo "📁 결과 디렉토리: $RESULTS_DIR"

# 결과 디렉토리 생성
mkdir -p "$RESULTS_DIR"

# yq 설치 확인
if ! command -v yq &> /dev/null; then
    echo "❌ 'yq'가 필요합니다. 설치: brew install yq"
    exit 1
fi

# 시나리오 개수 확인
scenario_count=$(yq e '.vllm_benchmark.scenarios | length' "$CONFIG_FILE")
echo "📊 총 ${scenario_count}개 시나리오 실행 예정"

# 각 시나리오 실행
for i in $(seq 0 $((scenario_count - 1))); do
    # 시나리오 정보 추출
    name=$(yq e ".vllm_benchmark.scenarios[$i].name" "$CONFIG_FILE")
    description=$(yq e ".vllm_benchmark.scenarios[$i].description" "$CONFIG_FILE")
    model=$(yq e ".vllm_benchmark.scenarios[$i].model" "$CONFIG_FILE")
    served_model_name=$(yq e ".vllm_benchmark.scenarios[$i].served_model_name" "$CONFIG_FILE")
    max_concurrency=$(yq e ".vllm_benchmark.scenarios[$i].max_concurrency" "$CONFIG_FILE")
    random_input_len=$(yq e ".vllm_benchmark.scenarios[$i].random_input_len" "$CONFIG_FILE")
    random_output_len=$(yq e ".vllm_benchmark.scenarios[$i].random_output_len" "$CONFIG_FILE")
    num_prompts=$(yq e ".vllm_benchmark.scenarios[$i].num_prompts" "$CONFIG_FILE")
    
    echo ""
    echo "▶ [$((i+1))/$scenario_count] 시나리오: $name"
    echo "  📝 설명: $description"
    echo "  🎯 모델: $model"
    echo "  🔀 동시성: $max_concurrency"
    echo "  📥 입력: ${random_input_len} 토큰"
    echo "  📤 출력: ${random_output_len} 토큰"
    echo "  📊 프롬프트: $num_prompts 개"
    
    # 시나리오별 결과 디렉토리
    scenario_dir="${RESULTS_DIR}/${name}_${TIMESTAMP}"
    mkdir -p "$scenario_dir"
    
    # Docker로 벤치마크 실행
    docker run --rm \
        -v "$scenario_dir:/results" \
        -e VLLM_ENDPOINT="$VLLM_ENDPOINT" \
        -e MODEL_NAME="$model" \
        -e SERVED_MODEL_NAME="$served_model_name" \
        -e MAX_CONCURRENCY="$max_concurrency" \
        -e RANDOM_INPUT_LEN="$random_input_len" \
        -e RANDOM_OUTPUT_LEN="$random_output_len" \
        -e NUM_PROMPTS="$num_prompts" \
        -e TZ=Asia/Seoul \
        vllm-benchmark:latest
    
    echo "  ✅ 시나리오 '$name' 완료"
done

echo ""
echo "🎉 모든 성능 벤치마크 완료!"
echo "📁 결과 위치: $RESULTS_DIR"
echo "📊 결과 분석을 위해 다음 명령어 실행:"
echo "   python3 scripts/analyze_performance_results.py $RESULTS_DIR" 
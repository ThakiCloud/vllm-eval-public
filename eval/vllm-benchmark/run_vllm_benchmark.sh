#!/bin/bash
set -euo pipefail

# YAML 파싱을 위한 Python 헬퍼 스크립트 생성
cat > /tmp/parse_yaml.py << 'EOF'
#!/usr/bin/env python3
import yaml
import sys
import json
import os

def parse_vllm_config(config_path):
    """VLLM 벤치마크 설정 파일 파싱"""
    if not os.path.exists(config_path):
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        benchmark_config = config.get('vllm_benchmark', {})
        defaults = benchmark_config.get('defaults', {})
        scenarios = benchmark_config.get('scenarios', [])
        
        # 활성화된 시나리오만 필터링 (주석 처리되지 않은 것들)
        active_scenarios = []
        for scenario in scenarios:
            if isinstance(scenario, dict) and 'name' in scenario:
                active_scenarios.append(scenario)
        
        result = {
            'defaults': defaults,
            'scenarios': active_scenarios
        }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 설정 파일 파싱 오류: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python3 parse_yaml.py <config_path>", file=sys.stderr)
        sys.exit(1)
    
    parse_vllm_config(sys.argv[1])
EOF

# 기본 설정 (Docker 환경 자동 감지)
if [ -f /.dockerenv ]; then
    # Docker 컨테이너 내부에서 실행 중
    DEFAULT_ENDPOINT="http://host.docker.internal:8000"
    CONFIG_PATH="/app/configs/vllm_benchmark.yaml"
else
    # 호스트에서 직접 실행 중
    DEFAULT_ENDPOINT="http://localhost:8000"
    CONFIG_PATH="${CONFIG_PATH:-configs/vllm_benchmark.yaml}"
fi

# 환경 변수 기본값 설정
VLLM_ENDPOINT="${VLLM_ENDPOINT:-$DEFAULT_ENDPOINT}"
OUTPUT_DIR="${OUTPUT_DIR:-/results}"
PARSED_DIR="$(dirname "$OUTPUT_DIR")/parsed"
REQUEST_RATE="${REQUEST_RATE:-1.0}"

# 출력 디렉토리 생성
mkdir -p "$OUTPUT_DIR"
mkdir -p "$PARSED_DIR"

# 타임스탬프 생성 (UTC)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
UTC_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
MAIN_LOG_FILE="$OUTPUT_DIR/vllm_benchmark_main_${TIMESTAMP}.log"

echo "🚀 VLLM 멀티 시나리오 벤치마크 시작 - $UTC_TIME" | tee "$MAIN_LOG_FILE"
echo "📡 서버: $VLLM_ENDPOINT" | tee -a "$MAIN_LOG_FILE"
echo "📁 설정 파일: $CONFIG_PATH" | tee -a "$MAIN_LOG_FILE"
echo "💾 결과 디렉토리: $OUTPUT_DIR" | tee -a "$MAIN_LOG_FILE"
echo "===============================================" | tee -a "$MAIN_LOG_FILE"

# YAML 설정 파싱
echo "📋 설정 파일 파싱 중..." | tee -a "$MAIN_LOG_FILE"
CONFIG_JSON=$(python3 /tmp/parse_yaml.py "$CONFIG_PATH")
if [ $? -ne 0 ]; then
    echo "❌ 설정 파일 파싱 실패" | tee -a "$MAIN_LOG_FILE"
    exit 1
fi

# 시나리오 개수 확인
SCENARIO_COUNT=$(echo "$CONFIG_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['scenarios']))")
echo "📊 발견된 시나리오 개수: $SCENARIO_COUNT" | tee -a "$MAIN_LOG_FILE"

if [ "$SCENARIO_COUNT" -eq 0 ]; then
    echo "❌ 실행할 시나리오가 없습니다." | tee -a "$MAIN_LOG_FILE"
    exit 1
fi

# defaults 설정 추출
DEFAULTS_JSON=$(echo "$CONFIG_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data['defaults']))")

# 각 시나리오 실행
for i in $(seq 0 $((SCENARIO_COUNT - 1))); do
    SCENARIO_START_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
    echo "" | tee -a "$MAIN_LOG_FILE"
    echo "🎯 시나리오 $((i + 1))/$SCENARIO_COUNT 실행 중... ($SCENARIO_START_TIME)" | tee -a "$MAIN_LOG_FILE"
    echo "===============================================" | tee -a "$MAIN_LOG_FILE"
    
    # 현재 시나리오 정보 추출
    SCENARIO_JSON=$(echo "$CONFIG_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
scenario = data['scenarios'][$i]
defaults = data['defaults']

# defaults와 scenario 병합 (scenario가 우선)
merged = {**defaults, **scenario}
print(json.dumps(merged))
")
    
    # 시나리오별 설정 추출
    SCENARIO_NAME=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', 'unknown'))")
    SCENARIO_DESC=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('description', 'No description'))")
    MODEL_NAME=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('model', 'vllm-model'))")
    SERVED_MODEL_NAME=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('served_model_name', data.get('model', 'vllm-model')))")
    ENDPOINT_PATH=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('endpoint_path', '/v1/chat/completions'))")
    MAX_CONCURRENCY=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('max_concurrency', 1))")
    RANDOM_INPUT_LEN=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('random_input_len', 1024))")
    RANDOM_OUTPUT_LEN=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('random_output_len', 128))")
    NUM_PROMPTS=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('num_prompts', data.get('max_concurrency', 1) * 2))")
    BACKEND=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('backend', 'openai-chat'))")
    DATASET_TYPE=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('dataset_type', 'random'))")
    PERCENTILE_METRICS=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('percentile_metrics', 'ttft,tpot,itl,e2el'))")
    METRIC_PERCENTILES=$(echo "$SCENARIO_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('metric_percentiles', '25,50,75,90,95,99'))")
    
    # 시나리오별 결과 파일
    SCENARIO_RESULT_DIR="$OUTPUT_DIR/scenario_${SCENARIO_NAME}_${TIMESTAMP}"
    SCENARIO_LOG_FILE="$OUTPUT_DIR/scenario_${SCENARIO_NAME}_${TIMESTAMP}.log"
    
    echo "📋 시나리오: $SCENARIO_NAME" | tee -a "$MAIN_LOG_FILE"
    echo "📝 설명: $SCENARIO_DESC" | tee -a "$MAIN_LOG_FILE"
    echo "🎯 모델: $MODEL_NAME" | tee -a "$MAIN_LOG_FILE"
    echo "🏷️  서빙 모델명: $SERVED_MODEL_NAME" | tee -a "$MAIN_LOG_FILE"
    echo "📊 프롬프트 수: $NUM_PROMPTS" | tee -a "$MAIN_LOG_FILE"
    echo "🔀 최대 동시 요청: $MAX_CONCURRENCY" | tee -a "$MAIN_LOG_FILE"
    echo "📥 입력 토큰 길이: $RANDOM_INPUT_LEN" | tee -a "$MAIN_LOG_FILE"
    echo "📤 출력 토큰 길이: $RANDOM_OUTPUT_LEN" | tee -a "$MAIN_LOG_FILE"
    echo "🔧 백엔드: $BACKEND" | tee -a "$MAIN_LOG_FILE"
    echo "💾 결과 디렉토리: $SCENARIO_RESULT_DIR" | tee -a "$MAIN_LOG_FILE"
    
    # 결과 디렉토리 생성
    mkdir -p "$SCENARIO_RESULT_DIR"
    
    # VLLM 공식 benchmark_serving.py 실행
    echo "⚡ 벤치마크 실행 시작..." | tee -a "$MAIN_LOG_FILE"
    cd /app/benchmarks && python3 benchmark_serving.py \
        --backend "$BACKEND" \
        --base-url "$VLLM_ENDPOINT" \
        --endpoint "$ENDPOINT_PATH" \
        --model "$MODEL_NAME" \
        --served-model-name "$SERVED_MODEL_NAME" \
        --dataset-name "$DATASET_TYPE" \
        --random-input-len "$RANDOM_INPUT_LEN" \
        --random-output-len "$RANDOM_OUTPUT_LEN" \
        --max-concurrency "$MAX_CONCURRENCY" \
        --num-prompts "$NUM_PROMPTS" \
        --result-dir "$SCENARIO_RESULT_DIR" \
        --percentile-metrics "$PERCENTILE_METRICS" \
        --metric-percentiles "$METRIC_PERCENTILES" \
        --save-result \
        2>&1 | tee "$SCENARIO_LOG_FILE"
    
    # 벤치마크 실행 결과 확인
    if [ $? -eq 0 ]; then
        SCENARIO_END_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
        echo "✅ 시나리오 '$SCENARIO_NAME' 완료! ($SCENARIO_END_TIME)" | tee -a "$MAIN_LOG_FILE"
        
        # 결과 분석 실행
        RESULT_JSON=$(find "$SCENARIO_RESULT_DIR" -name "*.json" -type f | head -1)
        if [ -n "$RESULT_JSON" ] && [ -f "$RESULT_JSON" ]; then
            echo "📈 시나리오 '$SCENARIO_NAME' 결과 분석 중: $RESULT_JSON" | tee -a "$MAIN_LOG_FILE"
            python3 /app/scripts/analyze_vllm_results.py "$RESULT_JSON" | tee -a "$MAIN_LOG_FILE"
            
            # 표준화된 JSON 파일 경로 생성
            STANDARDIZED_FILENAME="${SCENARIO_NAME}_${TIMESTAMP}_standardized.json"
            STANDARDIZED_JSON_PATH="$PARSED_DIR/$STANDARDIZED_FILENAME"

            echo "🔄 결과 표준화 중 -> $STANDARDIZED_JSON_PATH" | tee -a "$MAIN_LOG_FILE"
            python3 /app/scripts/standardize_vllm_benchmark.py "$RESULT_JSON" --output_file "$STANDARDIZED_JSON_PATH" | tee -a "$MAIN_LOG_FILE"
        else
            echo "⚠️  시나리오 '$SCENARIO_NAME' 결과 JSON 파일을 찾을 수 없습니다: $SCENARIO_RESULT_DIR" | tee -a "$MAIN_LOG_FILE"
        fi
    else
        SCENARIO_ERROR_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
        echo "❌ 시나리오 '$SCENARIO_NAME' 실행 실패! ($SCENARIO_ERROR_TIME)" | tee -a "$MAIN_LOG_FILE"
        echo "📋 로그 파일: $SCENARIO_LOG_FILE" | tee -a "$MAIN_LOG_FILE"
    fi
    
    echo "===============================================" | tee -a "$MAIN_LOG_FILE"
done

echo "" | tee -a "$MAIN_LOG_FILE"
COMPLETION_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
echo "🎉 모든 시나리오 실행 완료! ($COMPLETION_TIME)" | tee -a "$MAIN_LOG_FILE"
echo "📊 총 실행된 시나리오: $SCENARIO_COUNT" | tee -a "$MAIN_LOG_FILE"
echo "📁 결과 디렉토리: $OUTPUT_DIR" | tee -a "$MAIN_LOG_FILE"
echo "📋 메인 로그: $MAIN_LOG_FILE" | tee -a "$MAIN_LOG_FILE"

# 전체 결과 요약 생성
echo "" | tee -a "$MAIN_LOG_FILE"
echo "📈 전체 결과 요약:" | tee -a "$MAIN_LOG_FILE"
echo "===============================================" | tee -a "$MAIN_LOG_FILE"

# 각 시나리오의 결과 JSON 파일들을 찾아서 요약
for scenario_dir in "$OUTPUT_DIR"/scenario_*_"$TIMESTAMP"; do
    if [ -d "$scenario_dir" ]; then
        SCENARIO_NAME=$(basename "$scenario_dir" | sed "s/scenario_//" | sed "s/_${TIMESTAMP}//")
        RESULT_JSON=$(find "$scenario_dir" -name "*.json" -type f | head -1)
        
        if [ -n "$RESULT_JSON" ] && [ -f "$RESULT_JSON" ]; then
            echo "🎯 $SCENARIO_NAME:" | tee -a "$MAIN_LOG_FILE"
            echo "   📊 결과: $RESULT_JSON" | tee -a "$MAIN_LOG_FILE"
        fi
    fi
done

# 임시 파일 정리
rm -f /tmp/parse_yaml.py

FINAL_TIME=$(date '+%Y-%m-%d %H:%M:%S UTC')
echo "🏁 벤치마크 작업 완료! ($FINAL_TIME)" | tee -a "$MAIN_LOG_FILE" 
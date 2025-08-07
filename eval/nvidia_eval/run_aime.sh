#! /bin/bash

MODEL_NAME=$1
OUTPUT_DIR=$2
GPUS=$3
MAX_TOKENS=$4

check_model_endpoint() {
    local base_url=${MODEL_ENDPOINT}
    local endpoint="${base_url}/models"

    # JSON 응답 받아오기
    response=$(curl -s "$endpoint")

    # jq로 id 추출
    model_id=$(echo "$response" | jq -r '.data[0].id')

    if [[ -n "$model_id" && "$model_id" != "null" ]]; then
        echo "INFO: Model endpoint is valid: $model_id"
        echo "$model_id"
    else
        echo "ERROR: Model endpoint is not valid or model ID missing"
        return 1
    fi
    if [[ -z "$MODEL_NAME" ]]; then
        MODEL_NAME="$model_id"
    fi
}

check_model_endpoint || exit 1

if [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-7B" ]; then
    seed_list_aime24=(121 131 141 151 161 171 181 191)
    seed_list_aime25=(111 222 333 444 555 666 777 888)
    MODEL_TYPE="r1"
elif [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-14B" ]; then
    seed_list_aime24=(111 222 333 444 555 666 777 888)
    seed_list_aime25=(111 222 333 444 555 666 777 888)
    MODEL_TYPE="r1"
elif [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-1.1-7B" ]; then
    seed_list_aime24=(100 200 300 400 500 600 700 800)
    seed_list_aime25=(100 200 300 400 500 600 700 800)
    MODEL_TYPE="qwen"
elif [ "$MODEL_NAME" == "qwen3-8b" ]; then
    seed_list_aime24=(100)
    seed_list_aime25=(200)
    MODEL_TYPE="qwen"
else
    seed_list_aime24=(100)
    seed_list_aime25=(200)
    MODEL_TYPE="qwen"
fi


# Extract model display name
if [[ "$MODEL_NAME" == "nvidia/"* ]]; then
    DISPLAY_NAME=$(echo "$MODEL_NAME" | sed 's|nvidia/||')
else
    DISPLAY_NAME="$MODEL_NAME"
fi

echo ""
echo "$DISPLAY_NAME"
echo "===================================="

# AIME 24 Generation
echo "🚀 Starting AIME 2024 inference..."
for seed in ${seed_list_aime24[@]}; do
    bash generate_aime.sh ${MODEL_NAME} ${seed} aime24 ${OUTPUT_DIR} ${MODEL_TYPE} ${GPUS} ${MAX_TOKENS}
done

echo "🔍 Starting AIME 2024 evaluation..."
if [ -d "${OUTPUT_DIR}" ]; then
    python evaluate_aime.py --generation-path ${OUTPUT_DIR} --question-path data/aime24.jsonl
    
    # 결과 파일 확인 및 이동
    if [ -f "${OUTPUT_DIR}/aime24_evaluation_results.json" ]; then
        echo "✅ AIME 2024 evaluation completed! Results saved to ${OUTPUT_DIR}/aime24_evaluation_results.json"
    else
        echo "⚠️  Warning: AIME 2024 evaluation results file not found"
    fi
else
    echo "❌ Error: Output folder ${OUTPUT_DIR} not found for AIME 2024"
fi

echo ""

# AIME 25 Generation
echo "🚀 Starting AIME 2025 inference..."
for seed in ${seed_list_aime25[@]}; do
    bash generate_aime.sh ${MODEL_NAME} ${seed} aime25 ${OUTPUT_DIR} ${MODEL_TYPE} ${GPUS} ${MAX_TOKENS}
done

echo "🔍 Starting AIME 2025 evaluation..."
if [ -d "${OUTPUT_DIR}" ]; then
    python evaluate_aime.py --generation-path ${OUTPUT_DIR} --question-path data/aime25.jsonl
    
    # 결과 파일 확인 및 이동
    if [ -f "${OUTPUT_DIR}/aime25_evaluation_results.json" ]; then
        echo "✅ AIME 2025 evaluation completed! Results saved to ${OUTPUT_DIR}/aime25_evaluation_results.json"
    else
        echo "⚠️  Warning: AIME 2025 evaluation results file not found"
    fi
else
    echo "❌ Error: Output folder ${OUTPUT_DIR} not found for AIME 2025"
fi

echo "🎉 AIME pipeline completed!"

# 결과 표준화
echo ""
echo "📊 Standardizing AIME results..."
# 표준화 스크립트는 실행 경로 기준 'scripts' 디렉토리에 있어야 합니다.
# Docker에서 실행하려면 Docker 이미지에 이 스크립트가 포함되어야 합니다.
STANDARDIZE_SCRIPT="scripts/standardize_aime_results.py"

if [ -f "${STANDARDIZE_SCRIPT}" ]; then
    python "${STANDARDIZE_SCRIPT}" \
        --model-id "${MODEL_NAME}" \
        --input-dir "${OUTPUT_DIR}" \
        --output-dir "${OUTPUT_DIR}/standardized"

    if [ $? -eq 0 ]; then
        echo "✅ Standardization completed successfully."
    else
        echo "⚠️  Warning: Standardization failed." >&2
    fi
else
    echo "⚠️  Warning: Standardization script not found at ${STANDARDIZE_SCRIPT}" >&2
fi
echo ""
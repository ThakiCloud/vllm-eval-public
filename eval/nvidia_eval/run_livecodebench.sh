#! /bin/bash

MODEL_NAME=$1
OUTPUT_FOLDER_NAME=$2
GPUS=$3
OUT_SEQ_LEN=$4

if [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-7B" ]; then
    seed_list=(999 1000 1001 1002 1003 1004 1005 1006)
    MODEL_TYPE="r1"
elif [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-14B" ]; then
    seed_list=(999 1000 1001 1002 1003 1004 1005 1006)
    MODEL_TYPE="r1"
elif [ "$MODEL_NAME" == "nvidia/AceReason-Nemotron-1.1-7B" ]; then
    seed_list=(111 222 333 444 555 666 777 888)
    MODEL_TYPE="qwen"  
elif [ "$MODEL_NAME" == "qwen3-8b" ]; then
    seed_list=(111)
    MODEL_TYPE="qwen"
fi

python download_livecodebench.py

# 추론 실행
for seed in ${seed_list[@]}; do
    bash generate_livecodebench.sh ${MODEL_NAME} ${seed} ${OUTPUT_FOLDER_NAME} ${MODEL_TYPE} ${GPUS} ${OUT_SEQ_LEN}
done

echo "🔍 Starting LiveCodeBench evaluation..."

# 평가 실행 및 JSON 결과 생성
if [ -d "${OUTPUT_FOLDER_NAME}" ]; then
    echo "📊 Evaluating results in ${OUTPUT_FOLDER_NAME}..."
    python evaluate_livecodebench.py -q data/livecodebench_problems.jsonl -g ${OUTPUT_FOLDER_NAME}
    
    # 결과 파일을 출력 폴더로 이동
    if [ -f "livecodebench_evaluation_results.json" ]; then
        mv livecodebench_evaluation_results.json ${OUTPUT_FOLDER_NAME}/
        echo "✅ Evaluation completed! Results saved to ${OUTPUT_FOLDER_NAME}/livecodebench_evaluation_results.json"
    else
        echo "⚠️  Warning: Evaluation results file not found"
    fi
else
    echo "❌ Error: Output folder ${OUTPUT_FOLDER_NAME} not found"
fi

echo "🎉 LiveCodeBench pipeline completed!"

# 결과 표준화
echo ""
echo "📊 Standardizing LiveCodeBench results..."
STANDARDIZE_SCRIPT="scripts/standardize_livecodebench_results.py"
INPUT_JSON="${OUTPUT_FOLDER_NAME}/livecodebench_evaluation_results.json"
OUTPUT_JSON="${OUTPUT_FOLDER_NAME}/standardized/standardized_livecodebench_evaluation_results.json"

if [ -f "${STANDARDIZE_SCRIPT}" ]; then
    if [ -f "${INPUT_JSON}" ]; then
        python "${STANDARDIZE_SCRIPT}" \
            --model-id "${MODEL_NAME}" \
            --input-file "${INPUT_JSON}" \
            --output-file "${OUTPUT_JSON}"

        if [ $? -eq 0 ]; then
            echo "✅ Standardization completed successfully."
        else
            echo "⚠️  Warning: Standardization failed." >&2
        fi
    else
        echo "⚠️  Warning: Input JSON file not found at ${INPUT_JSON}" >&2
    fi
else
    echo "⚠️  Warning: Standardization script not found at ${STANDARDIZE_SCRIPT}" >&2
fi
echo ""

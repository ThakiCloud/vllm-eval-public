#!/bin/bash

DIR=`pwd`

CHECKPOINT_DIR=$1
TOKENIZER_DIR=$1
seed=$2
DATA="data/livecodebench_problems.jsonl"
OUTPUT_DIR=$3
MODEL_TYPE=$4

#######################################
BSZ=132
TOTAL=1
GPUS=1
OUT_SEQ_LEN=14000
top_p=0.95
temperature=0.6
#######################################

chunk=$(( (TOTAL + GPUS - 1) / GPUS ))

for (( gpu=0; gpu<GPUS; gpu++ )); do
  start=$(( gpu * chunk ))
  end=$(( start + chunk ))
  (( end > TOTAL )) && end=$TOTAL
  (( start >= TOTAL )) && break

  echo "GPU $gpu: processing [$start, $end)..."

  python inference.py \
    --load "${CHECKPOINT_DIR}" \
    --tokenizer-model "${TOKENIZER_DIR}" \
    --max-output-len "${OUT_SEQ_LEN}" \
    --batch-size "${BSZ}" \
    --temperature "${temperature}" \
    --topp "${top_p}" \
    --tensor-parallel-size 1 \
    --seed "${seed}" \
    --bf16 \
    --start-idx "${start}" \
    --end-idx "${end}" \
    --model-type "${MODEL_TYPE}" \
    --output-folder "${DIR}/${OUTPUT_DIR}" \
    --datapath "${DATA}" \
    --device-id "${gpu}" &
done

wait
echo "All GPUs finished."


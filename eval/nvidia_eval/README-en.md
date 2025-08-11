# NVIDIA Eval Benchmark Guide

This is an evaluation system that performs the **LiveCodeBench** and **AIME** benchmarks using datasets and evaluation methods provided by NVIDIA.

## 📋 Overview

This module supports the following two main benchmarks:
- **LiveCodeBench**: A benchmark based on the latest coding problems (Avg@8 evaluation)
- **AIME**: A benchmark based on the American Invitational Mathematics Examination problems (Avg@64 evaluation)

## 🔧 Environment Setup

### Dependencies
```bash
# Install core dependencies
pip install vllm==0.7.3 torch==2.5.1 transformers==4.48.2

# Install additional dependencies
pip install numpy tqdm sympy pandas antlr4-python3-runtime
```

### Supported Models
The following models are currently pre-configured:
- `nvidia/AceReason-Nemotron-7B`
- `nvidia/AceReason-Nemotron-14B` 
- `nvidia/AceReason-Nemotron-1.1-7B`
- `qwen3-8b` (for testing)

## 📁 File Structure

```
eval/nvidia_eval/
├── data/                           # Evaluation datasets
│   ├── aime24.jsonl               # AIME 2024 problems
│   ├── aime25.jsonl               # AIME 2025 problems
│   └── livecodebench_split.json   # LiveCodeBench problems
├── tools/                          # Evaluation tools
│   ├── grader.py                  # Math answer grader
│   ├── code_verifier.py           # Code verifier
│   └── convert_ckpt_to_safetensors.py
├── run_livecodebench.sh           # LiveCodeBench execution script
├── run_aime.sh                    # AIME execution script
├── inference.py                   # Inference engine
├── evaluate_*.py                  # Evaluation scripts
└── README.md                      # This document
```

## 🚀 Usage

### 1. One-Click Evaluation (Recommended)

**LiveCodeBench Evaluation**
```bash
bash run_livecodebench.sh <MODEL_PATH> <OUTPUT_PATH> <GPUS> <OUT_SEQ_LEN>

# Example
bash run_livecodebench.sh qwen3-8b cache/qwen3-8b 1 14444
```

**AIME Evaluation**
```bash  
bash run_aime.sh <MODEL_PATH> <OUTPUT_PATH> <GPUS> <OUT_SEQ_LEN>

# Example
bash run_aime.sh qwen3-8b cache/qwen3-8b 1 14444
```

### 2. Running Individual Components

**Download Dataset**
```bash
# Automatically download the LiveCodeBench dataset
python download_livecodebench.py
```

**Run Inference with Individual Seeds**
```bash
# Run a single seed for LiveCodeBench
bash generate_livecodebench.sh <MODEL_PATH> <SEED> <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>

# Run a single seed for AIME  
bash generate_aime.sh <MODEL_PATH> <SEED> aime24 <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>
bash generate_aime.sh <MODEL_PATH> <SEED> aime25 <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>
```

**Run Evaluation**
```bash
# AIME evaluation
python evaluate_aime.py --modelfolder <OUTPUT_PATH> --test_data data/aime24.jsonl

# LiveCodeBench evaluation
python evaluate_livecodebench.py -q data/livecodebench_problems.jsonl -g <OUTPUT_PATH>
```

## 📊 Output Results

After the evaluation is complete, the following files will be generated:

### LiveCodeBench Results
- `<OUTPUT_PATH>/livecodebench_evaluation_results.json`: Original evaluation results
- `<OUTPUT_PATH>/standardized/standardized_livecodebench_evaluation_results.json`: Standardized results

### AIME Results  
- `<OUTPUT_PATH>/aime24_evaluation_results.json`: AIME 2024 evaluation results
- `<OUTPUT_PATH>/aime25_evaluation_results.json`: AIME 2025 evaluation results
- `<OUTPUT_PATH>/standardized/`: Standardized results directory

## 🛠️ Advanced Usage

### API Server Mode
Evaluation using `inference.py` linked with an API server is also possible:
```bash
python inference.py \
    --api-base http://localhost:8000/v1 \
    --load <MODEL_NAME> \
    --datapath data/aime24.jsonl \
    --model-type qwen \
    --output-folder <OUTPUT_PATH>
```

### Dataset Customization
To use only a part of the LiveCodeBench dataset:
```python
# Modify download_livecodebench.py
# Before modification
test_data = dataset['test']

# After modification (use only 1 sample)
test_data = dataset['test'].select(range(1))
```

## 🔍 Evaluation Tools

### Grader (Math Grader)
`tools/grader.py` accurately grades the mathematical answers for AIME problems:
- Numerical equivalence check
- Symbolic equivalence check (using SymPy)
- LaTeX expression parsing support

### Code Verifier
`tools/code_verifier.py` verifies the solutions for LiveCodeBench coding problems:
- Syntax error check
- Execution time limit
- Test case execution

## 🐛 Troubleshooting

### Common Issues

**1. Dependency Errors**
```bash
# For ANTLR-related errors
pip install antlr4-python3-runtime

# For SymPy-related errors  
pip install sympy --upgrade
```

**2. Insufficient GPU Memory**
- Try reducing the `OUT_SEQ_LEN` parameter
- Increase the `GPUS` parameter for parallel processing

**3. API Connection Errors**
- Check if the VLLM server is running correctly
- Check if the `--api-base` URL is correct

**4. Missing Evaluation Result Files**
- Check if the inference has completed fully
- Check the output directory permissions

### Checking Logs
Each script outputs detailed progress, so check the logs for debugging when issues arise.

## 📈 Performance Optimization

- **Parallel Processing**: Adjust the `GPUS` parameter when using multiple GPUs
- **Batch Size**: Adjust the inference speed with the `--batch-size` parameter
- **Sequence Length**: Set `OUT_SEQ_LEN` according to the problem complexity

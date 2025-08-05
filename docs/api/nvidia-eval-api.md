# NVIDIA Eval API

## `nvidia_eval`

### livecodebench

1. Download `livecodebench` dataset:
    
    ```bash
    python download_livecodebench.py
    ```
    
2. Run inference code:
    
    ```bash
    python inference.py \         
        --api-base http://localhost:8000/v1 \
        --datapath data/livecodebench_problems.jsonl \
        --model-type opt125m \
        --output-folder "./results_livecodebench"  
    ```
    
3. Run evaluation code:
    
    ```bash
    python evaluate_livecodebench.py \
     --question-path data/livecodebench_problems.jsonl \
     --generation-path results_livecodebench/
    ```
    

### aime24 and aime25 benchmarks

Benchmark data is provided in data folder. Each file has about 30 and 15 questions respectively. 

**aime24** dataset:

1. Run inference code:
    
    ```bash
    python inference.py \         
        --api-base http://localhost:8000/v1 \
        --datapath data/aime24.jsonl \
        --model-type opt125m \
        --output-folder "./results_aime24"  
    ```
    
2. Run evaluation code:
    
    ```bash
    python evaluate_aime.py \
    	--question-path data/aime24.jsonl \
    	--generation-path results_aime24                       
    
    ```
    

**aime25** dataset:

1. Run inference code:
    
    ```bash
    python inference.py \         
        --api-base http://localhost:8000/v1 \
        --datapath data/aime25.jsonl \
        --model-type opt125m \
        --output-folder "./results_aime25"  
    ```
    
2. Run evaluation code:
    
    ```bash
    python evaluate_aime.py \
    	--question-path data/aime25.jsonl \
    	--generation-path results_aime25
    ```


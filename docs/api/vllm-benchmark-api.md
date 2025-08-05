# VLLM Benchmark API

## `vllm benchmark`

### Docker Run

1. Build Docker Image:
    
    ```bash
    docker build -f docker/vllm-benchmark.Dockerfile -t vllm-benchmark:latest .
    ```
    

2. Run a container from a created docker image:
    
    ```bash
    docker run --rm \
      --network host \
      -e VLLM_ENDPOINT="http://localhost:8080" \
      -e MODEL_NAME="Qwen/Qwen2-0.5B" \
      -e TOKENIZER="gpt2" \
      vllm-benchmark:latest
    ```
    
    *- variable is `VLLM_ENDPOINT` and provide only base url as given above. 
    

- Benchmark results
    
    ```bash
    Starting initial single prompt test run...
    Initial test run completed. Starting main benchmark run...
    Traffic request rate: inf RPS.
    Burstiness factor: 1.0 (Poisson process)
    Maximum request concurrency: 1
    100%|██████████| 1/1 [00:15<00:00, 15.13s/it]
    ============ Serving Benchmark Result ============
    Successful requests:                     1         
    Maximum request concurrency:             1         
    Benchmark duration (s):                  15.13     
    Total input tokens:                      1024      
    Total generated tokens:                  1024      
    Request throughput (req/s):              0.07      
    Output token throughput (tok/s):         67.69     
    Total Token throughput (tok/s):          135.37    
    ---------------Time to First Token----------------
    Mean TTFT (ms):                          47.19     
    Median TTFT (ms):                        47.19     
    P25 TTFT (ms):                           47.19     
    P50 TTFT (ms):                           47.19     
    P75 TTFT (ms):                           47.19     
    P90 TTFT (ms):                           47.19     
    P95 TTFT (ms):                           47.19     
    P99 TTFT (ms):                           47.19     
    -----Time per Output Token (excl. 1st token)------
    Mean TPOT (ms):                          14.74     
    Median TPOT (ms):                        14.74     
    P25 TPOT (ms):                           14.74     
    P50 TPOT (ms):                           14.74     
    P75 TPOT (ms):                           14.74     
    P90 TPOT (ms):                           14.74     
    P95 TPOT (ms):                           14.74     
    P99 TPOT (ms):                           14.74     
    ---------------Inter-token Latency----------------
    Mean ITL (ms):                           14.73     
    Median ITL (ms):                         14.62     
    P25 ITL (ms):                            14.33     
    P50 ITL (ms):                            14.62     
    P75 ITL (ms):                            15.01     
    P90 ITL (ms):                            15.71     
    P95 ITL (ms):                            16.34     
    P99 ITL (ms):                            20.46     
    ----------------End-to-end Latency----------------
    Mean E2EL (ms):                          15126.62  
    Median E2EL (ms):                        15126.62  
    P25 E2EL (ms):                           15126.62  
    P50 E2EL (ms):                           15126.62  
    P75 E2EL (ms):                           15126.62  
    P90 E2EL (ms):                           15126.62  
    P95 E2EL (ms):                           15126.62  
    P99 E2EL (ms):                           15126.62  
    ==================================================
    ```

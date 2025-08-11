# VLLM Benchmark API

The VLLM Benchmark API provides comprehensive performance evaluation capabilities for VLLM-served language models using the official VLLM `benchmark_serving.py` tool. This sophisticated benchmarking system supports multi-scenario configuration, detailed statistical analysis, and result standardization for integration with the broader evaluation pipeline.

!!! info "Benchmark Overview"
    
    VLLM Benchmark provides:
    
    - **Multi-Scenario Testing**: JSON-based configuration for complex benchmark scenarios
    - **Performance Metrics**: TTFT, TPOT, ITL, E2EL with detailed percentile analysis
    - **Concurrency Testing**: Configurable concurrent request handling evaluation  
    - **Result Analysis**: Sophisticated statistical analysis and result standardization
    - **Integration Support**: Standardized output for pipeline integration

## Prerequisites

!!! warning "Requirements"
    
    Before running VLLM benchmarks, ensure:
    
    - VLLM server is running and accessible
    - Docker is installed for containerized benchmarking
    - Sufficient system resources for load testing
    - Network connectivity between benchmark client and VLLM server

## Performance Metrics Explained

### Key Performance Indicators

!!! tip "Understanding Metrics"
    
    **Throughput Metrics:**

    - **Request Throughput**: Completed requests per second
    - **Output Token Throughput**: Generated tokens per second
    - **Total Token Throughput**: Combined input/output tokens per second
    
    **Latency Metrics:**

    - **TTFT (Time to First Token)**: Latency until first token generation
    - **TPOT (Time per Output Token)**: Average time between subsequent tokens
    - **ITL (Inter-token Latency)**: Real-time token generation intervals
    - **E2EL (End-to-End Latency)**: Complete request processing time

## Configuration System

VLLM benchmarks use a JSON-based configuration system located at `configs/vllm_benchmark.json`:

```json
{
  "name": "VLLM Performance Benchmark",
  "version": "2.0.0", 
  "description": "VLLM 서빙 성능 측정 벤치마크",
  "defaults": {
    "backend": "openai-chat",
    "endpoint_path": "/v1/chat/completions",
    "dataset_type": "random",
    "percentile_metrics": "ttft,tpot,itl,e2el",
    "metric_percentiles": "25,50,75,90,95,99"
  },
  "scenarios": [
    {
      "name": "basic_performance",
      "description": "기본 성능 측정",
      "max_concurrency": 1,
      "random_input_len": 1024,
      "random_output_len": 1024
    }
  ],
  "thresholds": {
    "ttft_p95_ms": 200,
    "tpot_mean_ms": 50,
    "throughput_min": 10,
    "success_rate": 0.95
  }
}
```

## Script-Based Execution

The primary benchmarking tool is `eval/vllm-benchmark/run_vllm_benchmark.sh`:

### Basic Usage

```bash
cd eval/vllm-benchmark
./run_vllm_benchmark.sh
```

### Environment Variables

- `MODEL_ENDPOINT`: VLLM server base URL (default: `http://localhost:8000`)
- `CONFIG_PATH`: Configuration file path (default: `configs/vllm_benchmark.json`)
- `OUTPUT_DIR`: Results output directory (default: `/app/results`)
- `REQUEST_RATE`: Request rate for load testing (default: `1.0`)
- `MODEL_NAME`: Model identifier
- `SERVED_MODEL_NAME`: Model name as configured in VLLM server
- `TOKENIZER`: Tokenizer specification (default: `gpt2`)

### Advanced Configuration

```bash
MODEL_ENDPOINT="http://localhost:8080" \
CONFIG_PATH="configs/custom_benchmark.json" \
OUTPUT_DIR="./benchmark_results" \
MODEL_NAME="Qwen/Qwen2-0.5B" \
./run_vllm_benchmark.sh
```

## Docker-Based Benchmarking

### Building the Benchmark Image

```bash
docker build -f docker/vllm-benchmark.Dockerfile -t vllm-benchmark:latest .
```

### Running Containerized Benchmarks

```bash
docker run --rm \
  --network host \
  -e MODEL_ENDPOINT="http://localhost:8080" \
  -e MODEL_NAME="Qwen/Qwen2-0.5B" \
  -e TOKENIZER="gpt2" \
  -e OUTPUT_DIR="/app/results" \
  -e PARSED_DIR="/app/parsed" \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/parsed:/app/parsed \
  vllm-benchmark:latest
```

!!! warning "Model Endpoint Validation"
    
    The script automatically validates the model endpoint and extracts the model ID from `/v1/models` before running benchmarks.

## Scenario Configuration

### Scenario Parameters

Each scenario in the configuration supports the following parameters:

**Core Parameters:**

- `name`: Unique scenario identifier
- `description`: Human-readable scenario description
- `max_concurrency`: Maximum concurrent requests
- `num_prompts`: Total number of prompts to process
- `random_input_len`: Input token length for random dataset
- `random_output_len`: Expected output token length

**Advanced Parameters:**

- `backend`: Backend type (`openai-chat`, `openai`, `tgi`)
- `endpoint_path`: API endpoint path (e.g., `/v1/chat/completions`)
- `dataset_type`: Dataset type (`random`, `synthetic`)
- `percentile_metrics`: Metrics to calculate percentiles for
- `metric_percentiles`: Percentile values to compute

### Multi-Scenario Example

```json
{
  "scenarios": [
    {
      "name": "light_load",
      "description": "Light load testing",
      "max_concurrency": 1,
      "num_prompts": 10,
      "random_input_len": 512,
      "random_output_len": 128
    },
    {
      "name": "heavy_load", 
      "description": "Heavy load testing",
      "max_concurrency": 8,
      "num_prompts": 100,
      "random_input_len": 2048,
      "random_output_len": 512
    }
  ]
}
```

## Sample Benchmark Output

### Performance Results Analysis

When you run the benchmark, you'll see comprehensive performance metrics:

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

### Result Interpretation

!!! success "Performance Analysis"
    
    **Key Insights from Results:**
    
    - **Throughput**: 67.69 tokens/sec output rate indicates model generation speed
    - **TTFT**: 47.19ms first token latency shows response initiation speed  
    - **TPOT**: 14.74ms per token indicates consistent generation performance
    - **Percentiles**: P90, P95, P99 values help identify tail latency behavior

## Load Testing Scenarios

### Single Client Performance

The basic benchmark runs single-client scenarios to establish baseline performance characteristics.

### Multi-Client Concurrency

!!! tip "Scaling Testing"
    
    For production readiness assessment:
    
    1. Start with single-client baseline
    2. Gradually increase concurrency levels
    3. Monitor performance degradation patterns
    4. Identify optimal concurrency for your hardware

### Stress Testing

```bash
# High-concurrency stress test
docker run --rm \
  --network host \
  -e MODEL_ENDPOINT="http://localhost:8080" \
  -e MODEL_NAME="Qwen/Qwen2-0.5B" \
  -e TOKENIZER="gpt2" \
  -e OUTPUT_DIR="/results" \
  -e PARSED_DIR="/parsed" \
  -e CONCURRENCY_LEVELS="50,100" \
  -e DURATION="600" \
  -v $(pwd)/results:/results \
  -v $(pwd)/parsed:/parsed \
  vllm-benchmark:latest
```

## Result Analysis and Processing

### Automated Analysis

The benchmark system includes sophisticated analysis capabilities via `eval/vllm-benchmark/analyze_vllm_results.py`:

```bash
# Analyze specific result file
python eval/vllm-benchmark/analyze_vllm_results.py /path/to/results.json

# Analyze entire results directory
python eval/vllm-benchmark/analyze_vllm_results.py /path/to/results/directory
```

### Output Directory Structure

```
benchmark_results/
├── vllm_benchmark_main_TIMESTAMP.log           # Main execution log
├── scenario_NAME_TIMESTAMP.log                 # Per-scenario logs
├── scenario_NAME_TIMESTAMP/                    # Raw VLLM results
│   └── benchmark_results.json
└── parsed/                                     # Standardized results
    └── SCENARIO_NAME_TIMESTAMP_standardized.json
```

### Result Standardization

Results are automatically standardized for pipeline integration:

```bash
python scripts/standardize_vllm_benchmark.py \
  results.json \
  --output_file standardized.json \
  --task_name "performance_test" \
  --config_path configs/vllm_benchmark.json
```

!!! success "Analysis Features"
    
    The analysis system provides:
    
    - **Statistical Summary**: Mean, median, percentiles for all metrics
    - **Performance Thresholds**: Automatic threshold validation
    - **Trend Analysis**: Multi-run performance comparison
    - **Export Formats**: JSON, CSV output for further processing

## Troubleshooting

### Common Issues

!!! warning "Troubleshooting Guide"
    
    **Connection Issues:**

    - Verify VLLM server is running and accessible
    - Check network connectivity with `curl` test
    - Ensure firewall rules allow benchmark traffic
    
    **Performance Issues:**

    - Monitor GPU/CPU utilization during benchmarks
    - Check for resource contention with other processes
    - Verify model loading completed successfully
    
    **Result Inconsistencies:**

    - Run multiple benchmark iterations for statistical stability
    - Account for system warm-up time in measurements
    - Monitor system load during benchmark execution

## Integration with VLLM Eval Pipeline

### Pipeline Integration

VLLM benchmark results integrate seamlessly with the evaluation aggregation system:

```bash
# Include VLLM benchmark results in aggregation
python scripts/aggregate_metrics.py \
  --include-vllm-benchmark \
  --results-dir eval/vllm-benchmark/parsed
```

### Performance Monitoring

!!! note "Monitoring Integration"
    
    Standardized results support:
    
    - ClickHouse analytics database storage
    - Grafana dashboard visualization
    - Prometheus metrics export
    - Automated regression detection

## Best Practices

### Benchmark Configuration

!!! tip "Optimization Tips"
    
    **For Accurate Results:**

    - Run multiple iterations for statistical stability
    - Allow adequate warm-up time before measurements
    - Monitor system resources during benchmarking
    - Use consistent hardware configurations
    
    **For Production Testing:**

    - Configure scenarios matching production workloads
    - Test various concurrency levels progressively
    - Establish baseline performance thresholds
    - Automate benchmark execution in CI/CD pipelines

### Troubleshooting

!!! warning "Common Issues"
    
    **Configuration Issues:**

    - Verify JSON configuration syntax
    - Ensure model endpoint accessibility
    - Check parameter compatibility with VLLM version
    
    **Performance Issues:**

    - Monitor GPU memory utilization
    - Check for CPU bottlenecks during high concurrency
    - Validate network connectivity stability
    
    **Result Issues:**
    
    - Ensure sufficient disk space for results
    - Verify write permissions to output directories
    - Check for incomplete benchmark runs in logs

## Next Steps

!!! success "Advanced Usage"
    
    After successful benchmarking:
    
    - Analyze results using the provided analysis tools
    - Configure performance thresholds for automated validation
    - Integrate with monitoring and alerting systems
    - Create custom scenarios for specific use cases
    - Set up automated performance regression testing
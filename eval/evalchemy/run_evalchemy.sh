#!/bin/bash

#
# Evalchemy Benchmark Runner Script
#
# This script runs lm-evaluation-harness benchmarks through the Evalchemy
# framework with support for various models, datasets, and configurations.
#
# Usage:
#   ./run_evalchemy.sh [OPTIONS]
#
# Environment Variables:
#   VLLM_MODEL_ENDPOINT  - API endpoint for VLLM model (required)
#   EVAL_CONFIG_PATH     - Path to evaluation config JSON (default: configs/eval_config.json)
#   OUTPUT_DIR          - Directory for results output (default: ./results)
#   RUN_ID              - Unique identifier for this evaluation run
#   GPU_DEVICE          - GPU device to use (default: 0)
#   BATCH_SIZE          - Batch size for evaluation (default: 8)
#   MAX_LENGTH          - Maximum sequence length (default: 2048)
#   TEMPERATURE         - Sampling temperature (default: 0.0)
#   TOP_P               - Top-p sampling parameter (default: 1.0)
#   LOG_LEVEL           - Logging level (default: INFO)
#

set -euo pipefail

# Script metadata
SCRIPT_NAME="run_evalchemy.sh"
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

#
# Configuration
#

# Default values
DEFAULT_CONFIG_PATH="${SCRIPT_DIR}/../../configs/evalchemy.json"
DEFAULT_OUTPUT_DIR="${SCRIPT_DIR}/results"
DEFAULT_GPU_DEVICE="0"
DEFAULT_BATCH_SIZE="8"
DEFAULT_MAX_LENGTH="2048"
DEFAULT_TEMPERATURE="0.0"
DEFAULT_TOP_P="1.0"
DEFAULT_LOG_LEVEL="INFO"
DEFAULT_TOKENIZER_BACKEND="none"

# Environment variables with defaults
VLLM_MODEL_ENDPOINT="${VLLM_MODEL_ENDPOINT:-}"
EVAL_CONFIG_PATH="${EVAL_CONFIG_PATH:-$DEFAULT_CONFIG_PATH}"
OUTPUT_DIR="${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_$$}"
GPU_DEVICE="${GPU_DEVICE:-$DEFAULT_GPU_DEVICE}"
BATCH_SIZE="${BATCH_SIZE:-$DEFAULT_BATCH_SIZE}"
MAX_LENGTH="${MAX_LENGTH:-$DEFAULT_MAX_LENGTH}"
TEMPERATURE="${TEMPERATURE:-$DEFAULT_TEMPERATURE}"
TOP_P="${TOP_P:-$DEFAULT_TOP_P}"
LOG_LEVEL="${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"
MODEL_NAME="${MODEL_NAME:-}"
TOKENIZER="${TOKENIZER:-$MODEL_NAME}"
TOKENIZER_BACKEND="${TOKENIZER_BACKEND:-$DEFAULT_TOKENIZER_BACKEND}"

# Derived paths
RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"
SUMMARY_FILE="${RESULTS_DIR}/evalchemy_summary_${RUN_ID}.json"

#
# Utility Functions
#

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${timestamp}: $message" >&2
            echo "[ERROR] ${timestamp}: $message" >> "$ERROR_LOG" 2>/dev/null || true
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${timestamp}: $message"
            echo "[WARN] ${timestamp}: $message" >> "$LOG_FILE" 2>/dev/null || true
            ;;
        INFO)
            echo -e "${GREEN}[INFO]${NC} ${timestamp}: $message"
            echo "[INFO] ${timestamp}: $message" >> "$LOG_FILE" 2>/dev/null || true
            ;;
        DEBUG)
            if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
                echo -e "${CYAN}[DEBUG]${NC} ${timestamp}: $message"
                echo "[DEBUG] ${timestamp}: $message" >> "$LOG_FILE" 2>/dev/null || true
            fi
            ;;
        *)
            echo -e "${BLUE}[${level}]${NC} ${timestamp}: $message"
            echo "[${level}] ${timestamp}: $message" >> "$LOG_FILE" 2>/dev/null || true
            ;;
    esac
}

show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Evalchemy Benchmark Runner - Executes lm-evaluation-harness benchmarks

OPTIONS:
    -e, --endpoint URL      VLLM model API endpoint (required)
    -c, --config PATH       Path to evaluation config JSON
    -o, --output DIR        Output directory for results
    -r, --run-id ID         Unique run identifier
    -g, --gpu DEVICE        GPU device number (default: 0)
    -b, --batch-size N      Batch size for evaluation (default: 8)
    -l, --max-length N      Maximum sequence length (default: 2048)
    -t, --temperature F     Sampling temperature (default: 0.0)
    -p, --top-p F           Top-p sampling parameter (default: 1.0)
    --model-name NAME       Model name (default: qwen3-8b)
    --tokenizer PATH        Tokenizer path (default: Qwen/Qwen3-8B)
    --tokenizer-backend TYPE Tokenizer backend (default: huggingface)
    --log-level LEVEL       Logging level (DEBUG|INFO|WARN|ERROR)
    --dry-run               Show commands without executing
    --list-benchmarks       List available benchmarks and exit
    --validate-config       Validate configuration and exit
    -h, --help              Show this help message
    -v, --version           Show version information

ENVIRONMENT VARIABLES:
    VLLM_MODEL_ENDPOINT     Model API endpoint
    EVAL_CONFIG_PATH        Configuration file path
    OUTPUT_DIR              Results output directory
    RUN_ID                  Evaluation run identifier
    GPU_DEVICE              GPU device number
    BATCH_SIZE              Evaluation batch size
    MAX_LENGTH              Maximum sequence length
    TEMPERATURE             Sampling temperature
    TOP_P                   Top-p sampling parameter
    MODEL_NAME              Model name
    TOKENIZER               Tokenizer path
    TOKENIZER_BACKEND       Tokenizer backend type
    LOG_LEVEL               Logging verbosity level

EXAMPLES:
    # Basic usage
    $SCRIPT_NAME --endpoint http://localhost:8000/v1/completions

    # Custom configuration and output
    $SCRIPT_NAME \\
        --endpoint http://model-api:8000/v1/completions \\
        --config /path/to/custom_config.json \\
        --output /data/results \\
        --run-id evaluation_20240101

    # High-performance settings with custom model
    $SCRIPT_NAME \\
        --endpoint http://localhost:8000/v1 \\
        --batch-size 16 \\
        --gpu 0,1,2,3 \\
        --max-length 4096 \\
        --model-name llama3-8b \\
        --tokenizer meta-llama/Llama-3-8B

    # Validation and dry-run
    $SCRIPT_NAME --validate-config --config custom.json
    $SCRIPT_NAME --dry-run --endpoint http://localhost:8000/v1/completions

EOF
}

show_version() {
    echo "$SCRIPT_NAME version $SCRIPT_VERSION"
    echo "lm-evaluation-harness integration for VLLM model evaluation"
}

cleanup() {
    local exit_code=$?
    log INFO "Cleaning up (exit code: $exit_code)"
    
    # Kill any background processes
    if [[ -n "${EVAL_PID:-}" ]]; then
        kill "$EVAL_PID" 2>/dev/null || true
    fi
    
    # Final log entry
    if [[ $exit_code -eq 0 ]]; then
        log INFO "Evalchemy evaluation completed successfully"
    else
        log ERROR "Evalchemy evaluation failed with exit code $exit_code"
    fi
    
    exit $exit_code
}

check_custom_tasks() {
    log INFO "Checking custom tasks availability..."
    
    local tasks_dir="$SCRIPT_DIR/tasks"
    
    if [[ ! -d "$tasks_dir" ]]; then
        log WARN "Custom tasks directory not found: $tasks_dir"
        return 1
    fi
    
    if [[ ! -f "$tasks_dir/__init__.py" ]]; then
        log WARN "Custom tasks __init__.py not found"
        return 1
    fi
    
    if [[ ! -f "$tasks_dir/custom_task.py" ]]; then
        log WARN "Custom task implementation not found"
        return 1
    fi
    
    log INFO "Custom tasks directory found: $tasks_dir"
    return 0
}

check_dependencies() {
    log INFO "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Python
    if ! command -v python &> /dev/null; then
        missing_deps+=("python")
    fi
    
    # Check pip packages
    local python_packages=(
        "lm_eval"
        "torch" 
        "transformers"
        "accelerate"
        "openai"
        "requests"
        "numpy"
        "datasets"
    )
    
    for package in "${python_packages[@]}"; do
        if ! python -c "import $package" &> /dev/null; then
            missing_deps+=("python-$package")
        fi
    done
    
    # Check system utilities
    local system_utils=(
        "jq"
        "curl"
    )
    
    for util in "${system_utils[@]}"; do
        if ! command -v "$util" &> /dev/null; then
            missing_deps+=("$util")
        fi
    done
    
    # Check nvidia-smi only if GPU_DEVICE is not cpu
    if [[ "$GPU_DEVICE" != "cpu" ]]; then
        if ! command -v nvidia-smi &> /dev/null; then
            log WARN "nvidia-smi not found but GPU_DEVICE=$GPU_DEVICE, setting to cpu mode"
            GPU_DEVICE="cpu"
        fi
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log ERROR "Missing dependencies: ${missing_deps[*]}"
        log ERROR "Please install missing dependencies before running"
        return 1
    fi
    
    log INFO "All dependencies satisfied"
    return 0
}

validate_config() {
    local config_file="$1"
    
    log INFO "Validating configuration file: $config_file"
    
    if [[ ! -f "$config_file" ]]; then
        log ERROR "Configuration file not found: $config_file"
        return 1
    fi
    
    # Basic JSON validation
    if ! jq empty "$config_file" 2>/dev/null; then
        log ERROR "Invalid JSON in configuration file"
        return 1
    fi
    
    # Check required fields
    local required_fields=(
        ".benchmarks"
        ".model_configs"
    )
    
    for field in "${required_fields[@]}"; do
        if ! jq -e "$field" "$config_file" >/dev/null 2>&1; then
            log ERROR "Missing required field in config: $field"
            return 1
        fi
    done
    
    # Validate benchmarks
    local benchmark_count=$(jq '.benchmarks | length' "$config_file")
    if [[ "$benchmark_count" -eq 0 ]]; then
        log ERROR "No benchmarks defined in configuration"
        return 1
    fi
    
    log INFO "Configuration validation passed ($benchmark_count benchmarks configured)"
    return 0
}

check_gpu_availability() {
    log INFO "Checking GPU availability..."
    
    if ! command -v nvidia-smi &> /dev/null; then
        log WARN "nvidia-smi not found, assuming CPU-only mode"
        return 0
    fi
    
    # Check if GPU is available
    if ! nvidia-smi &> /dev/null; then
        log WARN "No NVIDIA GPUs detected"
        return 0
    fi
    
    # Check specific GPU device
    if [[ "$GPU_DEVICE" != "cpu" ]]; then
        local gpu_count=$(nvidia-smi -L | wc -l)
        local gpu_list=(${GPU_DEVICE//,/ })
        
        for gpu in "${gpu_list[@]}"; do
            if [[ "$gpu" -ge "$gpu_count" ]]; then
                log ERROR "GPU device $gpu not available (only $gpu_count GPUs found)"
                return 1
            fi
        done
        
        log INFO "GPU device(s) $GPU_DEVICE available"
        
        # Check GPU memory
        for gpu in "${gpu_list[@]}"; do
            local memory_info=$(nvidia-smi --id="$gpu" --query-gpu=memory.total,memory.used --format=csv,noheader,nounits)
            local total_memory=$(echo "$memory_info" | cut -d',' -f1 | tr -d ' ')
            local used_memory=$(echo "$memory_info" | cut -d',' -f2 | tr -d ' ')
            local free_memory=$((total_memory - used_memory))
            
            log INFO "GPU $gpu memory: ${free_memory}MB free / ${total_memory}MB total"
            
            if [[ "$free_memory" -lt 4000 ]]; then
                log WARN "GPU $gpu has limited free memory: ${free_memory}MB"
            fi
        done
    fi
    
    return 0
}

test_model_endpoint() {
    local endpoint="$1"
    
    log INFO "Testing model endpoint: $endpoint"
    
    # Test completion endpoint directly with simple request
    local test_payload='{"model":"test","prompt":"Hello","max_tokens":1,"temperature":0}'
    local response
    
    if response=$(curl -s --connect-timeout 10 --max-time 30 \
                       -H "Content-Type: application/json" \
                       -d "$test_payload" \
                       "$endpoint" 2>&1); then
        log INFO "Model endpoint test successful"
        return 0
    else
        log WARN "Model endpoint test returned: $response"
        log INFO "Endpoint may still work during actual evaluation"
        return 0
    fi
}

list_benchmarks() {
    local config_file="$1"
    
    log INFO "Available benchmarks in $config_file:"
    
    if [[ ! -f "$config_file" ]]; then
        log ERROR "Configuration file not found"
        return 1
    fi
    
    # Parse and display benchmarks
    local benchmarks
    if benchmarks=$(jq -r '.benchmarks | to_entries[] | "\(.key): \(.value.enabled // true)"' "$config_file" 2>/dev/null); then
        echo ""
        echo -e "${BLUE}Benchmark Configuration:${NC}"
        echo "$benchmarks" | while read -r line; do
            local name=$(echo "$line" | cut -d':' -f1)
            local enabled=$(echo "$line" | cut -d':' -f2 | tr -d ' ')
            
            if [[ "$enabled" == "true" ]]; then
                echo -e "  ${GREEN}✓${NC} $name (enabled)"
            else
                echo -e "  ${RED}✗${NC} $name (disabled)"
            fi
        done
        echo ""
    else
        log ERROR "Failed to parse benchmarks from configuration"
        return 1
    fi
    
    return 0
}

prepare_environment() {
    log INFO "Preparing evaluation environment..."
    
    # Create output directories
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set CUDA device
    if [[ "$GPU_DEVICE" != "cpu" ]]; then
        export CUDA_VISIBLE_DEVICES="$GPU_DEVICE"
        log INFO "Set CUDA_VISIBLE_DEVICES=$GPU_DEVICE"
    fi
    
    # Set PyTorch settings for better performance
    export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128"
    export TOKENIZERS_PARALLELISM="false"
    
    # Set dummy OpenAI API key for VLLM compatibility
    export OPENAI_API_KEY="dummy"
    
    log INFO "Environment prepared, results will be saved to: $RESULTS_DIR"
}

run_benchmark() {
    local benchmark_name="$1"
    local config_file="$2"
    local endpoint="$3"
    
    log INFO "Running benchmark: $benchmark_name"
    
    # Extract benchmark configuration
    local benchmark_config
    if ! benchmark_config=$(jq -r ".benchmarks.\"$benchmark_name\"" "$config_file" 2>/dev/null); then
        log ERROR "Benchmark $benchmark_name not found in configuration"
        return 1
    fi
    
    # Check if benchmark is enabled
    local enabled=$(echo "$benchmark_config" | jq -r '.enabled // true')
    if [[ "$enabled" != "true" ]]; then
        log INFO "Benchmark $benchmark_name is disabled, skipping"
        return 0
    fi
    
    # Prepare benchmark arguments
    local tasks_raw=$(echo "$benchmark_config" | jq -r '.tasks // empty')
    local num_fewshot=$(echo "$benchmark_config" | jq -r '.num_fewshot // 0')
    local limit=$(echo "$benchmark_config" | jq -r '.limit // empty')
    
    # Convert JSON array to comma-separated string or use benchmark name
    local tasks
    if [[ -z "$tasks_raw" || "$tasks_raw" == "null" ]]; then
        tasks="$benchmark_name"
    else
        # If tasks is a JSON array, convert to comma-separated string
        if [[ "$tasks_raw" =~ ^\[.* ]]; then
            tasks=$(echo "$tasks_raw" | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')
        else
            tasks="$tasks_raw"
        fi
    fi
    
    # Build command arguments
    local cmd_args=(
        "--model" "openai-completions"
        "--model_args" "base_url=$endpoint,model=$MODEL_NAME,max_tokens=$MAX_LENGTH,tokenizer=$TOKENIZER,tokenizer_backend=$TOKENIZER_BACKEND"
        "--tasks" "$tasks"
        "--num_fewshot" "$num_fewshot"
        "--batch_size" "1"
        "--output_path" "$RESULTS_DIR/${benchmark_name}"
        "--log_samples"
        "--show_config"
        "--include_path" "$SCRIPT_DIR/tasks"
    )
    
    # Add optional arguments
    if [[ -n "$limit" && "$limit" != "null" ]]; then
        cmd_args+=("--limit" "$limit")
    fi
    
    # Add generation kwargs
    local gen_kwargs=$(jq -r '.generation_kwargs // {} | to_entries | map("\(.key)=\(.value)") | join(",")' "$config_file")
    if [[ -n "$gen_kwargs" && "$gen_kwargs" != "" ]]; then
        cmd_args+=("--gen_kwargs" "$gen_kwargs")
    fi
    
    # Run evaluation
    local benchmark_start_time=$(date +%s)
    local benchmark_log="$RESULTS_DIR/${benchmark_name}_benchmark.log"
    
    log INFO "Executing: lm_eval ${cmd_args[*]}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log INFO "[DRY RUN] Would run: lm_eval ${cmd_args[*]}"
        return 0
    fi
    
    # Execute benchmark
    if OPENAI_API_KEY=dummy python -m lm_eval "${cmd_args[@]}" \
        > "$benchmark_log" 2>&1; then
        
        local benchmark_end_time=$(date +%s)
        local benchmark_duration=$((benchmark_end_time - benchmark_start_time))
        
        log INFO "Benchmark $benchmark_name completed in ${benchmark_duration}s"
        
        # Parse results
        if [[ -f "$RESULTS_DIR/${benchmark_name}_results.json" ]]; then
            local accuracy=$(jq -r '.results | to_entries[0].value.acc // .results | to_entries[0].value.acc_norm // "N/A"' \
                           "$RESULTS_DIR/${benchmark_name}_results.json" 2>/dev/null || echo "N/A")
            log INFO "Benchmark $benchmark_name accuracy: $accuracy"
        fi
        
        return 0
    else
        log ERROR "Benchmark $benchmark_name failed"
        log ERROR "Check benchmark log: $benchmark_log"
        return 1
    fi
}

aggregate_results() {
    log INFO "Aggregating evaluation results..."
    
    local summary_data="{}"
    summary_data=$(echo "$summary_data" | jq ". + {\"run_id\": \"$RUN_ID\"}")
    summary_data=$(echo "$summary_data" | jq ". + {\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}")
    summary_data=$(echo "$summary_data" | jq ". + {\"model_endpoint\": \"$VLLM_MODEL_ENDPOINT\"}")
    summary_data=$(echo "$summary_data" | jq ". + {\"config_path\": \"$EVAL_CONFIG_PATH\"}")
    
    local results_data="{}"
    local total_benchmarks=0
    local successful_benchmarks=0
    
    # Process each result file
    for result_file in "$RESULTS_DIR"/*results*.json; do
        if [[ -f "$result_file" ]]; then
            local benchmark_name=$(basename "$result_file" "*results*.json")
            total_benchmarks=$((total_benchmarks + 1))
            
            # Extract key metrics
            if jq empty "$result_file" 2>/dev/null; then
                successful_benchmarks=$((successful_benchmarks + 1))
                
                # Extract all metrics for this benchmark
                local benchmark_results
                if benchmark_results=$(jq '.results' "$result_file" 2>/dev/null); then
                    results_data=$(echo "$results_data" | jq ". + {\"$benchmark_name\": $benchmark_results}")
                fi
            else
                log WARN "Invalid JSON in result file: $result_file"
            fi
        fi
    done
    
    # Add summary statistics
    summary_data=$(echo "$summary_data" | jq ". + {\"total_benchmarks\": $total_benchmarks}")
    summary_data=$(echo "$summary_data" | jq ". + {\"successful_benchmarks\": $successful_benchmarks}")
    summary_data=$(echo "$summary_data" | jq ". + {\"results\": $results_data}")
    
    # Add system information
    local system_info="{}"
    system_info=$(echo "$system_info" | jq ". + {\"hostname\": \"$(hostname)\"}")
    system_info=$(echo "$system_info" | jq ". + {\"gpu_device\": \"$GPU_DEVICE\"}")
    system_info=$(echo "$system_info" | jq ". + {\"batch_size\": $BATCH_SIZE}")
    system_info=$(echo "$system_info" | jq ". + {\"max_length\": $MAX_LENGTH}")
    
    summary_data=$(echo "$summary_data" | jq ". + {\"system_info\": $system_info}")
    
    # Save summary
    echo "$summary_data" | jq '.' > "$SUMMARY_FILE"
    
    log INFO "Results summary saved to: $SUMMARY_FILE"
    log INFO "Evaluation completed: $successful_benchmarks/$total_benchmarks benchmarks successful"
    
    return 0
}

standardize_results() {
    local results_dir="$1"
    local benchmark_name="$2"
    local benchmark_array="$3"
    local parsed_dir="${SCRIPT_DIR}/parsed"
    local standardize_script_path="${SCRIPT_DIR}/../../scripts/standardize_evalchemy.py"

    log INFO "Standardizing evaluation results..."

    if [[ ! -f "$standardize_script_path" ]]; then
        log ERROR "Standardization script not found at: $standardize_script_path"
        return 1
    fi

    mkdir -p "$parsed_dir"
    log INFO "Standardized results will be saved in: $parsed_dir"

    local result_files=($(find "$results_dir" -type f -name '*results*.json'))
    if [[ ${#result_files[@]} -eq 0 || ! -e "${result_files[0]}" ]]; then
        log WARN "No result files found to standardize in $results_dir"
        return 0
    fi

    log INFO "Found ${#result_files[@]} result files to standardize."

    for item in "${result_files[@]}"; do
        local input_to_standardize=""
        local base_stem=""

        if [[ -d "$item" ]]; then
            # Handle directory output (from --log_samples)
            # Find the result file, which may have a timestamp (e.g., results_20240101.json).
            result_file_path=$(find "$item" -name '*results*.json' -print -quit)

            if [[ -n "$result_file_path" && -f "$result_file_path" ]]; then
                input_to_standardize="$result_file_path"
                local dirname
                dirname=$(basename "$item")
                base_stem="${dirname%_results.json}"
            else
                log WARN "No result file matching '*results*.json' found in directory: $item"
                continue
            fi
        elif [[ -f "$item" ]]; then
            # Handle file output (original expectation)
            input_to_standardize="$item"
            local filename
            filename=$(basename "$item")
            base_stem="${filename%_results.json}"
        fi

        if [[ -n "$input_to_standardize" ]]; then
            local output_file="$parsed_dir/${RUN_ID}_${base_stem}.json"
            
            log INFO "Standardizing $input_to_standardize -> $output_file"

            if python "$standardize_script_path" "$input_to_standardize" --output_file "$output_file" --run_id "$RUN_ID" --benchmark_name "$benchmark_name" --tasks "$benchmark_array"; then
                log INFO "Successfully standardized $base_stem"
            else
                log ERROR "Failed to standardize $base_stem"
            fi
        fi
    done

    log INFO "Standardization process complete. Parsed files are in: $parsed_dir"
}

check_model_endpoint() {
    local base_url="$1"
    local endpoint=$(echo "$base_url" | sed -E 's|/v1/.*$||')/v1/models

    # JSON 응답 받아오기
    response=$(curl -s "$endpoint")

    # jq로 id 추출
    model_id=$(echo "$response" | jq -r '.data[0].id')

    if [[ -n "$model_id" && "$model_id" != "null" ]]; then
        log INFO "Model endpoint is valid: $model_id"
        echo "$model_id"
    else
        log ERROR "Model endpoint is not valid or model ID missing"
        return 1
    fi
    if [[ -z "$MODEL_NAME" ]]; then
        MODEL_NAME="$model_id"
    fi
    if [[ -z "$TOKENIZER" ]]; then
        TOKENIZER="$MODEL_NAME"
    fi
}

main() {
    # Set up signal handlers
    trap cleanup EXIT INT TERM
    
    # Store the original working directory
    local initial_pwd
    initial_pwd=$(pwd)
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--endpoint)
                VLLM_MODEL_ENDPOINT="$2"
                shift 2
                ;;
            -c|--config)
                EVAL_CONFIG_PATH="$2"
                # If path is relative, make it absolute from the original CWD
                if [[ ! "$EVAL_CONFIG_PATH" =~ ^/ && -n "$initial_pwd" ]]; then
                    EVAL_CONFIG_PATH="$initial_pwd/$EVAL_CONFIG_PATH"
                fi
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                # If path is relative, make it absolute from the original CWD
                if [[ ! "$OUTPUT_DIR" =~ ^/ && -n "$initial_pwd" ]]; then
                    OUTPUT_DIR="$initial_pwd/$OUTPUT_DIR"
                fi
                RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
                LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
                ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"
                SUMMARY_FILE="${RESULTS_DIR}/evalchemy_summary_${RUN_ID}.json"
                shift 2
                ;;
            -r|--run-id)
                RUN_ID="$2"
                RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
                LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
                ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"
                SUMMARY_FILE="${RESULTS_DIR}/evalchemy_summary_${RUN_ID}.json"
                shift 2
                ;;
            -g|--gpu)
                GPU_DEVICE="$2"
                shift 2
                ;;
            -b|--batch-size)
                BATCH_SIZE="$2"
                shift 2
                ;;
            -l|--max-length)
                MAX_LENGTH="$2"
                shift 2
                ;;
            -t|--temperature)
                TEMPERATURE="$2"
                shift 2
                ;;
            -p|--top-p)
                TOP_P="$2"
                shift 2
                ;;
            --model-name)
                MODEL_NAME="$2"
                shift 2
                ;;
            --tokenizer)
                TOKENIZER="$2"
                shift 2
                ;;
            --tokenizer-backend)
                TOKENIZER_BACKEND="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --list-benchmarks)
                LIST_BENCHMARKS="true"
                shift
                ;;
            --validate-config)
                VALIDATE_CONFIG="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--version)
                show_version
                exit 0
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Early exits for special modes
    if [[ "${LIST_BENCHMARKS:-false}" == "true" ]]; then
        list_benchmarks "$EVAL_CONFIG_PATH"
        exit $?
    fi
    
    if [[ "${VALIDATE_CONFIG:-false}" == "true" ]]; then
        validate_config "$EVAL_CONFIG_PATH"
        exit $?
    fi
    
    # Initialize logging directory
    mkdir -p "$RESULTS_DIR" 2>/dev/null || true
    
    # Script start
    log INFO "Starting Evalchemy evaluation (Run ID: $RUN_ID)"
    log INFO "Script: $SCRIPT_NAME v$SCRIPT_VERSION"
    log INFO "Configuration: $EVAL_CONFIG_PATH"
    log INFO "Output directory: $RESULTS_DIR"
    
    # Validation
    if [[ -z "$VLLM_MODEL_ENDPOINT" ]]; then
        log ERROR "VLLM model endpoint is required"
        log ERROR "Use --endpoint or set VLLM_MODEL_ENDPOINT environment variable"
        exit 1
    fi
    
    # Change to the parent directory of the script
    cd "$SCRIPT_DIR" || exit 1
    log INFO "Changed working directory to $(pwd)"

    # Pre-flight checks
    check_dependencies || exit 1
    validate_config "$EVAL_CONFIG_PATH" || exit 1
    check_gpu_availability || exit 1
    test_model_endpoint "$VLLM_MODEL_ENDPOINT" || exit 1
    check_model_endpoint "$VLLM_MODEL_ENDPOINT" || exit 1
    check_custom_tasks || log WARN "Custom tasks not available - some benchmarks may fail"
    
    # Environment setup
    prepare_environment
    
    # Get list of enabled benchmarks
    local enabled_benchmarks
    if ! enabled_benchmarks=$(jq -r '.benchmarks | to_entries[] | select(.value.enabled // true) | .key' "$EVAL_CONFIG_PATH" 2>/dev/null); then
        log ERROR "Failed to parse enabled benchmarks from configuration"
        exit 1
    fi
    
    local benchmark_array=()
    while IFS= read -r benchmark; do
        [[ -n "$benchmark" ]] && benchmark_array+=("$benchmark")
    done <<< "$enabled_benchmarks"
    
    if [[ ${#benchmark_array[@]} -eq 0 ]]; then
        log ERROR "No enabled benchmarks found in configuration"
        exit 1
    fi
    
    log INFO "Found ${#benchmark_array[@]} enabled benchmarks: ${benchmark_array[*]}"
    
    # Run benchmarks
    local failed_benchmarks=()
    local evaluation_start_time=$(date +%s)
    
    for benchmark in "${benchmark_array[@]}"; do
        if ! run_benchmark "$benchmark" "$EVAL_CONFIG_PATH" "$VLLM_MODEL_ENDPOINT"; then
            failed_benchmarks+=("$benchmark")
            log ERROR "Benchmark $benchmark failed"
        fi
    done
    
    local evaluation_end_time=$(date +%s)
    local total_duration=$((evaluation_end_time - evaluation_start_time))
    
    # Aggregate results
    aggregate_results
    
    # Final summary
    local successful_count=$((${#benchmark_array[@]} - ${#failed_benchmarks[@]}))
    
    log INFO "=== Evaluation Summary ==="
    log INFO "Run ID: $RUN_ID"
    log INFO "Total duration: ${total_duration}s"
    log INFO "Benchmarks attempted: ${#benchmark_array[@]}"
    log INFO "Benchmarks successful: $successful_count"
    log INFO "Benchmarks failed: ${#failed_benchmarks[@]}"
    
    if [[ ${#failed_benchmarks[@]} -gt 0 ]]; then
        log WARN "Failed benchmarks: ${failed_benchmarks[*]}"
    fi
    
    log INFO "Results directory: $RESULTS_DIR"
    log INFO "Summary file: $SUMMARY_FILE"
    
    # Standardize results
    standardize_results "$RESULTS_DIR" "Evalchemy" "${benchmark_array}"

    # Exit with appropriate code
    if [[ ${#failed_benchmarks[@]} -eq 0 ]]; then
        log INFO "All benchmarks completed successfully"
        exit 0
    else
        log ERROR "Some benchmarks failed"
        exit 1
    fi
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

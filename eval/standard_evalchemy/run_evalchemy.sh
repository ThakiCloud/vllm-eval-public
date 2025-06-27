#!/bin/bash

#
# Evalchemy Framework Runner Script
#
# This script runs evaluations using the Evalchemy framework with the
# `python -m eval.eval` command structure.
# It automatically reads enabled tasks from eval_config.json.
#
# Usage:
#   ./run_evalchemy.sh [OPTIONS]
#
# Environment Variables:
#   VLLM_MODEL_ENDPOINT  - API endpoint for VLLM model (required)
#   EVAL_CONFIG_PATH     - Path to evaluation config JSON (default: configs/eval_config.json)
#   OUTPUT_DIR          - Directory for results output (default: ./logs)
#   RUN_ID              - Unique identifier for this evaluation run
#   BATCH_SIZE          - Batch size for evaluation (default: 1)
#   MAX_TOKENS          - Maximum tokens (default: 14000)
#   NUM_FEWSHOT         - Number of few-shot examples (default: 1)
#   LIMIT               - Limit number of examples (default: 1)
#   LOG_LEVEL           - Logging level (default: INFO)
#

set -euo pipefail

# Script metadata
SCRIPT_NAME="run_evalchemy.sh"
SCRIPT_VERSION="3.1.0"
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
DEFAULT_CONFIG_PATH="${SCRIPT_DIR}/../../configs/standard_evalchemy.json"
DEFAULT_OUTPUT_DIR="${SCRIPT_DIR}/logs"
DEFAULT_BATCH_SIZE="1"
DEFAULT_MAX_TOKENS="14000"
DEFAULT_NUM_FEWSHOT="1"
DEFAULT_LIMIT="1"
DEFAULT_LOG_LEVEL="INFO"

# Environment variables with defaults
VLLM_MODEL_ENDPOINT="${VLLM_MODEL_ENDPOINT:-}"
EVAL_CONFIG_PATH="${EVAL_CONFIG_PATH:-$DEFAULT_CONFIG_PATH}"
OUTPUT_DIR="${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_$$}"
BATCH_SIZE="${BATCH_SIZE:-}"
MAX_TOKENS="${MAX_TOKENS:-$DEFAULT_MAX_TOKENS}"
NUM_FEWSHOT="${NUM_FEWSHOT:-}"
LIMIT="${LIMIT:-$DEFAULT_LIMIT}"
LOG_LEVEL="${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"

# Derived paths
RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"

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

get_enabled_tasks() {
    local config_file="$1"
    
    log DEBUG "Reading enabled tasks from config: $config_file" >&2
    
    # First check if any benchmark groups are enabled
    local enabled_groups=$(jq -r '.benchmark_groups | to_entries[] | select(.value.enabled == true) | .value.tasks[]' "$config_file" 2>/dev/null)
    
    if [[ -n "$enabled_groups" ]]; then
        log INFO "Found enabled tasks from benchmark groups: $enabled_groups" >&2
        # Return as space-separated list for individual processing
        echo "$enabled_groups" | tr '\n' ' '
        return 0
    fi
    
    # If no benchmark groups are enabled, check individual tasks
    local enabled_tasks=$(jq -r '.tasks | to_entries[] | select(.value.enabled == true) | .key' "$config_file" 2>/dev/null)
    
    if [[ -n "$enabled_tasks" ]]; then
        log INFO "Found enabled individual tasks: $enabled_tasks" >&2
        # Return as space-separated list for individual processing
        echo "$enabled_tasks" | tr '\n' ' '
        return 0
    fi
    
    # Fallback if nothing is enabled
    log WARN "No enabled benchmark groups or tasks found, using AIME24 as fallback" >&2
    echo "AIME24"
}

get_task_config() {
    local config_file="$1"
    local task_name="$2"
    local config_key="$3"
    local default_value="$4"
    
    local value=$(jq -r ".tasks.\"$task_name\".\"$config_key\" // \"$default_value\"" "$config_file" 2>/dev/null)
    if [[ "$value" == "null" ]]; then
        echo "$default_value"
    else
        echo "$value"
    fi
}

get_config_value() {
    local config_file="$1"
    local path="$2"
    local default_value="$3"
    
    local value=$(jq -r "$path // \"$default_value\"" "$config_file" 2>/dev/null)
    echo "$value"
}

load_config_values() {
    local config_file="$1"
    
    log INFO "Loading configuration values from: $config_file"
    
    # Override with config file values if not set via command line
    if [[ -z "$BATCH_SIZE" ]]; then
        local config_batch_size=$(get_config_value "$config_file" ".evaluation_settings.batch_size" "")
        if [[ -n "$config_batch_size" && "$config_batch_size" != "null" ]]; then
            BATCH_SIZE="$config_batch_size"
        fi
    fi
    
    if [[ "$MAX_TOKENS" == "$DEFAULT_MAX_TOKENS" ]]; then
        MAX_TOKENS=$(get_config_value "$config_file" ".evaluation_settings.max_tokens" "$DEFAULT_MAX_TOKENS")
    fi
    
    if [[ -z "$NUM_FEWSHOT" ]]; then
        local config_num_fewshot=$(get_config_value "$config_file" ".evaluation_settings.num_fewshot" "")
        if [[ -n "$config_num_fewshot" && "$config_num_fewshot" != "null" ]]; then
            NUM_FEWSHOT="$config_num_fewshot"
        fi
    fi
    
    if [[ "$LIMIT" == "$DEFAULT_LIMIT" ]]; then
        LIMIT=$(get_config_value "$config_file" ".evaluation_settings.limit" "$DEFAULT_LIMIT")
    fi
    
    if [[ "$LOG_LEVEL" == "$DEFAULT_LOG_LEVEL" ]]; then
        LOG_LEVEL=$(get_config_value "$config_file" ".evaluation_settings.verbosity" "$DEFAULT_LOG_LEVEL")
    fi
    
    log DEBUG "Configuration loaded - Batch size: ${BATCH_SIZE:-'not set'}, Max tokens: $MAX_TOKENS, Few-shot: ${NUM_FEWSHOT:-'not set'}, Limit: $LIMIT, Log level: $LOG_LEVEL"
}

show_usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Evalchemy Framework Runner - Executes evaluations using python -m eval.eval
Tasks are automatically determined from eval_config.json (enabled: true)

OPTIONS:
    -e, --endpoint URL      VLLM model API endpoint (required)
    -t, --tasks TASKS       Tasks to run (comma-separated, overrides config)
    -c, --config PATH       Path to evaluation config JSON
    -o, --output DIR        Output directory for results
    -r, --run-id ID         Unique run identifier
    -b, --batch-size N      Batch size for evaluation
    --max-tokens N          Maximum tokens
    --num-fewshot N         Number of few-shot examples
    --limit N               Limit number of examples
    --log-level LEVEL       Logging level (DEBUG|INFO|WARN|ERROR)
    --dry-run               Show commands without executing
    --debug                 Enable debug mode
    --list-tasks            List available tasks from config
    -h, --help              Show this help message
    -v, --version           Show version information

ENVIRONMENT VARIABLES:
    VLLM_MODEL_ENDPOINT     Model API endpoint
    EVAL_CONFIG_PATH        Configuration file path
    OUTPUT_DIR              Results output directory
    RUN_ID                  Evaluation run identifier
    BATCH_SIZE              Evaluation batch size
    MAX_TOKENS              Maximum tokens
    NUM_FEWSHOT             Few-shot examples count
    LIMIT                   Example limit
    LOG_LEVEL               Logging verbosity level

EXAMPLES:
    # Run all enabled tasks from config
    $SCRIPT_NAME --endpoint http://localhost:8000/v1

    # Override specific tasks
    $SCRIPT_NAME \\
        --endpoint http://localhost:8000/v1 \\
        --tasks AIME24,bbh \\
        --debug

    # List available tasks
    $SCRIPT_NAME --list-tasks

    # Using environment variables
    export VLLM_MODEL_ENDPOINT="http://localhost:8000/v1"
    $SCRIPT_NAME

EOF
}

list_tasks() {
    local config_file="$EVAL_CONFIG_PATH"
    
    if [[ ! -f "$config_file" ]]; then
        log ERROR "Configuration file not found: $config_file"
        return 1
    fi
    
    echo -e "${BLUE}Available Tasks:${NC}"
    echo "=================="
    
    # List individual tasks
    jq -r '.tasks | to_entries[] | "\(.key): \(.value.description) (enabled: \(.value.enabled))"' "$config_file" 2>/dev/null
    
    echo ""
    echo -e "${BLUE}Benchmark Groups:${NC}"
    echo "=================="
    
    # List benchmark groups
    jq -r '.benchmark_groups | to_entries[] | "\(.key): \(.value.description) (enabled: \(.value.enabled))\n  Tasks: \(.value.tasks | join(", "))"' "$config_file" 2>/dev/null
    
    echo ""
    echo -e "${GREEN}Currently Enabled Tasks:${NC}"
    local enabled_tasks=$(get_enabled_tasks "$config_file")
    # Convert space-separated to comma-separated for display
    echo "$enabled_tasks" | tr ' ' ','
}

show_version() {
    echo "$SCRIPT_NAME version $SCRIPT_VERSION"
    echo "Evalchemy framework integration for VLLM model evaluation"
    echo "Supports automatic task selection from configuration"
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

check_dependencies() {
    log INFO "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check if we can import eval.eval module
    if ! python3 -c "import eval.eval" &> /dev/null; then
        log ERROR "Cannot import eval.eval module - evalchemy may not be properly installed"
        return 1
    fi
    
    # Check system utilities
    local system_utils=("jq" "curl")
    for util in "${system_utils[@]}"; do
        if ! command -v "$util" &> /dev/null; then
            missing_deps+=("$util")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log ERROR "Missing dependencies: ${missing_deps[*]}"
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
    
    # Check for required sections
    local required_sections=(".tasks" ".model_config" ".evaluation_config")
    for section in "${required_sections[@]}"; do
        if ! jq -e "$section" "$config_file" >/dev/null 2>&1; then
            log WARN "Missing configuration section: $section"
        fi
    done
    
    log INFO "Configuration validation passed"
    return 0
}

test_model_endpoint() {
    local endpoint="$1"
    
    log INFO "Testing model endpoint: $endpoint"
    
    # Basic connectivity test
    local base_url=$(echo "$endpoint" | sed 's|/v1.*||')
    if ! curl -f -s --connect-timeout 10 --max-time 30 "$base_url/health" >/dev/null 2>&1; then
        log WARN "Health check failed, trying models endpoint..."
        
        # Try models endpoint
        if ! curl -f -s --connect-timeout 10 --max-time 30 "$endpoint/models" >/dev/null 2>&1; then
            log WARN "Cannot connect to model endpoint: $endpoint"
            log INFO "Endpoint may still work during actual evaluation"
            return 0
        fi
    fi
    
    log INFO "Model endpoint test successful"
    return 0
}

prepare_environment() {
    log INFO "Preparing evaluation environment..."
    
    # Create output directories
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Set environment variables for evalchemy
    export TOKENIZERS_PARALLELISM="false"
    
    log INFO "Environment prepared, results will be saved to: $RESULTS_DIR"
}

run_single_task_evaluation() {
    local task="$1"
    local endpoint="$2"
    
    log INFO "Running evalchemy evaluation for task: $task"
    
    # Read model configuration from config file - use simple defaults for now
    local model_name="qwen3-8b"
    local tokenizer="Qwen/Qwen3-8B"
    local tokenizer_backend="huggingface"
    local temperature="0.0"
    local top_p="1.0"
    
    log DEBUG "Model config: name=$model_name, tokenizer=$tokenizer, backend=$tokenizer_backend"
    
    # Get task-specific configuration
    local task_max_tokens=$(get_task_config "$EVAL_CONFIG_PATH" "$task" "max_tokens" "$MAX_TOKENS")
    local task_limit=$(get_task_config "$EVAL_CONFIG_PATH" "$task" "limit" "$LIMIT")
    local task_log_samples=$(get_task_config "$EVAL_CONFIG_PATH" "$task" "log_samples" "false")
    local task_timeout=$(get_task_config "$EVAL_CONFIG_PATH" "$task" "timeout" "3600")
    
    # Create task-specific output directory
    local task_results_dir="${RESULTS_DIR}/${task}"
    mkdir -p "$task_results_dir"
    
    # Create task-specific log file
    local task_log_file="${task_results_dir}/evalchemy_${task}_${RUN_ID}.log"
    
    log INFO "Task-specific config for $task: max_tokens=$task_max_tokens, limit=$task_limit, log_samples=$task_log_samples, timeout=$task_timeout"
    
    # Build command arguments
    local cmd_args=(
        "--model" "curator"
        "--tasks" "$task"
        "--model_args" "base_url=${endpoint},model=${model_name},tokenizer=${tokenizer},tokenizer_backend=${tokenizer_backend}"
        "--output_path" "$task_results_dir/"
        "--limit" "$task_limit"
        "--apply_chat_template" "True"
        "--max_tokens" "$task_max_tokens"
        "--verbosity" "$LOG_LEVEL"
    )
    
    # Add optional arguments only if they are set (global or task-specific)
    if [[ -n "$NUM_FEWSHOT" ]]; then
        log DEBUG "Adding num_fewshot argument: $NUM_FEWSHOT"
        cmd_args+=("--num_fewshot" "$NUM_FEWSHOT")
    else
        log DEBUG "NUM_FEWSHOT is empty, not adding num_fewshot argument"
    fi
    
    if [[ -n "$BATCH_SIZE" ]]; then
        log DEBUG "Adding batch_size argument: $BATCH_SIZE"
        cmd_args+=("--batch_size" "$BATCH_SIZE")
    else
        log DEBUG "BATCH_SIZE is empty, not adding batch_size argument"
    fi
    
    # Add debug flag if log level is DEBUG
    if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
        cmd_args+=("--debug")
    fi
    
    # Add log samples if enabled for this task
    if [[ "$task_log_samples" == "true" ]]; then
        cmd_args+=("--log_samples")
    fi
    
    # Run evaluation with timeout
    local evaluation_start_time=$(date +%s)
    
    log INFO "Executing for $task: python -m eval.eval ${cmd_args[*]}"
    
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
        log INFO "[DRY RUN] Would run for $task: python -m eval.eval ${cmd_args[*]}"
        return 0
    fi
    
    # Execute evaluation with timeout
    if timeout "$task_timeout" python -m eval.eval "${cmd_args[@]}" \
        > "$task_log_file" 2>&1; then
        
        local evaluation_end_time=$(date +%s)
        local evaluation_duration=$((evaluation_end_time - evaluation_start_time))
        
        log INFO "Task $task completed in ${evaluation_duration}s"
        
        # Append task log to main log
        echo "=== Task: $task ===" >> "$LOG_FILE"
        cat "$task_log_file" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log ERROR "Task $task timed out after ${task_timeout}s"
        else
            log ERROR "Task $task failed with exit code $exit_code"
        fi
        log ERROR "Check task log file: $task_log_file"
        
        # Append error log to main log
        echo "=== Task: $task (FAILED) ===" >> "$LOG_FILE"
        cat "$task_log_file" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        return 1
    fi
}

run_evalchemy_evaluation() {
    local tasks_string="$1"
    local endpoint="$2"
    
    # Convert tasks string to array
    local tasks_array
    read -ra tasks_array <<< "$tasks_string"
    
    log INFO "Running evalchemy evaluation with ${#tasks_array[@]} tasks: ${tasks_array[*]}"
    
    local failed_tasks=()
    local successful_tasks=()
    local total_start_time=$(date +%s)
    
    # Run each task individually
    for task in "${tasks_array[@]}"; do
        # Skip empty task names
        if [[ -z "$task" ]]; then
            continue
        fi
        
        log INFO "Starting evaluation for task: $task"
        
        if run_single_task_evaluation "$task" "$endpoint"; then
            successful_tasks+=("$task")
            log INFO "✅ Task $task completed successfully"
        else
            failed_tasks+=("$task")
            log ERROR "❌ Task $task failed"
        fi
        
        log INFO "Progress: $((${#successful_tasks[@]} + ${#failed_tasks[@]}))/${#tasks_array[@]} tasks processed"
    done
    
    local total_end_time=$(date +%s)
    local total_duration=$((total_end_time - total_start_time))
    
    # Summary
    log INFO "=== Evaluation Summary ==="
    log INFO "Total duration: ${total_duration}s"
    log INFO "Successful tasks (${#successful_tasks[@]}): ${successful_tasks[*]}"
    
    if [[ ${#failed_tasks[@]} -gt 0 ]]; then
        log ERROR "Failed tasks (${#failed_tasks[@]}): ${failed_tasks[*]}"
        return 1
    else
        log INFO "All tasks completed successfully!"
        return 0
    fi
}

standardize_results() {
    local results_dir="$1"
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
            result_file_path=$(find "$item" -name 'results*.json' -print -quit)

            if [[ -n "$result_file_path" && -f "$result_file_path" ]]; then
                input_to_standardize="$result_file_path"
                local dirname
                dirname=$(basename "$item")
                base_stem="${dirname%_results.json}"
            else
                log WARN "No result file matching 'results*.json' found in directory: $item"
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

            if python3 "$standardize_script_path" "$input_to_standardize" --output_file "$output_file" --run_id "$RUN_ID"; then
                log INFO "Successfully standardized $base_stem"
            else
                log ERROR "Failed to standardize $base_stem"
            fi
        fi
    done

    log INFO "Standardization process complete. Parsed files are in: $parsed_dir"
}

main() {
    # Set up signal handlers
    trap cleanup EXIT INT TERM
    
    # Default tasks (will be overridden by config)
    local tasks=""
    local override_tasks=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--endpoint)
                VLLM_MODEL_ENDPOINT="$2"
                shift 2
                ;;
            -t|--tasks)
                tasks="$2"
                override_tasks=true
                shift 2
                ;;
            -c|--config)
                EVAL_CONFIG_PATH="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
                LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
                ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"
                shift 2
                ;;
            -r|--run-id)
                RUN_ID="$2"
                RESULTS_DIR="${OUTPUT_DIR}/${RUN_ID}"
                LOG_FILE="${RESULTS_DIR}/evalchemy_${RUN_ID}.log"
                ERROR_LOG="${RESULTS_DIR}/evalchemy_errors_${RUN_ID}.log"
                shift 2
                ;;
            -b|--batch-size)
                BATCH_SIZE="$2"
                shift 2
                ;;
            --max-tokens)
                MAX_TOKENS="$2"
                shift 2
                ;;
            --num-fewshot)
                NUM_FEWSHOT="$2"
                shift 2
                ;;
            --limit)
                LIMIT="$2"
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
            --debug)
                LOG_LEVEL="DEBUG"
                shift
                ;;
            --list-tasks)
                list_tasks
                exit 0
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
    
    # Initialize logging directory
    mkdir -p "$RESULTS_DIR" 2>/dev/null || true
    
    # Script start
    log INFO "Starting Evalchemy evaluation (Run ID: $RUN_ID)"
    log INFO "Script: $SCRIPT_NAME v$SCRIPT_VERSION"
    log INFO "Configuration: $EVAL_CONFIG_PATH"
    log INFO "Output directory: $RESULTS_DIR"
    
    # Pre-flight checks
    check_dependencies || exit 1
    validate_config "$EVAL_CONFIG_PATH" || exit 1
    
    # Load configuration values
    load_config_values "$EVAL_CONFIG_PATH"
    
    # Determine tasks to run
    if [[ "$override_tasks" == "false" ]]; then
        tasks=$(get_enabled_tasks "$EVAL_CONFIG_PATH")
        log INFO "Auto-detected enabled tasks from config: $tasks"
    else
        log INFO "Using manually specified tasks: $tasks"
    fi
    
    if [[ -z "$tasks" ]]; then
        log ERROR "No tasks specified or enabled in configuration"
        exit 1
    fi
    
    # Validation
    if [[ -z "$VLLM_MODEL_ENDPOINT" ]]; then
        log ERROR "VLLM model endpoint is required"
        log ERROR "Use --endpoint or set VLLM_MODEL_ENDPOINT environment variable"
        exit 1
    fi
    
    # Skip endpoint test in dry-run mode
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
        test_model_endpoint "$VLLM_MODEL_ENDPOINT" || exit 1
    else
        log INFO "Skipping endpoint test in dry-run mode"
    fi
    
    # Environment setup
    prepare_environment
    
    # Run evaluation
    local evaluation_start_time=$(date +%s)
    
    if ! run_evalchemy_evaluation "$tasks" "$VLLM_MODEL_ENDPOINT"; then
        standardize_results "$RESULTS_DIR"
        
        log ERROR "Evaluation failed"
        exit 1
    fi
    
    standardize_results "$RESULTS_DIR"

    local evaluation_end_time=$(date +%s)
    local total_duration=$((evaluation_end_time - evaluation_start_time))
    
    # Final summary
    log INFO "=== Evaluation Summary ==="
    log INFO "Run ID: $RUN_ID"
    log INFO "Total duration: ${total_duration}s"
    log INFO "Tasks: $tasks"
    log INFO "Results directory: $RESULTS_DIR"
    
    log INFO "Evalchemy evaluation completed successfully"
    exit 0
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
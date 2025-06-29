import json
import argparse
import requests
import sys
import os
from pathlib import Path
from datetime import datetime

def send_to_endpoint(url: str, data: str, data_description: str, run_id: str, benchmark_name: str, timestamp: str, model_id: str, tokenizer_id: str, source: str):
    """
    지정된 URL로 데이터를 POST 요청으로 전송합니다.
    
    Parameters:
    - url (str): 전송할 엔드포인트 URL
    - data (str): 전송할 JSON 데이터 (stringified)
    - data_description (str): 로그/출력용 설명
    - run_id (str): 실행 식별자
    - benchmark_name (str): 벤치마크 이름
    - timestamp (str): 타임스탬프
    - model_id (str): 모델 이름
    - tokenizer_id (str): 토크나이저 이름
    - source (str): 모델 소스
    """
    try:
        # 최종 전송할 JSON payload 구성
        payload = {
            "run_id": run_id,
            "benchmark_name": benchmark_name,
            "data": json.loads(data),  # 문자열로 전달된 JSON을 실제 객체로 변환
            "timestamp": timestamp,
            "model_id": model_id,
            "tokenizer_id": tokenizer_id,
            "source": source
        }

        headers = {'Content-Type': 'application/json; charset=utf-8'}
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"✅ Successfully sent {data_description} to: {url}")

    except requests.RequestException as e:
        print(f"⚠️ Warning: Failed to send {data_description} to {url}. Error: {e}", file=sys.stderr)
    except json.JSONDecodeError as je:
        print(f"❌ Invalid JSON format in 'data' argument. Error: {je}", file=sys.stderr)

def load_config_metrics(config_path: str = None) -> list:
    """
    설정 파일에서 latency metrics를 로드합니다.
    """
    default_metrics = ["ttft", "tpot", "itl", "e2el"]
    
    if not config_path:
        # 기본 설정 파일 경로들 시도
        possible_paths = [
            "configs/vllm_benchmark.json",
            "../configs/vllm_benchmark.json", 
            "../../configs/vllm_benchmark.json"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if not config_path or not os.path.exists(config_path):
        print(f"⚠️ Warning: Config file not found, using default metrics: {default_metrics}")
        return default_metrics
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # percentile_metrics에서 메트릭 추출
        percentile_metrics = config.get("defaults", {}).get("percentile_metrics", "")
        if percentile_metrics:
            metrics = [metric.strip() for metric in percentile_metrics.split(",")]
            print(f"✅ Loaded metrics from config: {metrics}")
            return metrics
        else:
            print(f"⚠️ Warning: percentile_metrics not found in config, using default: {default_metrics}")
            return default_metrics
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Warning: Error reading config file {config_path}: {e}, using default metrics: {default_metrics}")
        return default_metrics

def standardize_vllm_json(input_path: Path, output_path: Path, task_name: str = None, config_path: str = None):
    """
    vLLM 벤치마크 결과 JSON 파일을 표준 형식으로 변환합니다.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_input_data = f.read()
            data = json.loads(raw_input_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading file {input_path}: {e}")
        return

    # --- Meta 데이터 추출 ---
    try:
        # YYYYMMDD-HHMMSS 형식의 날짜 파싱
        dt_obj = datetime.strptime(str(data["date"]), "%Y%m%d-%H%M%S")
        timestamp = dt_obj.isoformat() + "Z"
    except (ValueError, KeyError):
        # 파싱 실패 시 현재 시간 사용
        timestamp = datetime.now().isoformat() + "Z"

    meta = {
        "run_id": str(data.get("date")),
        "timestamp": timestamp,
        "benchmark_name": "vllm_benchmark",
        "tasks": task_name,
        "model": {
            "id": data.get("model_id"),
            "tokenizer_id": data.get("tokenizer_id"),
            "source": data.get("backend")
        },
        "config": {
            "num_prompts": data.get("num_prompts"),
            "request_rate": data.get("request_rate"),
            "burstiness": data.get("burstiness"),
            "max_concurrency": data.get("max_concurrency")
        }
    }

    # --- Results 데이터는 vLLM 벤치마크에 없음 ---
    results_data = {}

    # --- Performance 데이터 추출 ---
    latency_data = {}
    latency_metrics = load_config_metrics(config_path)
    for metric in latency_metrics:
        # mean, median, std, p25-p99 등 모든 통계 정보 추출
        stats = {}
        for key in ["mean", "median", "std", "p25", "p50", "p75", "p90", "p95", "p99"]:
            data_key = f"{key}_{metric}_ms"
            if data_key in data:
                stats[key] = data[data_key]
        if stats:
            latency_data[f"{metric}_ms"] = stats

    performance = {
        "summary": {
            "duration_sec": data.get("duration"),
            "completed_requests": data.get("completed"),
            "total_input_tokens": data.get("total_input_tokens"),
            "total_output_tokens": data.get("total_output_tokens")
        },
        "throughput": {
            "requests_per_second": data.get("request_throughput"),
            "output_tokens_per_second": data.get("output_throughput"),
            "total_tokens_per_second": data.get("total_token_throughput")
        },
        "latency": latency_data
    }

    # --- 표준 형식으로 조합 ---
    standardized_data = {
        "meta": meta,
        "results": results_data,
        "performance": performance
    }

    # --- 파일로 저장 ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    standardized_data_json = json.dumps(standardized_data, indent=2, ensure_ascii=False)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(standardized_data_json)
    
    print(f"Standardized vLLM benchmark results saved to: {output_path}")

    url = os.environ.get("BACKEND_API", "http://localhost:8000")
    input_url = f"{url}/raw_input"
    send_to_endpoint(input_url, raw_input_data, "original input data", meta["run_id"], meta["benchmark_name"], meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])
    output_url = f"{url}/standardized_output"
    send_to_endpoint(output_url, standardized_data_json, "standardized output data", meta["run_id"], meta["benchmark_name"], meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardize vLLM benchmark JSON results.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON file from vLLM benchmark.")
    parser.add_argument("--output_file", type=str, help="Path to the output standardized JSON file. (Optional)")
    parser.add_argument("--task_name", type=str, help="Task name for the benchmark results. (Optional)")
    parser.add_argument("--config_path", type=str, help="Path to the vLLM benchmark config JSON file. (Optional)")
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}.json"
        
    standardize_vllm_json(input_path, output_path, task_name=args.task_name, config_path=args.config_path) 
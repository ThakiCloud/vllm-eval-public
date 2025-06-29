import json
import argparse
import sys
import requests
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

def parse_model_args(model_args_str: str) -> dict:
    """'key1=value1,key2=value2' 형식의 문자열을 파싱하여 딕셔너리로 반환합니다."""
    args_dict = {}
    if not model_args_str:
        return args_dict
    
    parts = model_args_str.split(',')
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            args_dict[key.strip()] = value.strip()
    return args_dict

def standardize_evalchemy_json(input_path: Path, output_path: Path, run_id: str = None, benchmark_name: str = None, tasks: str = None):
    """
    Evalchemy (lm-evaluation-harness) 벤치마크 결과 JSON 파일을 표준 형식으로 변환합니다.
    결과를 파일에 저장하고, 선택적으로 원본 및 변환된 데이터를 원격 URL로 전송합니다.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_input_data = f.read()
            data = json.loads(raw_input_data)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing file {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Meta 데이터 추출 ---
    benchmark_name = benchmark_name
    task_name = tasks
    model_args = parse_model_args(data.get("config", {}).get("model_args", ""))
    tokenizer_id = model_args.get("tokenizer", data.get("config", {}).get("model_name"))

    # run_id 우선순위: 1. 명시적 전달, 2. 경로에서 추론
    inferred_run_id = "unknown"
    if len(input_path.parts) > 2:
        # heuristic: '.../RUN_ID/benchmark_name_results.json' 또는
        # '.../RUN_ID/benchmark_name_results.json/results.json' 구조를 가정
        if "results" in str(input_path.parts[-1]):
             inferred_run_id = input_path.parts[-3]
        else:
             inferred_run_id = input_path.parts[-2]

    meta = {
        "run_id": run_id or inferred_run_id,
        "timestamp": datetime.fromtimestamp(data["date"]).isoformat() + "Z" if "date" in data else datetime.now().isoformat() + "Z",
        "benchmark_name": benchmark_name,
        "tasks": task_name,
        "model": {
            "id": data.get("model_name"),
            "tokenizer_id": tokenizer_id,
            "source": data.get("model_source") or data.get("config", {}).get("model")
        },
        "config": data.get("config", {})
    }

    # --- Results 데이터 추출 ---
    results_data = data.get("results", {})

    # --- Performance 데이터 추출 ---
    performance = {
        "summary": {
            "duration_sec": float(data["total_evaluation_time_seconds"]) if "total_evaluation_time_seconds" in data else None,
            "completed_requests": None,
            "total_input_tokens": None, # Evalchemy 결과에는 토큰 정보가 없음
            "total_output_tokens": None
        },
        "throughput": {
            "requests_per_second": None,
            "output_tokens_per_second": None,
            "total_tokens_per_second": None
        },
        "latency": {}
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
    
    print(f"Standardized Evalchemy results saved to: {output_path}")

    url = os.environ.get("BACKEND_API", "http://localhost:8000")
    input_url = f"{url}/raw_input"
    send_to_endpoint(input_url, raw_input_data, "original input data", run_id, benchmark_name, meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])  
    output_url = f"{url}/standardized_output"
    send_to_endpoint(output_url, standardized_data_json, "standardized output data", run_id, benchmark_name, meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardize Evalchemy (lm-evaluation-harness) JSON results.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON file from Evalchemy.")
    parser.add_argument("--output_file", type=str, help="Path to the output standardized JSON file. (Optional)")
    parser.add_argument("--run_id", type=str, help="Explicitly set the Run ID for the benchmark results. (Optional)")
    parser.add_argument("--benchmark_name", type=str, help="Explicitly set the Benchmark Name for the benchmark results. (Optional)")
    parser.add_argument("--tasks", type=str, help="Explicitly set the Benchmark Array for the benchmark results. (Optional)")
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}_standardized.json"

    standardize_evalchemy_json(input_path, output_path, run_id=args.run_id, benchmark_name=args.benchmark_name, tasks=args.tasks) 
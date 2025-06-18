import json
import argparse
from pathlib import Path
from datetime import datetime

def standardize_vllm_json(input_path: Path, output_path: Path):
    """
    vLLM 벤치마크 결과 JSON 파일을 표준 형식으로 변환합니다.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
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
        "benchmark_name": "vllm_performance_test",
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
    latency_metrics = ["ttft", "tpot", "itl", "e2el"]
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
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(standardized_data, f, indent=2, ensure_ascii=False)
    
    print(f"Standardized vLLM benchmark results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardize vLLM benchmark JSON results.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON file from vLLM benchmark.")
    parser.add_argument("--output_file", type=str, help="Path to the output standardized JSON file. (Optional)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}.json"
        
    standardize_vllm_json(input_path, output_path) 
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

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

def standardize_evalchemy_json(input_path: Path, output_path: Path, run_id: str = None):
    """
    Evalchemy (lm-evaluation-harness) 벤치마크 결과 JSON 파일을 표준 형식으로 변환합니다.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing file {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Meta 데이터 추출 ---
    benchmark_keys = list(data.get("results", {}).keys())
    benchmark_name = benchmark_keys[0] if benchmark_keys else "unknown_benchmark"
    
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
        "model": {
            "id": data.get("model_name"),
            "tokenizer_id": tokenizer_id,
            "source": data.get("model_source") or data.get("config", {}).get("model")
        },
        "config": {
            "num_fewshot": data.get("n-shot", {}).get(benchmark_name),
            "batch_size": data.get("config", {}).get("batch_size"),
            "limit": data.get("config", {}).get("limit"),
            "doc_to_text": data.get("configs", {}).get(benchmark_name, {}).get("doc_to_text"),
            "generation_kwargs": data.get("config", {}).get("gen_kwargs")
        }
    }

    # --- Results 데이터 추출 ---
    results_data = data.get("results", {}).get(benchmark_name, {})
    results_data.pop("alias", None) # 'alias' 키는 필요 없으므로 제거

    # --- Performance 데이터 추출 ---
    performance = {
        "summary": {
            "duration_sec": float(data["total_evaluation_time_seconds"]) if "total_evaluation_time_seconds" in data else None,
            "completed_requests": data.get("n-samples", {}).get(benchmark_name, {}).get("effective"),
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
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(standardized_data, f, indent=2, ensure_ascii=False)
    
    print(f"Standardized Evalchemy results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standardize Evalchemy (lm-evaluation-harness) JSON results.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON file from Evalchemy.")
    parser.add_argument("--output_file", type=str, help="Path to the output standardized JSON file. (Optional)")
    parser.add_argument("--run_id", type=str, help="Explicitly set the Run ID for the benchmark results. (Optional)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}_standardized.json"

    standardize_evalchemy_json(input_path, output_path, run_id=args.run_id) 
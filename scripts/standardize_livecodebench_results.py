import json
import uuid
import datetime
import os
import argparse
import sys
import requests
from pathlib import Path

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
            "benchmark_name": "Nvidia Eval",
            "tasks": "livecodebench",
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

def infer_run_id_from_path(file_path):
    """
    파일 경로에서 run_id를 추론합니다.
    """
    path_parts = Path(file_path).parts
    if len(path_parts) > 2:
        # 경로 구조에서 run_id 추론 (예: output/run_123/livecodebench_results.json)
        return path_parts[-2] if path_parts[-2] != "output" else str(uuid.uuid4())
    return str(uuid.uuid4())

def standardize_livecodebench_format(input_data, model_id, file_path, run_id=None):
    """
    LiveCodeBench 데이터를 표준 양식으로 변환합니다.
    """
    # run_id 결정: 명시적 전달 > 경로 추론 > UUID 생성
    final_run_id = run_id or infer_run_id_from_path(file_path)
    
    # 타임스탬프 처리: 입력 데이터에 있으면 사용, 없으면 현재 시각
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp = input_data.get("timestamp")
    if timestamp:
        # 이미 ISO 형식이라고 가정
        final_timestamp = timestamp if timestamp.endswith('Z') else timestamp + 'Z'
    else:
        final_timestamp = now_utc.isoformat().replace("+00:00", "Z")
    
    # 'overall' 섹션에서 주요 결과 추출
    overall_results = input_data.get("overall", {})
    
    # 모델 정보 추출
    model_info = input_data.get("model", {})
    if isinstance(model_info, str):
        model_info = {"id": model_info}
    
    # config 정보 추출 및 보존
    config = input_data.get("config", {})
    config.update({
        "total_questions": overall_results.get("total_questions"),
        "evaluation_version": input_data.get("version"),
        "dataset_source": input_data.get("dataset_source")
    })
    # None 값 제거
    config = {k: v for k, v in config.items() if v is not None}
    
    # 표준화된 데이터 구조 생성
    standardized_data = {
        "meta": {
            "run_id": final_run_id,
            "timestamp": final_timestamp,
            "benchmark_name": "Nvidia Eval",
            "tasks": "livecodebench",
            "model": {
                "id": model_info.get("id") or model_id,
                "tokenizer_id": model_info.get("tokenizer_id") or model_info.get("id") or model_id,
                "source": model_info.get("source") or "nvidia_eval"
            },
            "config": config
        },
        "results": {
            # 'overall' 섹션의 값들을 기본 결과로 추가
            "accuracy_overall_percent": overall_results.get("accuracy"),
            "total_questions": overall_results.get("total_questions"),
            "correct_answers": overall_results.get("correct_answers"),
            
            # 상세 분석 결과들을 그대로 추가
            "monthly_results": input_data.get("monthly_results", {}),
            "period_results": input_data.get("period_results", {}),
            "version_results": input_data.get("version_results", {})
        },
        "performance": {
            "summary": {
                "duration_sec": input_data.get("evaluation_time_seconds"),
                "completed_requests": overall_results.get("total_questions"),
                "total_input_tokens": input_data.get("total_input_tokens"),
                "total_output_tokens": input_data.get("total_output_tokens")
            },
            "throughput": {
                "requests_per_second": input_data.get("requests_per_second"),
                "output_tokens_per_second": input_data.get("output_tokens_per_second"),
                "total_tokens_per_second": input_data.get("total_tokens_per_second")
            },
            "latency": input_data.get("latency", {})
        }
    }
    
    # None 값들을 정리
    def clean_none_values(obj):
        if isinstance(obj, dict):
            return {k: clean_none_values(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [clean_none_values(item) for item in obj if item is not None]
        return obj
    
    return clean_none_values(standardized_data)

def convert_file(input_path, output_path, model_id, run_id=None):
    """
    단일 파일을 읽고 변환하여 저장합니다.
    """
    print(f"원본 파일 읽는 중: {input_path}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_input_data = f.read()
            input_json = json.loads(raw_input_data)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다 - {input_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패 - {input_path}: {e}", file=sys.stderr)
        return False

    print("LiveCodeBench 벤치마크 데이터 표준화 중...")
    standardized_json = standardize_livecodebench_format(input_json, model_id, input_path, run_id)

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    standardized_data_json = json.dumps(standardized_json, indent=2, ensure_ascii=False)
    print(f"표준화된 파일 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(standardized_json, f, indent=2, ensure_ascii=False)
    print(f"'{output_path}' 저장 완료.")

    meta = standardized_json["meta"]
    url = os.environ.get("BACKEND_API", "http://localhost:8000")
    input_url = f"{url}/raw_input"
    send_to_endpoint(input_url, raw_input_data, "original input data", meta["run_id"], meta["benchmark_name"], meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])  
    output_url = f"{url}/standardized_output"
    send_to_endpoint(output_url, standardized_data_json, "standardized output data", meta["run_id"], meta["benchmark_name"], meta["timestamp"], meta["model"]["id"], meta["model"]["tokenizer_id"], meta["model"]["source"])
    
    return True

def main():
    parser = argparse.ArgumentParser(description="LiveCodeBench 평가 결과 파일을 표준 JSON 형식으로 변환합니다.")
    parser.add_argument(
        '--model-id', 
        type=str, 
        default="Qwen/Qwen3-8B", 
        help="사용된 모델의 ID"
    )
    parser.add_argument(
        '--input-file', 
        type=str, 
        default="output/livecodebench_evaluation_results.json", 
        help="입력 JSON 파일 경로"
    )
    parser.add_argument(
        '--output-file', 
        type=str, 
        default="output/standardized/standardized_livecodebench_evaluation_results.json", 
        help="변환된 파일을 저장할 경로"
    )
    parser.add_argument(
        '--run-id',
        type=str,
        help="명시적으로 설정할 run ID (선택사항)"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        print(f"오류: 입력 파일을 찾을 수 없습니다 - {args.input_file}", file=sys.stderr)
        sys.exit(1)

    success = convert_file(args.input_file, args.output_file, args.model_id, args.run_id)
    
    if success:
        print("LiveCodeBench 결과 변환 완료.")
    else:
        print("LiveCodeBench 결과 변환 실패.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 
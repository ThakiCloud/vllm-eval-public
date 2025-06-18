#!/usr/bin/env python3
"""
실제 VLLM 서버와 연동하는 Deepeval 테스트 스크립트
"""

import json
import logging
import os
from typing import Optional

import requests
from deepeval.models import DeepEvalBaseLLM

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMModel(DeepEvalBaseLLM):
    """VLLM OpenAI 호환 API 모델"""

    def __init__(self, base_url: str = "http://localhost:8000/v1", model_name: str = "qwen3-8b"):
        self.base_url = base_url
        self.model_name = model_name

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, schema=None) -> str:  # noqa: ARG002
        """VLLM API를 통한 텍스트 생성"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 150,
                    "stream": False,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return "API 호출 실패"

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return "요청 실패"

    async def a_generate(self, prompt: str, schema=None) -> str:
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name


def check_vllm_server(base_url: str) -> bool:
    """VLLM 서버 상태 확인"""
    try:
        health_url = base_url.replace("/v1", "/health")
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def load_test_questions(file_path: Optional[str] = None):
    """테스트 질문 로드"""
    if file_path and os.path.exists(file_path):
        with open(file_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    # 기본 테스트 케이스
    return [
        {
            "input": "한국의 수도는 어디인가요?",
            "expected_keywords": ["서울"],
            "context": "한국 지리",
        },
        {
            "input": "파이썬에서 리스트를 정렬하는 방법은?",
            "expected_keywords": ["sort", "sorted"],
            "context": "프로그래밍",
        },
        {
            "input": "지구의 둘레는 얼마나 됩니까?",
            "expected_keywords": ["40", "075", "km"],
            "context": "지구과학",
        },
    ]


def evaluate_response(actual: str, expected_keywords: list) -> tuple:
    """응답 평가"""
    actual_lower = actual.lower()
    matches = sum(1 for keyword in expected_keywords if keyword.lower() in actual_lower)
    score = matches / len(expected_keywords) if expected_keywords else 0.0
    return score, matches, len(expected_keywords)


def main():
    """메인 실행"""
    print("🚀 VLLM Deepeval 테스트 시작")

    # VLLM 서버 설정
    base_url = os.getenv("VLLM_MODEL_ENDPOINT", "http://localhost:8000/v1")
    model_name = os.getenv("MODEL_NAME", "qwen3-8b")

    # 서버 상태 확인
    print(f"📡 VLLM 서버 상태 확인 중... ({base_url})")
    if not check_vllm_server(base_url):
        print("❌ VLLM 서버에 연결할 수 없습니다.")
        print("서버를 먼저 시작해주세요:")
        print("docker run -d --name vllm-server --gpus all -p 8000:8000 \\")
        print("  vllm/vllm-openai:latest --model Qwen/Qwen2-7B-Instruct \\")
        print(f"  --served-model-name {model_name}")
        return

    print("✅ VLLM 서버 연결 성공")

    # 모델 생성
    model = VLLMModel(base_url, model_name)

    # 테스트 질문 로드
    test_questions = load_test_questions("eval/deepeval_tests/datasets/test_local_dataset.jsonl")

    # 결과 저장
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    os.makedirs(output_dir, exist_ok=True)

    results = {
        "test_results": [],
        "summary": {
            "total_tests": len(test_questions),
            "model_name": model.get_model_name(),
            "server_url": base_url,
            "status": "success",
        },
    }

    print(f"\n🧪 {len(test_questions)}개 테스트 실행 중...")

    total_score = 0.0
    for i, question in enumerate(test_questions):
        print(f"\n--- Test {i+1}/{len(test_questions)} ---")
        print(f"질문: {question['input']}")

        # VLLM으로 응답 생성
        actual_output = model.generate(question["input"])
        print(f"응답: {actual_output}")

        # 평가
        if "expected_keywords" in question:
            score, matches, total_keywords = evaluate_response(
                actual_output, question["expected_keywords"]
            )
            print(f"평가: {matches}/{total_keywords} 키워드 매치 (점수: {score:.2f})")
        else:
            # expected_output과 단순 비교
            expected = question.get("expected_output", "")
            score = 1.0 if expected.lower() in actual_output.lower() else 0.5
            print(f"평가: 유사도 점수 {score:.2f}")

        total_score += score

        # 결과 저장
        results["test_results"].append(
            {
                "test_id": i + 1,
                "input": question["input"],
                "actual_output": actual_output,
                "expected_info": question.get(
                    "expected_keywords", question.get("expected_output", "")
                ),
                "score": score,
                "context": question.get("context", ""),
            }
        )

    # 평균 점수 계산
    avg_score = total_score / len(test_questions)
    results["summary"]["average_score"] = avg_score
    results["summary"]["total_score"] = total_score

    # JSON 파일로 저장
    results_file = f"{output_dir}/vllm_deepeval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 결과가 저장되었습니다: {results_file}")

    # 요약 출력
    print("\n📊 최종 결과:")
    print(f"  총 테스트: {len(test_questions)}")
    print(f"  평균 점수: {avg_score:.2f}")
    print(f"  총합 점수: {total_score:.2f}/{len(test_questions)}")
    print(f"  성공률: {(avg_score * 100):.1f}%")

    # 각 테스트 결과 요약
    print("\n📋 개별 테스트 결과:")
    for result in results["test_results"]:
        status = "✅" if result["score"] >= 0.7 else "⚠️" if result["score"] >= 0.4 else "❌"
        print(f"  Test {result['test_id']}: {result['score']:.2f} {status}")

    return results


if __name__ == "__main__":
    main()

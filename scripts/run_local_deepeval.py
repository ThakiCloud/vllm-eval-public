#!/usr/bin/env python3
"""
로컬 VLLM 서버를 이용한 Deepeval 평가 스크립트
"""

import json
import logging
import os
from typing import Any, Optional

import openai
import requests
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMModel(DeepEvalBaseLLM):
    """VLLM OpenAI 호환 API를 위한 모델 클래스"""

    def __init__(self, model_name: str = "qwen3-8b", base_url: str = "http://localhost:1234/v1"):
        self.model_name = model_name
        self.client = openai.OpenAI(
            base_url=base_url, api_key="dummy"  # VLLM에서는 API 키가 필요없음
        )

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, schema: Optional[dict] = None) -> str:  # noqa: ARG002
        """텍스트 생성"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 256,
                    "stream": False,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"API Error: {response.status_code}")
                return "API 오류가 발생했습니다."

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return "서버 연결 오류가 발생했습니다."
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "텍스트 생성 중 오류가 발생했습니다."

    async def a_generate(self, prompt: str, schema: Optional[dict] = None) -> str:
        """비동기 텍스트 생성"""
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name


def load_test_dataset(file_path: str) -> list[dict[str, Any]]:
    """JSONL 테스트 데이터셋 로드"""
    test_cases = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            test_cases.append(json.loads(line.strip()))
    return test_cases


def create_test_cases(dataset: list[dict], model: VLLMModel) -> list[LLMTestCase]:
    """테스트 케이스 생성"""
    test_cases = []

    for item in dataset:
        # 모델로부터 실제 응답 생성
        actual_output = model.generate(item["input"])

        test_case = LLMTestCase(
            input=item["input"],
            actual_output=actual_output,
            expected_output=item["expected_output"],
            context=[item.get("context", "")],
        )
        test_cases.append(test_case)
        logger.info(f"Created test case: {item['input'][:50]}...")

    return test_cases


def main():
    """메인 평가 실행"""
    # 모델 초기화
    model = VLLMModel()

    # 테스트 데이터셋 로드
    dataset_path = "eval/deepeval_tests/datasets/test_local_dataset.jsonl"
    dataset = load_test_dataset(dataset_path)

    # 테스트 케이스 생성
    test_cases = create_test_cases(dataset, model)

    # 평가 메트릭 정의
    metrics = [
        AnswerRelevancyMetric(threshold=0.7, model=model, include_reason=True),
        ContextualRelevancyMetric(threshold=0.7, model=model, include_reason=True),
    ]

    # 평가 실행
    logger.info("Starting evaluation...")
    results = evaluate(test_cases=test_cases, metrics=metrics, print_results=True)

    # 결과 저장
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    os.makedirs(output_dir, exist_ok=True)

    results_file = f"{output_dir}/deepeval_results_{os.getenv('RUN_ID', 'local')}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_results": [
                    {
                        "input": tc.input,
                        "actual_output": tc.actual_output,
                        "expected_output": tc.expected_output,
                        "metrics": {
                            metric.__class__.__name__: {
                                "score": getattr(metric, "score", None),
                                "threshold": getattr(metric, "threshold", None),
                                "success": getattr(metric, "success", None),
                                "reason": getattr(metric, "reason", None),
                            }
                            for metric in metrics
                        },
                    }
                    for tc in test_cases
                ]
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Results saved to: {results_file}")
    return results


if __name__ == "__main__":
    main()

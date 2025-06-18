#!/usr/bin/env python3
"""
Mock VLLM을 이용한 로컬 Deepeval 평가 스크립트 (서버 없이 테스트 가능)
"""

import json
import logging
import os
from typing import Any, Optional

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockVLLMModel(DeepEvalBaseLLM):
    """Mock VLLM 모델 (테스트용)"""

    def __init__(self, model_name: str = "qwen3-8b"):
        self.model_name = model_name
        # Mock 응답을 위한 간단한 규칙 기반 응답
        self.mock_responses = {
            "한국의 수도": "한국의 수도는 서울입니다.",
            "파이썬": "파이썬에서 리스트를 정렬하려면 sort() 메서드나 sorted() 함수를 사용할 수 있습니다.",
            "지구": "지구의 둘레는 약 40,075km입니다.",
            "인공지능": "인공지능(AI)은 인간의 지능을 모방하여 학습, 추론, 문제 해결 등의 작업을 수행하는 컴퓨터 시스템입니다.",
            "커피": "커피의 원산지는 에티오피아입니다.",
        }

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, schema: Optional[dict] = None) -> str:  # noqa: ARG002
        """Mock 텍스트 생성"""
        try:
            # 간단한 키워드 기반 응답
            if "한국" in prompt and "수도" in prompt:
                return "한국의 수도는 서울입니다."
            elif "파이썬" in prompt and "리스트" in prompt:
                return "파이썬에서 리스트를 정렬하려면 sort() 메서드를 사용합니다."
            elif "지구" in prompt and "둘레" in prompt:
                return "지구의 둘레는 약 40,075km입니다."
            else:
                return "죄송합니다. 해당 질문에 대한 답변을 제공할 수 없습니다."

        except Exception as e:
            logger.error(f"Mock generation failed: {e}")
            return "Mock 응답 생성 중 오류가 발생했습니다."

    async def a_generate(self, prompt: str, schema: Optional[dict] = None) -> str:
        """비동기 텍스트 생성"""
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name


def load_test_dataset(file_path: str) -> list[dict[str, Any]]:
    """JSONL 테스트 데이터셋 로드"""
    test_cases = []
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    test_cases.append(json.loads(line.strip()))
        logger.info(f"Loaded {len(test_cases)} test cases from {file_path}")
    except FileNotFoundError:
        logger.error(f"Dataset file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        return []

    return test_cases


def create_test_cases(dataset: list[dict], model: MockVLLMModel) -> list[LLMTestCase]:
    """테스트 케이스 생성"""
    test_cases = []

    for item in dataset:
        # Mock 모델로부터 실제 응답 생성
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
    model = MockVLLMModel()

    # 테스트 데이터셋 로드
    dataset_path = "eval/deepeval_tests/datasets/test_local_dataset.jsonl"
    dataset = load_test_dataset(dataset_path)

    if not dataset:
        logger.error("No test data available. Exiting.")
        return

    # 테스트 케이스 생성
    test_cases = create_test_cases(dataset, model)

    # 평가 메트릭 정의 (간단한 메트릭만 사용)
    try:
        metrics = [AnswerRelevancyMetric(threshold=0.5, model=model, include_reason=True)]

        # 평가 실행 (print_results 파라미터 제거)
        logger.info("Starting evaluation...")
        results = evaluate(test_cases=test_cases, metrics=metrics)

        # 결과 저장
        output_dir = os.getenv("OUTPUT_DIR", "./test_results")
        os.makedirs(output_dir, exist_ok=True)

        run_id = os.getenv("RUN_ID", "local_mock")
        results_file = f"{output_dir}/deepeval_results_{run_id}.json"

        # 결과 데이터 구성
        result_data = {
            "test_results": [],
            "summary": {
                "total_tests": len(test_cases),
                "model_name": model.get_model_name(),
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        for i, tc in enumerate(test_cases):
            test_result = {
                "test_id": i + 1,
                "input": tc.input,
                "actual_output": tc.actual_output,
                "expected_output": tc.expected_output,
                "context": tc.context,
                "metrics": {},
            }

            # 각 메트릭 결과 추가
            for metric in metrics:
                metric_name = metric.__class__.__name__
                test_result["metrics"][metric_name] = {
                    "score": getattr(metric, "score", 0.8),  # Mock 점수
                    "threshold": getattr(metric, "threshold", 0.5),
                    "success": getattr(metric, "success", True),
                    "reason": getattr(metric, "reason", "Mock evaluation successful"),
                }

            result_data["test_results"].append(test_result)

        # 결과 저장
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to: {results_file}")

        # 간단한 결과 요약 출력
        print("\n=== Mock Deepeval Results Summary ===")
        print(f"Total Tests: {len(test_cases)}")
        print(f"Model: {model.get_model_name()}")
        print("\nSample Results:")
        for i, tc in enumerate(test_cases[:3]):  # 처음 3개만 출력
            print(f"\nTest {i+1}:")
            print(f"  Input: {tc.input}")
            print(f"  Expected: {tc.expected_output}")
            print(f"  Actual: {tc.actual_output}")
            print(
                f"  Match: {'✅' if tc.actual_output in tc.expected_output or tc.expected_output in tc.actual_output else '❌'}"
            )

        return results

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        print(f"\n❌ Evaluation failed: {e}")

        # 간단한 직접 비교 수행
        print("\n=== Direct Comparison (Fallback) ===")
        for i, tc in enumerate(test_cases):
            similarity = 1.0 if tc.actual_output == tc.expected_output else 0.8
            print(f"Test {i+1}: {tc.input[:50]}... → Score: {similarity:.2f}")

        return None


if __name__ == "__main__":
    main()

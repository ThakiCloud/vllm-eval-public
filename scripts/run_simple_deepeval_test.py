#!/usr/bin/env python3
"""
간단한 Deepeval 테스트 스크립트
"""

import json
import logging
import os

from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleModel(DeepEvalBaseLLM):
    """간단한 Mock 모델"""

    def __init__(self):
        self.model_name = "simple-mock"

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str, schema=None) -> str:  # noqa: ARG002
        """간단한 응답 생성"""
        if "한국" in prompt:
            return "한국의 수도는 서울입니다."
        elif "파이썬" in prompt:
            return "파이썬에서 리스트를 정렬하려면 sort() 메서드나 sorted() 함수를 사용하세요."
        elif "지구" in prompt:
            return "지구의 둘레는 약 40,075km입니다."
        else:
            return "죄송합니다. 해당 질문에 대한 답변을 찾을 수 없습니다."

    async def a_generate(self, prompt: str, schema=None) -> str:
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return self.model_name


def main():
    """메인 실행"""
    print("🚀 간단한 Deepeval 테스트 시작")

    # 모델 생성
    model = SimpleModel()

    # 테스트 케이스 생성
    test_cases = [
        LLMTestCase(
            input="한국의 수도는 어디인가요?",
            actual_output=model.generate("한국의 수도는 어디인가요?"),
            expected_output="한국의 수도는 서울입니다.",
        ),
        LLMTestCase(
            input="파이썬에서 리스트 정렬 방법은?",
            actual_output=model.generate("파이썬에서 리스트 정렬 방법은?"),
            expected_output="파이썬에서 리스트를 정렬하려면 sort() 메서드를 사용합니다.",
        ),
    ]

    # 결과 저장
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    os.makedirs(output_dir, exist_ok=True)

    results = {
        "test_results": [],
        "summary": {
            "total_tests": len(test_cases),
            "model_name": model.get_model_name(),
            "status": "success",
        },
    }

    print("\n=== 테스트 결과 ===")
    for i, tc in enumerate(test_cases):
        print(f"\nTest {i+1}:")
        print(f"  Input: {tc.input}")
        print(f"  Expected: {tc.expected_output}")
        print(f"  Actual: {tc.actual_output}")

        # 정확도 계산
        accuracy = 1.0 if tc.actual_output == tc.expected_output else 0.8
        match = "✅" if accuracy == 1.0 else "❌"

        print(f"  Accuracy: {accuracy:.2f} {match}")

        # 결과 저장
        results["test_results"].append(
            {
                "test_id": i + 1,
                "input": tc.input,
                "expected_output": tc.expected_output,
                "actual_output": tc.actual_output,
                "accuracy": accuracy,
                "match": accuracy == 1.0,
            }
        )

    # JSON 파일로 저장
    results_file = f"{output_dir}/simple_deepeval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 결과가 저장되었습니다: {results_file}")

    # 요약 출력
    total_tests = len(test_cases)
    passed_tests = sum(1 for result in results["test_results"] if result["match"])
    success_rate = (passed_tests / total_tests) * 100

    print("\n📊 요약:")
    print(f"  총 테스트: {total_tests}")
    print(f"  통과: {passed_tests}")
    print(f"  성공률: {success_rate:.1f}%")

    return results


if __name__ == "__main__":
    main()

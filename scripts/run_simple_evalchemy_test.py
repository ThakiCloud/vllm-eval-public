#!/usr/bin/env python3
"""
간단한 Evalchemy 벤치마크 대안 (직접 API 호출 방식)
"""

import json
import logging
import os
import re
import time
from typing import Any

import requests

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleEvalchemy:
    """간단한 벤치마크 실행 클래스"""

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self.session = requests.Session()

    def call_model(self, prompt: str, max_tokens: int = 50) -> str:
        """VLLM API 호출"""
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return ""

    def extract_answer(self, response: str) -> str:
        """모델 응답에서 A, B, C, D 답변 추출"""
        # deepseek-r1 모델의 경우 <think> 태그 이후의 실제 답변 부분 찾기
        if "</think>" in response:
            # </think> 이후의 내용에서 답변 추출
            after_think = response.split("</think>")[-1].strip()
            if after_think:
                response = after_think

        # 일반적인 패턴들로 답변 추출
        # 패턴 1: "답: A" 또는 "답변: B" 등
        answer_pattern = r"답\s*:\s*([A-D])"
        match = re.search(answer_pattern, response)
        if match:
            return match.group(1)

        # 패턴 2: "정답은 A" 또는 "답은 B" 등
        answer_pattern2 = r"(?:정답|답)은?\s*([A-D])"
        match = re.search(answer_pattern2, response)
        if match:
            return match.group(1)

        # 패턴 3: 마지막에 나오는 A, B, C, D
        letters = re.findall(r"\b([A-D])\b", response)
        if letters:
            return letters[-1]  # 마지막에 나오는 것을 답으로 간주

        # 패턴 4: 첫 번째로 나오는 A, B, C, D
        for char in response.upper():
            if char in ["A", "B", "C", "D"]:
                return char

        return ""  # 답변을 찾지 못함

    def run_arc_easy_style_test(self) -> dict[str, Any]:
        """ARC Easy 스타일 테스트 실행"""
        questions = [
            {
                "question": "다음 중 지구의 위성은 무엇입니까?",
                "choices": ["A) 태양", "B) 달", "C) 화성", "D) 금성"],
                "correct": "B",
                "id": "q1",
            },
            {
                "question": "물의 화학 기호는 무엇입니까?",
                "choices": ["A) H2O", "B) CO2", "C) O2", "D) NaCl"],
                "correct": "A",
                "id": "q2",
            },
            {
                "question": "1 + 1은 무엇입니까?",
                "choices": ["A) 1", "B) 2", "C) 3", "D) 4"],
                "correct": "B",
                "id": "q3",
            },
            {
                "question": "한국의 수도는 어디입니까?",
                "choices": ["A) 부산", "B) 서울", "C) 대구", "D) 광주"],
                "correct": "B",
                "id": "q4",
            },
            {
                "question": "컴퓨터의 CPU는 무엇을 의미합니까?",
                "choices": ["A) 중앙처리장치", "B) 하드디스크", "C) 메모리", "D) 모니터"],
                "correct": "A",
                "id": "q5",
            },
        ]

        results = []
        correct_count = 0

        print("🧪 ARC Easy 스타일 테스트 실행 중...")

        for i, q in enumerate(questions):
            print(f"\n--- 질문 {i+1}/{len(questions)} ---")
            print(f"질문: {q['question']}")

            # 프롬프트 구성 (더 명확한 지시)
            prompt = f"""다음 질문에 대해 가장 적절한 답을 A, B, C, D 중에서 선택해주세요.

질문: {q['question']}

선택지:
{chr(10).join(q['choices'])}

위 선택지 중에서 정답을 A, B, C, D 중 하나의 알파벳으로만 답해주세요.
답:"""

            # 모델 호출
            response = self.call_model(prompt, max_tokens=100)
            print(f"모델 응답: {response}")

            # 답변 추출
            predicted = self.extract_answer(response)

            # 정답 확인
            is_correct = predicted == q["correct"]
            if is_correct:
                correct_count += 1
                status = "✅"
            else:
                status = "❌"

            print(f"예측: {predicted}, 정답: {q['correct']} {status}")

            results.append(
                {
                    "question_id": q["id"],
                    "question": q["question"],
                    "choices": q["choices"],
                    "correct_answer": q["correct"],
                    "predicted_answer": predicted,
                    "model_response": response,
                    "is_correct": is_correct,
                }
            )

            time.sleep(1)  # API 호출 간격

        accuracy = correct_count / len(questions)

        return {
            "task": "arc_easy_style",
            "total_questions": len(questions),
            "correct_answers": correct_count,
            "accuracy": accuracy,
            "details": results,
        }

    def run_hellaswag_style_test(self) -> dict[str, Any]:
        """HellaSwag 스타일 테스트 실행"""
        scenarios = [
            {
                "context": "사람이 길을 걷고 있다",
                "endings": [
                    "A) 갑자기 날아갔다",
                    "B) 계속해서 앞으로 걸었다",
                    "C) 바닥에 뿌리를 내렸다",
                    "D) 투명해졌다",
                ],
                "correct": "B",
                "id": "h1",
            },
            {
                "context": "학생이 책을 읽고 있다",
                "endings": [
                    "A) 책이 말을 하기 시작했다",
                    "B) 페이지를 넘겼다",
                    "C) 책이 날아갔다",
                    "D) 학생이 사라졌다",
                ],
                "correct": "B",
                "id": "h2",
            },
            {
                "context": "요리사가 음식을 준비하고 있다",
                "endings": [
                    "A) 재료를 손질했다",
                    "B) 주방이 폭발했다",
                    "C) 음식이 저절로 만들어졌다",
                    "D) 요리사가 춤을 추었다",
                ],
                "correct": "A",
                "id": "h3",
            },
        ]

        results = []
        correct_count = 0

        print("\n🧪 HellaSwag 스타일 테스트 실행 중...")

        for i, scenario in enumerate(scenarios):
            print(f"\n--- 시나리오 {i+1}/{len(scenarios)} ---")
            print(f"상황: {scenario['context']}")

            prompt = f"""다음 상황에서 가장 자연스럽고 현실적인 다음 행동을 A, B, C, D 중에서 선택해주세요.

상황: {scenario['context']}

다음 행동 선택지:
{chr(10).join(scenario['endings'])}

위 선택지 중에서 가장 적절한 것을 A, B, C, D 중 하나의 알파벳으로만 답해주세요.
답:"""

            response = self.call_model(prompt, max_tokens=100)
            print(f"모델 응답: {response}")

            # 답변 추출
            predicted = self.extract_answer(response)

            is_correct = predicted == scenario["correct"]
            if is_correct:
                correct_count += 1
                status = "✅"
            else:
                status = "❌"

            print(f"예측: {predicted}, 정답: {scenario['correct']} {status}")

            results.append(
                {
                    "scenario_id": scenario["id"],
                    "context": scenario["context"],
                    "endings": scenario["endings"],
                    "correct_answer": scenario["correct"],
                    "predicted_answer": predicted,
                    "model_response": response,
                    "is_correct": is_correct,
                }
            )

            time.sleep(1)

        accuracy = correct_count / len(scenarios)

        return {
            "task": "hellaswag_style",
            "total_scenarios": len(scenarios),
            "correct_answers": correct_count,
            "accuracy": accuracy,
            "details": results,
        }


def main():
    """메인 실행 함수"""
    print("🚀 간단한 Evalchemy 벤치마크 시작")

    # 설정
    base_url = os.getenv("VLLM_MODEL_ENDPOINT", "http://localhost:1234/v1")
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")

    # 모델 확인
    try:
        response = requests.get(f"{base_url}/models", timeout=5)
        models_data = response.json()
        available_models = [model["id"] for model in models_data.get("data", [])]

        if not available_models:
            print("❌ 사용 가능한 모델이 없습니다.")
            return

        model_name = available_models[0]
        print(f"✅ 사용 모델: {model_name}")

    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return

    # 벤치마크 실행
    evalchemy = SimpleEvalchemy(base_url, model_name)

    # ARC Easy 스타일 테스트
    arc_results = evalchemy.run_arc_easy_style_test()

    # HellaSwag 스타일 테스트
    hellaswag_results = evalchemy.run_hellaswag_style_test()

    # 결과 통합
    final_results = {
        "model": model_name,
        "server_url": base_url,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": {"arc_easy_style": arc_results, "hellaswag_style": hellaswag_results},
        "summary": {
            "arc_easy_accuracy": arc_results["accuracy"],
            "hellaswag_accuracy": hellaswag_results["accuracy"],
            "overall_accuracy": (arc_results["accuracy"] + hellaswag_results["accuracy"]) / 2,
        },
    }

    # 결과 저장
    os.makedirs(output_dir, exist_ok=True)
    results_file = f"{output_dir}/simple_evalchemy_results.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)

    # 결과 출력
    print("\n" + "=" * 50)
    print("📊 최종 결과")
    print("=" * 50)
    print(f"모델: {model_name}")
    print(
        f"ARC Easy 스타일 정확도: {arc_results['accuracy']:.1%} ({arc_results['correct_answers']}/{arc_results['total_questions']})"
    )
    print(
        f"HellaSwag 스타일 정확도: {hellaswag_results['accuracy']:.1%} ({hellaswag_results['correct_answers']}/{hellaswag_results['total_scenarios']})"
    )
    print(f"전체 평균 정확도: {final_results['summary']['overall_accuracy']:.1%}")
    print(f"\n💾 결과가 저장되었습니다: {results_file}")


if __name__ == "__main__":
    main()

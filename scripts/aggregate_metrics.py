#!/usr/bin/env python3
"""
Aggregate Metrics Script

Deepeval과 Evalchemy 평가 결과를 ClickHouse에 저장하고
Teams Webhook으로 알림을 전송하는 스크립트입니다.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from clickhouse_driver import Client
from jinja2 import Template

# Constants
REGRESSION_THRESHOLD = 0.1
SIGNIFICANT_CHANGE_THRESHOLD = 0.2
HTTP_TIMEOUT = 30
DEFAULT_HISTORICAL_LIMIT = 5
RUN_ID_DISPLAY_LENGTH = 8

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MetricsAggregator:
    """메트릭 집계 및 저장 클래스."""

    def __init__(
        self,
        clickhouse_host: str = "localhost",
        clickhouse_port: int = 9000,
        clickhouse_database: str = "vllm_eval",
        teams_webhook_url: Optional[str] = None,
    ):
        """
        Args:
            clickhouse_host: ClickHouse 호스트
            clickhouse_port: ClickHouse 포트
            clickhouse_database: 데이터베이스명
            teams_webhook_url: Teams Webhook URL
        """
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_database = clickhouse_database
        self.teams_webhook_url = teams_webhook_url

        # ClickHouse 클라이언트 초기화
        try:
            self.clickhouse_client = Client(
                host=clickhouse_host, port=clickhouse_port, database=clickhouse_database
            )
            logger.info(f"ClickHouse 연결 성공: {clickhouse_host}:{clickhouse_port}")
        except Exception as e:
            logger.error(f"ClickHouse 연결 실패: {e}")
            self.clickhouse_client = None

    def ensure_table_exists(self) -> None:
        """ClickHouse 테이블 생성 (존재하지 않는 경우)."""
        if not self.clickhouse_client:
            logger.warning("ClickHouse 클라이언트가 없어 테이블 생성을 건너뜁니다.")
            return

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS vllm_eval.results (
            run_id String,
            model_tag String,
            metric_name String,
            metric_value Float64,
            metric_category String,
            evaluation_framework String,
            dataset_name String,
            dataset_version String,
            timestamp DateTime64(3),
            metadata String
        ) ENGINE = MergeTree()
        ORDER BY (model_tag, timestamp, metric_name)
        PARTITION BY toYYYYMM(timestamp)
        """

        try:
            self.clickhouse_client.execute(create_table_sql)
            logger.info("ClickHouse 테이블 확인/생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")

    def load_evaluation_results(self, results_file: str) -> dict:
        """평가 결과 파일 로드."""
        logger.info(f"평가 결과 로드: {results_file}")

        try:
            results_path = Path(results_file)
            results = json.loads(results_path.read_text(encoding="utf-8"))
            return results
        except Exception as e:
            logger.error(f"결과 파일 로드 실패: {e}")
            return {}

    def parse_deepeval_results(self, results: dict, run_id: str, model_tag: str) -> list[dict]:
        """Deepeval 결과 파싱."""
        parsed_results = []

        if "deepeval_results" not in results:
            return parsed_results

        deepeval_data = results["deepeval_results"]
        timestamp = datetime.utcnow()

        # 메트릭별 결과 파싱
        for metric_name, metric_value in deepeval_data.get("metrics", {}).items():
            if isinstance(metric_value, (int, float)):
                parsed_results.append(
                    {
                        "run_id": run_id,
                        "model_tag": model_tag,
                        "metric_name": metric_name,
                        "metric_value": float(metric_value),
                        "metric_category": self._get_metric_category(metric_name),
                        "evaluation_framework": "deepeval",
                        "dataset_name": deepeval_data.get("dataset_name", "unknown"),
                        "dataset_version": deepeval_data.get("dataset_version", "v1.0.0"),
                        "timestamp": timestamp,
                        "metadata": json.dumps(
                            {
                                "execution_time": deepeval_data.get("execution_time"),
                                "sample_count": deepeval_data.get("sample_count"),
                                "success_rate": deepeval_data.get("success_rate"),
                            }
                        ),
                    }
                )

        logger.info(f"Deepeval 결과 파싱 완료: {len(parsed_results)}개 메트릭")
        return parsed_results

    def parse_evalchemy_results(self, results: dict, run_id: str, model_tag: str) -> list[dict]:
        """Evalchemy 결과 파싱."""
        parsed_results = []

        if "evalchemy_results" not in results:
            return parsed_results

        evalchemy_data = results["evalchemy_results"]
        timestamp = datetime.utcnow()

        # 벤치마크별 결과 파싱
        for benchmark_name, benchmark_data in evalchemy_data.get("benchmarks", {}).items():
            if isinstance(benchmark_data, dict):
                for metric_name, metric_value in benchmark_data.items():
                    if isinstance(metric_value, (int, float)):
                        parsed_results.append(
                            {
                                "run_id": run_id,
                                "model_tag": model_tag,
                                "metric_name": f"{benchmark_name}_{metric_name}",
                                "metric_value": float(metric_value),
                                "metric_category": "benchmark",
                                "evaluation_framework": "evalchemy",
                                "dataset_name": benchmark_name,
                                "dataset_version": evalchemy_data.get("dataset_versions", {}).get(
                                    benchmark_name, "v1.0.0"
                                ),
                                "timestamp": timestamp,
                                "metadata": json.dumps(
                                    {
                                        "shots": evalchemy_data.get("shots", 0),
                                        "batch_size": evalchemy_data.get("batch_size", 1),
                                        "model_args": evalchemy_data.get("model_args", {}),
                                    }
                                ),
                            }
                        )

        logger.info(f"Evalchemy 결과 파싱 완료: {len(parsed_results)}개 메트릭")
        return parsed_results

    def _get_metric_category(self, metric_name: str) -> str:
        """메트릭 이름에서 카테고리 추출."""
        category_mapping = {
            "rag_precision": "rag",
            "rag_recall": "rag",
            "rag_f1": "rag",
            "hallucination_rate": "hallucination",
            "context_relevance": "context",
            "answer_accuracy": "accuracy",
            "faithfulness": "faithfulness",
        }

        for key, category in category_mapping.items():
            if key in metric_name.lower():
                return category

        return "general"

    def store_results(self, results: list[dict]) -> None:
        """ClickHouse에 결과 저장."""
        if not self.clickhouse_client:
            logger.warning("ClickHouse 클라이언트가 없어 저장을 건너뜁니다.")
            return

        if not results:
            logger.warning("저장할 결과가 없습니다.")
            return

        try:
            # 배치 삽입
            self.clickhouse_client.execute(
                "INSERT INTO vllm_eval.results VALUES",
                [
                    (
                        r["run_id"],
                        r["model_tag"],
                        r["metric_name"],
                        r["metric_value"],
                        r["metric_category"],
                        r["evaluation_framework"],
                        r["dataset_name"],
                        r["dataset_version"],
                        r["timestamp"],
                        r["metadata"],
                    )
                    for r in results
                ],
            )
            logger.info(f"ClickHouse에 {len(results)}개 결과 저장 완료")

        except Exception as e:
            logger.error(f"ClickHouse 저장 실패: {e}")

    def get_historical_results(
        self, model_tag: str, limit: int = DEFAULT_HISTORICAL_LIMIT
    ) -> list[dict]:
        """과거 결과 조회."""
        if not self.clickhouse_client:
            return []

        query = """
        SELECT metric_name, AVG(metric_value) as avg_value
        FROM vllm_eval.results
        WHERE model_tag = %(model_tag)s
        AND timestamp >= now() - INTERVAL 30 DAY
        GROUP BY metric_name
        ORDER BY metric_name
        LIMIT %(limit)s
        """

        try:
            results = self.clickhouse_client.execute(
                query, {"model_tag": model_tag, "limit": limit}
            )
            return [{"metric_name": row[0], "avg_value": row[1]} for row in results]
        except Exception as e:
            logger.error(f"과거 결과 조회 실패: {e}")
            return []

    def detect_regression(self, current_results: list[dict], model_tag: str) -> list[dict]:
        """품질 퇴화 탐지 (최근 N회 Rolling Mean 대비 10% 하락)."""
        regressions = []
        historical_results = self.get_historical_results(model_tag)

        # 이력 데이터를 딕셔너리로 변환
        historical_dict = {
            result["metric_name"]: result["avg_value"] for result in historical_results
        }

        for current in current_results:
            metric_name = current["metric_name"]
            current_value = current["metric_value"]

            if metric_name in historical_dict:
                historical_avg = historical_dict[metric_name]
                decline_rate = (historical_avg - current_value) / historical_avg

                if decline_rate > REGRESSION_THRESHOLD:  # 10% 이상 하락
                    regressions.append(
                        {
                            "metric_name": metric_name,
                            "current_value": current_value,
                            "historical_avg": historical_avg,
                            "decline_rate": decline_rate * 100,
                            "severity": (
                                "high" if decline_rate > SIGNIFICANT_CHANGE_THRESHOLD else "medium"
                            ),
                        }
                    )

        if regressions:
            logger.warning(f"품질 퇴화 감지: {len(regressions)}개 메트릭")

        return regressions

    def send_teams_notification(
        self, run_id: str, model_tag: str, results_summary: dict, regressions: list[dict]
    ) -> None:
        """Microsoft Teams에 알림 전송."""
        if not self.teams_webhook_url:
            logger.info("Teams Webhook URL이 없어 알림을 건너뜁니다.")
            return

        # Adaptive Card 템플릿
        card_template = Template(
            """
        {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": "🚀 VLLM 평가 완료: {{ model_tag }}"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Run ID",
                                        "value": "{{ run_id }}"
                                    },
                                    {
                                        "title": "실행 시간",
                                        "value": "{{ execution_time }}"
                                    },
                                    {
                                        "title": "총 메트릭",
                                        "value": "{{ total_metrics }}"
                                    },
                                    {
                                        "title": "상태",
                                        "value": "{{ status }}"
                                    }
                                ]
                            }
                            {% if regressions %}
                            ,{
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": "⚠️ 품질 퇴화 감지",
                                "color": "Attention"
                            }
                            {% for regression in regressions %}
                            ,{
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "메트릭",
                                        "value": "{{ regression.metric_name }}"
                                    },
                                    {
                                        "title": "현재값",
                                        "value": "{{ regression.current_value | round(3) }}"
                                    },
                                    {
                                        "title": "이전 평균",
                                        "value": "{{ regression.historical_avg | round(3) }}"
                                    },
                                    {
                                        "title": "하락률",
                                        "value": "{{ regression.decline_rate | round(1) }}%"
                                    }
                                ]
                            }
                            {% endfor %}
                            {% endif %}
                        ],
                        "actions": [
                            {
                                "type": "Action.OpenUrl",
                                "title": "Grafana 대시보드",
                                "url": "{{ grafana_url }}"
                            },
                            {
                                "type": "Action.OpenUrl",
                                "title": "Argo Workflows",
                                "url": "{{ argo_url }}"
                            }
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.2"
                    }
                }
            ]
        }
        """
        )

        # 템플릿 변수 준비
        template_vars = {
            "run_id": run_id[:RUN_ID_DISPLAY_LENGTH],  # 짧게 표시
            "model_tag": model_tag,
            "execution_time": results_summary.get("execution_time", "N/A"),
            "total_metrics": results_summary.get("total_metrics", 0),
            "status": "⚠️ 퇴화 감지" if regressions else "✅ 성공",
            "regressions": regressions,
            "grafana_url": "http://grafana.company.com/d/vllm-eval",
            "argo_url": "http://argo.company.com/workflows",
        }

        # Adaptive Card 생성
        try:
            card_json = card_template.render(**template_vars)
            card_data = json.loads(card_json)

            # Teams에 전송
            response = requests.post(self.teams_webhook_url, json=card_data, timeout=HTTP_TIMEOUT)

            if response.status_code == 200:
                logger.info("Teams 알림 전송 성공")
            else:
                logger.error(f"Teams 알림 전송 실패: {response.status_code}")

        except Exception as e:
            logger.error(f"Teams 알림 전송 중 오류: {e}")

    def aggregate(
        self,
        deepeval_results_file: str,
        evalchemy_results_file: str,
        model_tag: str,
        run_id: Optional[str] = None,
    ) -> None:
        """전체 집계 프로세스 실행."""
        if not run_id:
            run_id = str(uuid.uuid4())

        logger.info(f"메트릭 집계 시작: {run_id}")

        # 테이블 확인/생성
        self.ensure_table_exists()

        # 결과 파일 로드
        all_results = {}

        deepeval_path = Path(deepeval_results_file)
        if deepeval_path.exists():
            deepeval_results = self.load_evaluation_results(deepeval_results_file)
            all_results["deepeval_results"] = deepeval_results

        evalchemy_path = Path(evalchemy_results_file)
        if evalchemy_path.exists():
            evalchemy_results = self.load_evaluation_results(evalchemy_results_file)
            all_results["evalchemy_results"] = evalchemy_results

        # 결과 파싱
        parsed_results = []
        parsed_results.extend(self.parse_deepeval_results(all_results, run_id, model_tag))
        parsed_results.extend(self.parse_evalchemy_results(all_results, run_id, model_tag))

        # ClickHouse에 저장
        self.store_results(parsed_results)

        # 품질 퇴화 감지
        regressions = self.detect_regression(parsed_results, model_tag)

        # 결과 요약
        results_summary = {
            "run_id": run_id,
            "model_tag": model_tag,
            "total_metrics": len(parsed_results),
            "execution_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "regressions_count": len(regressions),
        }

        # Teams 알림 전송
        self.send_teams_notification(run_id, model_tag, results_summary, regressions)

        logger.info(f"메트릭 집계 완료: {run_id}")

        # 결과 반환 (테스트용)
        return {
            "results_summary": results_summary,
            "parsed_results": parsed_results,
            "regressions": regressions,
        }


def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description="평가 결과 집계 및 저장")
    parser.add_argument("--deepeval-results", required=True, help="Deepeval 결과 파일 경로")
    parser.add_argument("--evalchemy-results", required=True, help="Evalchemy 결과 파일 경로")
    parser.add_argument("--model-tag", required=True, help="모델 태그 (예: release-0.3.1)")
    parser.add_argument("--run-id", help="실행 ID (미지정시 자동 생성)")
    parser.add_argument("--clickhouse-host", default="localhost", help="ClickHouse 호스트")
    parser.add_argument("--clickhouse-port", type=int, default=9000, help="ClickHouse 포트")
    parser.add_argument("--teams-webhook-url", help="Teams Webhook URL")

    args = parser.parse_args()

    # 환경 변수에서 Teams Webhook URL 가져오기
    teams_webhook_url = args.teams_webhook_url or os.getenv("TEAMS_WEBHOOK_URL")

    try:
        aggregator = MetricsAggregator(
            clickhouse_host=args.clickhouse_host,
            clickhouse_port=args.clickhouse_port,
            teams_webhook_url=teams_webhook_url,
        )

        result = aggregator.aggregate(
            deepeval_results_file=args.deepeval_results,
            evalchemy_results_file=args.evalchemy_results,
            model_tag=args.model_tag,
            run_id=args.run_id,
        )

        # 결과 출력
        print(json.dumps(result["results_summary"], indent=2))

    except Exception as e:
        logger.error(f"집계 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

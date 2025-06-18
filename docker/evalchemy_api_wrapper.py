#!/usr/bin/env python3
# API-based Evalchemy evaluation wrapper script
# Uses lm-evaluation-harness with API models for VLLM evaluation

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 상수 정의
MAX_BATCH_SIZE = 100
MIN_TIMEOUT = 60
MAX_TIMEOUT = 7200
MAX_MODEL_NAME_LENGTH = 200
MAX_NUM_FEWSHOT = 100
MAX_LIMIT = 10000
GIT_TIMEOUT = 10


class EvAlchemyAPIRunner:
    """API 기반 Evalchemy 평가 실행기"""

    def __init__(self, config_file: str, model_endpoint: str, output_file: str):
        self.config_file = Path(config_file)
        self.model_endpoint = model_endpoint
        self.output_file = Path(output_file)
        self.lm_eval_path = Path("/app/lm-eval")

        # 보안: 경로 검증
        if not self.lm_eval_path.exists():
            raise ValueError(f"lm-eval path does not exist: {self.lm_eval_path}")
        if not self.config_file.exists():
            raise ValueError(f"Config file does not exist: {self.config_file}")

    def load_config(self) -> dict[str, Any]:
        """설정 파일 로드"""
        try:
            with self.config_file.open(encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"설정 파일 로드 완료: {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise

    def determine_model_type(self, model_endpoint: str) -> tuple[str, dict[str, str]]:
        """모델 엔드포인트를 기반으로 모델 타입과 인자 결정"""
        model_args = {}

        # 보안: URL 검증
        if not model_endpoint or len(model_endpoint.strip()) == 0:
            raise ValueError("Model endpoint cannot be empty")

        if "openai" in model_endpoint.lower() or "api.openai.com" in model_endpoint:
            model_type = "openai-chat-completions"
            model_args = {
                "model": "gpt-4",  # 기본값, 설정에서 오버라이드 가능
                "api_key": os.getenv("OPENAI_API_KEY", ""),
            }
        elif "anthropic" in model_endpoint.lower():
            model_type = "anthropic-chat-completions"
            model_args = {
                "model": "claude-3-sonnet-20240229",  # 기본값
                "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            }
        elif model_endpoint.startswith("http"):
            # 로컬 또는 커스텀 API 서버
            model_type = "local-chat-completions"
            model_args = {
                "base_url": model_endpoint,
                "model": "vllm-model",  # 기본값
                "num_concurrent": "1",
                "max_retries": str(os.getenv("MAX_RETRIES", "3")),
                "timeout": str(os.getenv("API_TIMEOUT", "300")),
            }
        else:
            raise ValueError(f"지원하지 않는 모델 엔드포인트: {model_endpoint}")

        return model_type, model_args

    def _validate_task_config(self, task_config: dict[str, Any]) -> None:
        """태스크 설정 검증"""
        if not isinstance(task_config, dict):
            raise ValueError("Task config must be a dictionary")

        # 보안: 숫자 값 검증
        batch_size = task_config.get("batch_size", 1)
        if not isinstance(batch_size, int) or batch_size < 1 or batch_size > MAX_BATCH_SIZE:
            raise ValueError(f"Invalid batch_size: {batch_size}")

        timeout = task_config.get("timeout", 3600)
        if not isinstance(timeout, int) or timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
            raise ValueError(f"Invalid timeout: {timeout}")

    def run_benchmark(self, task_name: str, task_config: dict[str, Any]) -> dict[str, Any]:
        """개별 벤치마크 실행 (API 기반)"""
        logger.info(f"벤치마크 실행 시작: {task_name}")

        try:
            # 보안: 입력 검증
            if not task_name or not task_name.replace("_", "").replace("-", "").isalnum():
                raise ValueError(f"Invalid task name: {task_name}")

            self._validate_task_config(task_config)

            # 모델 타입과 인자 결정
            model_type, model_args = self.determine_model_type(self.model_endpoint)

            # 태스크 설정에서 모델 인자 오버라이드
            if "model_name" in task_config:
                model_name = task_config["model_name"]
                # 보안: 모델명 검증
                if not model_name or len(model_name) > MAX_MODEL_NAME_LENGTH:
                    raise ValueError(f"Invalid model name: {model_name}")
                model_args["model"] = model_name

            # 모델 인자 문자열 생성 (보안: 특수문자 이스케이프)
            model_args_str = ",".join(
                [
                    f"{k}={v}"
                    for k, v in model_args.items()
                    if isinstance(k, str) and isinstance(v, str)
                ]
            )

            # 보안: 임시 디렉토리 안전하게 생성
            with tempfile.TemporaryDirectory(prefix=f"evalchemy_{task_name}_") as temp_dir:
                output_path = Path(temp_dir) / "results"

                # lm_eval 명령 구성 (보안: 리스트 형태로 구성하여 shell injection 방지)
                cmd = [
                    "python",
                    "-m",
                    "lm_eval",
                    "--model",
                    model_type,
                    "--model_args",
                    model_args_str,
                    "--tasks",
                    task_name,
                    "--batch_size",
                    str(task_config.get("batch_size", 1)),
                    "--output_path",
                    str(output_path),
                    "--log_samples",
                ]

                # 추가 인자 설정 (보안: 값 검증)
                if task_config.get("num_fewshot") is not None:
                    num_fewshot = task_config["num_fewshot"]
                    if isinstance(num_fewshot, int) and 0 <= num_fewshot <= MAX_NUM_FEWSHOT:
                        cmd.extend(["--num_fewshot", str(num_fewshot)])

                if task_config.get("limit"):
                    limit = task_config["limit"]
                    if isinstance(limit, int) and 1 <= limit <= MAX_LIMIT:
                        cmd.extend(["--limit", str(limit)])

                # Chat 모델의 경우 chat template 적용
                if "chat" in model_type:
                    cmd.append("--apply_chat_template")

                # 환경 변수 설정 (보안: 기존 환경 복사)
                process_env = os.environ.copy()

                # API 키 설정 (보안: 키 존재 여부만 확인)
                if (
                    model_type.startswith("openai")
                    and "OPENAI_API_KEY" not in process_env
                    and model_args.get("api_key")
                ):
                    process_env["OPENAI_API_KEY"] = model_args["api_key"]
                elif (
                    model_type.startswith("anthropic")
                    and "ANTHROPIC_API_KEY" not in process_env
                    and model_args.get("api_key")
                ):
                    process_env["ANTHROPIC_API_KEY"] = model_args["api_key"]

                # 명령 실행 (보안: shell=False, 경로 검증)
                logger.info(f"실행 명령: {' '.join(cmd)}")
                result = subprocess.run(  # nosec B603 - subprocess with list is safe
                    cmd,
                    cwd=self.lm_eval_path,
                    env=process_env,
                    capture_output=True,
                    text=True,
                    timeout=task_config.get("timeout", 3600),
                    check=False,
                    shell=False,  # 보안: shell injection 방지
                )

                if result.returncode != 0:
                    logger.error(f"벤치마크 실행 실패: {task_name}")
                    logger.error(f"stderr: {result.stderr}")
                    return {
                        "error": f"Command failed with return code {result.returncode}",
                        "stderr": result.stderr,
                        "stdout": result.stdout,
                    }

                # 결과 파일 읽기 (보안: 임시 디렉토리 내에서만 접근)
                results_file = output_path / "results.json"
                if results_file.exists():
                    with results_file.open(encoding="utf-8") as f:
                        benchmark_results = json.load(f)
                    logger.info(f"벤치마크 완료: {task_name}")
                    return benchmark_results
                else:
                    logger.warning(f"결과 파일을 찾을 수 없음: {results_file}")
                    return {"error": "Results file not found", "stdout": result.stdout}

        except subprocess.TimeoutExpired:
            logger.error(f"벤치마크 타임아웃: {task_name}")
            return {"error": "Timeout expired"}
        except Exception as e:
            logger.error(f"벤치마크 실행 중 오류: {task_name}, {e}")
            return {"error": str(e)}

    def run_evaluation(self) -> dict[str, Any]:
        """전체 평가 실행"""
        logger.info("API 기반 Evalchemy 평가 시작")

        config = self.load_config()
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_endpoint": self.model_endpoint,
            "config_file": str(self.config_file),
            "evaluation_mode": "api_based",
            "lm_eval_version": self.get_lm_eval_version(),
            "benchmarks": {},
        }

        # 활성화된 태스크만 실행
        tasks = config.get("tasks", {})
        if not isinstance(tasks, dict):
            raise ValueError("Config 'tasks' must be a dictionary")

        enabled_tasks = {
            name: task_config
            for name, task_config in tasks.items()
            if isinstance(task_config, dict) and task_config.get("enabled", False)
        }

        if not enabled_tasks:
            logger.warning("활성화된 태스크가 없습니다")
            return results

        logger.info(f"실행할 태스크: {list(enabled_tasks.keys())}")

        for task_name, task_config in enabled_tasks.items():
            try:
                benchmark_result = self.run_benchmark(task_name, task_config)
                results["benchmarks"][task_name] = benchmark_result
            except Exception as e:
                logger.error(f"태스크 실행 실패: {task_name}, {e}")
                results["benchmarks"][task_name] = {"error": str(e)}

        # 결과 저장 (보안: 경로 검증)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        if not str(self.output_file.resolve()).startswith("/results/"):
            logger.warning(f"Output file outside expected directory: {self.output_file}")

        with self.output_file.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"평가 완료. 결과 저장: {self.output_file}")
        return results

    def get_lm_eval_version(self) -> str:
        """lm-evaluation-harness 버전 정보 가져오기"""
        try:
            # 보안: git 명령어 절대 경로로 안전하게 실행
            result = subprocess.run(  # nosec B603 - subprocess with list is safe
                ["/usr/bin/git", "rev-parse", "HEAD"],  # 절대 경로 사용
                cwd=self.lm_eval_path,
                capture_output=True,
                text=True,
                check=False,
                shell=False,  # 보안: shell injection 방지
                timeout=GIT_TIMEOUT,  # 보안: 타임아웃 설정
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # 짧은 해시
        except Exception as e:
            logger.warning(f"Failed to get lm-eval version: {e}")
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="API 기반 Evalchemy 평가 실행기")
    parser.add_argument("--config", required=True, help="설정 파일 경로")
    parser.add_argument("--model-endpoint", required=True, help="모델 API 엔드포인트")
    parser.add_argument(
        "--output", default="/results/evalchemy_results.json", help="출력 파일 경로"
    )
    parser.add_argument("--debug", action="store_true", help="디버그 모드")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # 필수 환경 변수 확인
    if not args.model_endpoint:
        logger.error("MODEL_ENDPOINT가 설정되지 않았습니다")
        sys.exit(1)

    try:
        runner = EvAlchemyAPIRunner(args.config, args.model_endpoint, args.output)
        results = runner.run_evaluation()

        # 성공한 벤치마크 수 출력
        successful_benchmarks = sum(
            1 for result in results["benchmarks"].values() if "error" not in result
        )
        total_benchmarks = len(results["benchmarks"])

        logger.info(f"평가 완료: {successful_benchmarks}/{total_benchmarks} 벤치마크 성공")

        if successful_benchmarks == 0:
            sys.exit(1)

    except Exception as e:
        logger.error(f"평가 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# 🚀 macOS OrbStack 환경에서 VLLM 로컬 평가 가이드

이 문서는 macOS의 OrbStack 환경에서 VLLM 모델을 실행하고 LLM 평가를 수행하는 단계별 가이드입니다.

## 📋 목차

1. 🛠 사전 요구사항
2. 🔧 OrbStack 설치 및 설정
3. 🤖 VLLM 서버 실행
4. 🔬 평가 환경 구축
5. 🧪 Deepeval 평가 실행
6. 📚 Evalchemy 벤치마크 실행
7. 📈 결과 분석 및 시각화
8. 🚫 문제 해결

## 🛠 사전 요구사항

### 시스템 요구사항

- **macOS**: 13.0 이상 (Apple Silicon 권장)
- **RAM**: 최소 16GB, 권장 32GB
- **디스크**: 최소 20GB 여유 공간
- **GPU**: Apple Silicon GPU 또는 NVIDIA GPU (선택사항)

### 필수 도구 설치

```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 필수 도구들 설치
brew install python@3.11 git curl jq
```

## 🔧 OrbStack 설치 및 설정

### 1. OrbStack 설치

```bash
# OrbStack 설치 (Docker Desktop 대신 권장)
brew install --cask orbstack

# OrbStack 시작
open -a OrbStack

# OrbStack 시작 확인
while ! docker info > /dev/null 2>&1; do
    echo "OrbStack 시작 대기 중..."
    sleep 3
done
echo "✅ OrbStack이 성공적으로 시작되었습니다."
```

### 2. 프로젝트 클론 및 설정

```bash
# 프로젝트 클론
git clone https://github.com/your-org/vllm-eval.git
cd vllm-eval

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 필수 패키지 설치
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -r requirements-deepeval.txt
pip install -r requirements-evalchemy.txt
```

## 🤖 VLLM 서버 실행

### 1. 모델 다운로드 및 실행

```bash
# VLLM 서버 실행 (예: Qwen2-7B 모델)
docker run -d \
  --name vllm-server \
  --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model "Qwen/Qwen2-7B-Instruct" \
  --served-model-name "qwen3-8b" \
  --host 0.0.0.0 \
  --port 8000

# 서버 상태 확인
docker logs vllm-server

# API 테스트
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-8b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "한국의 수도는 어디인가요?"}
    ],
    "temperature": 0.7,
    "max_tokens": 256,
    "top_p": 0.95,
    "stream": false
  }'
```

### 2. 모델 서버 헬스체크

```bash
# 모델 목록 확인
curl http://localhost:8000/v1/models | jq

# 서버 상태 확인
curl http://localhost:8000/health
```

## 🔬 평가 환경 구축

### 1. 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << 'EOF'
# VLLM 모델 엔드포인트
VLLM_MODEL_ENDPOINT=http://localhost:8000/v1
MODEL_NAME=qwen3-8b

# 평가 설정
EVAL_CONFIG_PATH=configs/evalchemy.json
OUTPUT_DIR=./test_results
RUN_ID=local_eval_$(date +%Y%m%d_%H%M%S)

# 로그 설정
LOG_LEVEL=INFO
PYTHONPATH=.
EOF

# 환경 변수 로드
source .env
```

### 2. 테스트 데이터셋 준비

```bash
# 결과 디렉토리 생성
mkdir -p test_results

# 테스트용 데이터셋 생성
mkdir -p datasets/raw/local_test_dataset
cat > datasets/raw/local_test_dataset/test.jsonl << 'EOF'
{"input": "한국의 수도는 어디인가요?", "expected_output": "한국의 수도는 서울입니다.", "context": "한국 지리에 관한 질문입니다."}
{"input": "파이썬에서 리스트를 정렬하는 방법은?", "expected_output": "파이썬에서 리스트를 정렬하려면 sort() 메서드나 sorted() 함수를 사용할 수 있습니다.", "context": "프로그래밍 관련 질문입니다."}
{"input": "지구의 둘레는 얼마나 됩니까?", "expected_output": "지구의 둘레는 약 40,075km입니다.", "context": "지구과학에 관한 질문입니다."}
EOF
```

## 🧪 Deepeval 평가 실행

### 1. 커스텀 평가 스크립트 생성

```bash
# 로컬 평가 스크립트 생성
cat > scripts/run_local_deepeval.py << 'EOF'
#!/usr/bin/env python3
"""
로컬 VLLM 서버를 이용한 Deepeval 평가 스크립트
"""

import os
import json
import asyncio
from typing import List, Dict, Any
from deepeval import evaluate
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    AnswerRelevancyMetric
)
import openai
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VLLMModel(DeepEvalBaseLLM):
    """VLLM OpenAI 호환 API를 위한 모델 클래스"""
    
    def __init__(self, model_name: str = "qwen3-8b", base_url: str = "http://localhost:8000/v1"):
        self.model_name = model_name
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key="dummy"  # VLLM에서는 API 키가 필요없음
        )
    
    def load_model(self):
        return self.model_name
    
    def generate(self, prompt: str, schema: Dict = None) -> str:
        """텍스트 생성"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ""
    
    async def a_generate(self, prompt: str, schema: Dict = None) -> str:
        """비동기 텍스트 생성"""
        return self.generate(prompt, schema)
    
    def get_model_name(self) -> str:
        return self.model_name

def load_test_dataset(file_path: str) -> List[Dict[str, Any]]:
    """JSONL 테스트 데이터셋 로드"""
    test_cases = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            test_cases.append(json.loads(line.strip()))
    return test_cases

def create_test_cases(dataset: List[Dict], model: VLLMModel) -> List[LLMTestCase]:
    """테스트 케이스 생성"""
    test_cases = []
    
    for item in dataset:
        # 모델로부터 실제 응답 생성
        actual_output = model.generate(item["input"])
        
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=actual_output,
            expected_output=item["expected_output"],
            context=[item.get("context", "")]
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
        AnswerRelevancyMetric(
            threshold=0.7,
            model=model,
            include_reason=True
        ),
        ContextualRelevancyMetric(
            threshold=0.7,
            model=model,
            include_reason=True
        )
    ]
    
    # 평가 실행
    logger.info("Starting evaluation...")
    results = evaluate(
        test_cases=test_cases,
        metrics=metrics,
        print_results=True
    )
    
    # 결과 저장
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    results_file = f"{output_dir}/deepeval_results_{os.getenv('RUN_ID', 'local')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_results": [
                {
                    "input": tc.input,
                    "actual_output": tc.actual_output,
                    "expected_output": tc.expected_output,
                    "metrics": {
                        metric.__class__.__name__: {
                            "score": getattr(metric, 'score', None),
                            "threshold": getattr(metric, 'threshold', None),
                            "success": getattr(metric, 'success', None),
                            "reason": getattr(metric, 'reason', None)
                        }
                        for metric in metrics
                    }
                }
                for tc in test_cases
            ]
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Results saved to: {results_file}")
    return results

if __name__ == "__main__":
    main()
EOF

# 실행 권한 부여
chmod +x scripts/run_local_deepeval.py
```

### 2. Deepeval 실행

```bash
# Deepeval 평가 실행
python scripts/run_local_deepeval.py

# 결과 확인
ls -la test_results/
cat test_results/deepeval_results_*.json | jq
```

## ⚡ Evalchemy 벤치마크 실행

### 1. 로컬 Evalchemy 설정

```bash
# 로컬용 Evalchemy 설정 파일 생성
cat > eval/evalchemy/configs/local_eval_config.json << 'EOF'
{
  "benchmarks": {
    "arc_easy": {
      "enabled": true,
      "tasks": ["arc_easy"],
      "num_fewshot": 5,
      "batch_size": 4,
      "limit": 10,
      "description": "ARC Easy 벤치마크 (로컬 테스트용)",
      "metrics": ["acc", "acc_norm"]
    },
    "hellaswag": {
      "enabled": true,
      "tasks": ["hellaswag"],
      "num_fewshot": 10,
      "batch_size": 4,
      "limit": 10,
      "description": "HellaSwag 벤치마크 (로컬 테스트용)",
      "metrics": ["acc", "acc_norm"]
    }
  }
}
EOF
```

### 2. 로컬 Evalchemy 실행 스크립트

```bash
# 로컬 Evalchemy 실행 스크립트 생성
cat > scripts/run_local_evalchemy.py << 'EOF'
#!/usr/bin/env python3
"""
로컬 VLLM 서버를 이용한 Evalchemy 벤치마크 실행
"""

import os
import json
import subprocess
import logging
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_evalchemy_benchmark(config_path: str, output_dir: str) -> Dict[str, Any]:
    """Evalchemy 벤치마크 실행"""
    
    # 환경 변수 설정
    env = os.environ.copy()
    env.update({
        "VLLM_MODEL_ENDPOINT": "http://localhost:8000/v1",
        "MODEL_NAME": "qwen3-8b",
        "OUTPUT_DIR": output_dir,
        "EVAL_CONFIG_PATH": config_path
    })
    
    # lm_eval 명령어 구성
    cmd = [
        "lm_eval",
        "--model", "openai-chat-completions",
        "--model_args", f"base_url=http://localhost:8000/v1,model={env['MODEL_NAME']},tokenizer={env['MODEL_NAME']}",
        "--tasks", "arc_easy,hellaswag",
        "--num_fewshot", "5",
        "--batch_size", "4",
        "--limit", "10",
        "--output_path", f"{output_dir}/evalchemy_results.json",
        "--log_samples"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
        # 벤치마크 실행
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1시간 타임아웃
        )
        
        if result.returncode == 0:
            logger.info("Evalchemy benchmark completed successfully")
            
            # 결과 파일 읽기
            results_file = f"{output_dir}/evalchemy_results.json"
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    results = json.load(f)
                return results
            else:
                logger.warning("Results file not found")
                return {}
        else:
            logger.error(f"Benchmark failed with return code: {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return {}
            
    except subprocess.TimeoutExpired:
        logger.error("Benchmark timed out")
        return {}
    except Exception as e:
        logger.error(f"Benchmark failed with exception: {e}")
        return {}

def main():
    """메인 실행 함수"""
    config_path = "eval/evalchemy/configs/local_eval_config.json"
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 벤치마크 실행
    results = run_evalchemy_benchmark(config_path, output_dir)
    
    if results:
        logger.info("Benchmark results:")
        for task, metrics in results.get("results", {}).items():
            logger.info(f"  {task}: {metrics}")
    else:
        logger.error("No results obtained")

if __name__ == "__main__":
    main()
EOF

# 실행 권한 부여
chmod +x scripts/run_local_evalchemy.py
```

### 3. Evalchemy 실행

```bash
# lm-evaluation-harness 설치 (필요한 경우)
pip install lm-eval[openai]

# Evalchemy 벤치마크 실행
python scripts/run_local_evalchemy.py

# 결과 확인
ls -la test_results/
cat test_results/evalchemy_results.json | jq
```

## 📊 결과 분석 및 시각화

### 1. 결과 집계 스크립트

```bash
# 결과 집계 스크립트 생성
cat > scripts/aggregate_local_results.py << 'EOF'
#!/usr/bin/env python3
"""
로컬 평가 결과 집계 및 시각화
"""

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_deepeval_results(results_dir: str) -> dict:
    """Deepeval 결과 로드"""
    results = {}
    for file in os.listdir(results_dir):
        if file.startswith("deepeval_results_") and file.endswith(".json"):
            with open(os.path.join(results_dir, file), 'r') as f:
                results[file] = json.load(f)
    return results

def load_evalchemy_results(results_dir: str) -> dict:
    """Evalchemy 결과 로드"""
    results = {}
    for file in os.listdir(results_dir):
        if file.startswith("evalchemy_results") and file.endswith(".json"):
            with open(os.path.join(results_dir, file), 'r') as f:
                results[file] = json.load(f)
    return results

def create_summary_report(deepeval_results: dict, evalchemy_results: dict, output_dir: str):
    """통합 보고서 생성"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "model_name": os.getenv("MODEL_NAME", "unknown"),
        "summary": {
            "deepeval": {},
            "evalchemy": {}
        }
    }
    
    # Deepeval 결과 요약
    if deepeval_results:
        for filename, data in deepeval_results.items():
            test_results = data.get("test_results", [])
            if test_results:
                # 메트릭별 평균 계산
                metrics_summary = {}
                for result in test_results:
                    for metric_name, metric_data in result.get("metrics", {}).items():
                        if metric_name not in metrics_summary:
                            metrics_summary[metric_name] = []
                        if metric_data.get("score") is not None:
                            metrics_summary[metric_name].append(metric_data["score"])
                
                # 평균 계산
                avg_metrics = {}
                for metric_name, scores in metrics_summary.items():
                    if scores:
                        avg_metrics[metric_name] = {
                            "average_score": sum(scores) / len(scores),
                            "count": len(scores)
                        }
                
                report["summary"]["deepeval"][filename] = avg_metrics
    
    # Evalchemy 결과 요약
    if evalchemy_results:
        for filename, data in evalchemy_results.items():
            results = data.get("results", {})
            summary = {}
            for task, metrics in results.items():
                summary[task] = {
                    "accuracy": metrics.get("acc", 0),
                    "normalized_accuracy": metrics.get("acc_norm", 0)
                }
            report["summary"]["evalchemy"][filename] = summary
    
    # 보고서 저장
    report_file = f"{output_dir}/evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Summary report saved to: {report_file}")
    return report

def create_visualizations(report: dict, output_dir: str):
    """결과 시각화"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 스타일 설정
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Deepeval 결과 시각화
        deepeval_data = report["summary"]["deepeval"]
        if deepeval_data:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Local VLLM Evaluation Results - {report["model_name"]}', fontsize=16)
            
            # 메트릭별 점수 시각화
            all_scores = []
            all_metrics = []
            
            for filename, metrics in deepeval_data.items():
                for metric_name, metric_data in metrics.items():
                    all_scores.append(metric_data["average_score"])
                    all_metrics.append(metric_name.replace("Metric", ""))
            
            if all_scores:
                axes[0, 0].bar(all_metrics, all_scores)
                axes[0, 0].set_title('Deepeval Metrics Scores')
                axes[0, 0].set_ylabel('Score')
                axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Evalchemy 결과 시각화
        evalchemy_data = report["summary"]["evalchemy"]
        if evalchemy_data:
            tasks = []
            accuracies = []
            
            for filename, results in evalchemy_data.items():
                for task, metrics in results.items():
                    tasks.append(task)
                    accuracies.append(metrics["accuracy"])
            
            if tasks:
                axes[0, 1].bar(tasks, accuracies)
                axes[0, 1].set_title('Evalchemy Benchmark Accuracies')
                axes[0, 1].set_ylabel('Accuracy')
                axes[0, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        chart_file = f"{output_dir}/evaluation_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        logger.info(f"Charts saved to: {chart_file}")
        
    except ImportError:
        logger.warning("matplotlib/seaborn not installed, skipping visualization")
    except Exception as e:
        logger.error(f"Visualization failed: {e}")

def main():
    """메인 실행 함수"""
    output_dir = os.getenv("OUTPUT_DIR", "./test_results")
    
    # 결과 로드
    deepeval_results = load_deepeval_results(output_dir)
    evalchemy_results = load_evalchemy_results(output_dir)
    
    # 통합 보고서 생성
    report = create_summary_report(deepeval_results, evalchemy_results, output_dir)
    
    # 시각화
    create_visualizations(report, output_dir)
    
    # 콘솔 출력
    print("\n=== Local VLLM Evaluation Summary ===")
    print(f"Model: {report['model_name']}")
    print(f"Timestamp: {report['timestamp']}")
    
    if report["summary"]["deepeval"]:
        print("\n--- Deepeval Results ---")
        for filename, metrics in report["summary"]["deepeval"].items():
            print(f"File: {filename}")
            for metric_name, data in metrics.items():
                print(f"  {metric_name}: {data['average_score']:.3f} (n={data['count']})")
    
    if report["summary"]["evalchemy"]:
        print("\n--- Evalchemy Results ---")
        for filename, results in report["summary"]["evalchemy"].items():
            print(f"File: {filename}")
            for task, metrics in results.items():
                print(f"  {task}: {metrics['accuracy']:.3f}")

if __name__ == "__main__":
    main()
EOF

# 실행 권한 부여
chmod +x scripts/aggregate_local_results.py
```

### 2. 결과 집계 실행

```bash
# 시각화 라이브러리 설치
pip install matplotlib seaborn pandas

# 결과 집계 및 시각화
python scripts/aggregate_local_results.py

# 생성된 파일 확인
ls -la test_results/evaluation_*
```

## 🔧 통합 실행 스크립트

```bash
# 전체 로컬 평가 실행 스크립트 생성
cat > scripts/run_full_local_evaluation.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 로컬 VLLM 평가 시작"
echo "===================="

# 환경 변수 로드
source .env

# 1. VLLM 서버 상태 확인
echo "📡 VLLM 서버 상태 확인 중..."
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ VLLM 서버가 실행되지 않았습니다. 서버를 먼저 시작해주세요."
    exit 1
fi
echo "✅ VLLM 서버 정상 작동"

# 2. 결과 디렉토리 생성
mkdir -p $OUTPUT_DIR

# 3. Deepeval 실행
echo "🧪 Deepeval 평가 실행 중..."
python scripts/run_local_deepeval.py
echo "✅ Deepeval 완료"

# 4. Evalchemy 실행
echo "⚡ Evalchemy 벤치마크 실행 중..."
python scripts/run_local_evalchemy.py
echo "✅ Evalchemy 완료"

# 5. 결과 집계
echo "📊 결과 집계 및 시각화 중..."
python scripts/aggregate_local_results.py
echo "✅ 결과 집계 완료"

# 6. 결과 출력
echo ""
echo "🎉 로컬 VLLM 평가 완료!"
echo "===================="
echo "결과 파일 위치: $OUTPUT_DIR"
echo "주요 파일:"
echo "  - Deepeval 결과: $OUTPUT_DIR/deepeval_results_*.json"
echo "  - Evalchemy 결과: $OUTPUT_DIR/evalchemy_results.json"
echo "  - 통합 보고서: $OUTPUT_DIR/evaluation_summary_*.json"
echo "  - 시각화 차트: $OUTPUT_DIR/evaluation_charts_*.png"
EOF

# 실행 권한 부여
chmod +x scripts/run_full_local_evaluation.sh
```

## 🚨 문제 해결

### 1. VLLM 서버 관련 문제

```bash
# 서버 로그 확인
docker logs vllm-server

# 서버 재시작
docker restart vllm-server

# 포트 사용 확인
lsof -i :8000
```

### 2. Python 의존성 문제

```bash
# 가상환경 재생성
deactivate
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 3. 메모리 부족 문제

```bash
# Docker 메모리 제한 설정
docker run -d \
  --name vllm-server \
  --memory="8g" \
  --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model "Qwen/Qwen2-7B-Instruct" \
  --gpu-memory-utilization 0.8
```

### 4. 평가 결과가 나오지 않는 경우

```bash
# 로그 레벨 변경
export LOG_LEVEL=DEBUG

# 단계별 디버깅
python -c "
import openai
client = openai.OpenAI(base_url='http://localhost:8000/v1', api_key='dummy')
response = client.chat.completions.create(
    model='qwen3-8b',
    messages=[{'role': 'user', 'content': 'Hello!'}]
)
print(response.choices[0].message.content)
"
```

## 🎯 실행 요약

### 방법 1: 통합 스크립트 사용 (권장)

```bash
# 한 번에 모든 것을 실행 (VLLM 서버 자동 감지)
./scripts/run_complete_local_evaluation.sh
```

### 방법 2: 수동 단계별 실행

```bash
# 1. VLLM 서버 시작 (선택사항)
docker run -d \
  --name vllm-server \
  --gpus all \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model "Qwen/Qwen2-7B-Instruct" \
  --served-model-name "qwen3-8b"

# 2. 개별 테스트 실행
python scripts/run_simple_deepeval_test.py      # Mock 테스트
python scripts/run_vllm_deepeval_test.py        # 실제 VLLM 테스트

# 전체 평가 실행
python scripts/run_complete_local_evalchemy.py

# 개별 테스트 실행
python scripts/run_simple_deepeval_test.py
python scripts/run_simple_evalchemy_test.py

# 3. 결과 확인
cat test_results/*.json | jq
```

### 실행 결과 예시

```
🚀 macOS OrbStack VLLM 로컬 평가 통합 실행
=============================================
📋 1. 환경 확인
📋 2. 필수 패키지 확인
✅ 필수 패키지 확인 완료
📋 3. 결과 디렉토리 생성
✅ 결과 디렉토리 생성: ./test_results
📋 4. VLLM 서버 상태 확인
✅ VLLM 서버 발견: http://localhost:1234
📋 5. 실제 VLLM 서버로 평가 실행

📊 최종 결과:
  총 테스트: 5
  평균 점수: 0.50
  성공률: 50.0%

✅ 로컬 VLLM 평가가 완료되었습니다!
```

## 🎉 정리

이 가이드를 통해 macOS OrbStack 환경에서 VLLM 모델의 로컬 평가를 완전히 수행할 수 있습니다:

### 🔧 주요 기능
- **자동 환경 감지**: VLLM 서버 여러 포트 자동 탐지
- **Mock 모드 지원**: 서버 없이도 테스트 가능
- **통합 실행**: 한 번의 명령으로 전체 평가 수행
- **상세한 결과 분석**: JSON 형태의 구조화된 결과

### 📊 생성되는 결과 파일
- `simple_deepeval_results.json`: Mock 테스트 결과
- `vllm_deepeval_results.json`: VLLM 서버 테스트 결과

### 🚀 다음 단계
이 로컬 평가 시스템을 기반으로 다음과 같은 확장이 가능합니다:
- 커스텀 평가 메트릭 추가
- 다양한 모델 비교 평가
- 성능 벤치마크 확장
- CI/CD 파이프라인 통합 
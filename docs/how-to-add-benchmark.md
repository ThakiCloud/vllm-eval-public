# 🎯 벤치마크 추가 가이드

이 문서는 VLLM 평가 시스템에 새로운 벤치마크를 추가하는 방법을 설명합니다.

## 📋 목차

- [개요](#개요)
- [데이터셋 준비](#데이터셋-준비)
- [벤치마크 유형](#벤치마크-유형)
- [Deepeval 메트릭 추가](#deepeval-메트릭-추가)
- [Evalchemy 벤치마크 추가](#evalchemy-벤치마크-추가)
- [테스트 및 검증](#테스트-및-검증)
- [문제 해결](#문제-해결)

## 🎯 개요

VLLM 평가 시스템은 두 가지 평가 프레임워크를 지원합니다:

- **Deepeval**: 커스텀 메트릭 및 RAG 평가
- **Evalchemy**: 표준 벤치마크 및 대규모 평가

새로운 벤치마크를 추가할 때는 평가 목적과 특성에 따라 적절한 프레임워크를 선택해야 합니다.

## 📊 데이터셋 준비

### 1. JSONL 형식으로 데이터셋 생성

먼저 커스텀 데이터셋을 JSONL 형식으로 준비합니다:

```bash
# 데이터셋 디렉토리 생성
mkdir -p datasets/raw/custom_benchmark

# 훈련 데이터 생성 (train.jsonl)
cat > datasets/raw/custom_benchmark/train.jsonl << 'EOF'
{"question": "한국의 수도는 어디인가요?", "answer": "서울", "context": "한국은 동아시아에 위치한 국가입니다.", "category": "geography", "difficulty": "easy"}
{"question": "파이썬에서 리스트를 정렬하는 방법은?", "answer": "sort() 메서드나 sorted() 함수를 사용합니다.", "context": "파이썬은 다양한 정렬 방법을 제공합니다.", "category": "programming", "difficulty": "medium"}
{"question": "지구에서 가장 큰 대륙은?", "answer": "아시아", "context": "지구는 7개의 대륙으로 구성되어 있습니다.", "category": "geography", "difficulty": "easy"}
{"question": "HTTP와 HTTPS의 차이점은?", "answer": "HTTPS는 HTTP에 SSL/TLS 암호화가 추가된 프로토콜입니다.", "context": "웹 통신에서 보안은 매우 중요합니다.", "category": "technology", "difficulty": "medium"}
{"question": "셰익스피어의 대표작은?", "answer": "햄릿, 로미오와 줄리엣, 맥베스 등이 있습니다.", "context": "셰익스피어는 영국의 대표적인 극작가입니다.", "category": "literature", "difficulty": "medium"}
EOF

# 테스트 데이터 생성 (test.jsonl)
cat > datasets/raw/custom_benchmark/test.jsonl << 'EOF'
{"question": "일본의 수도는 어디인가요?", "answer": "도쿄", "context": "일본은 동아시아의 섬나라입니다.", "category": "geography", "difficulty": "easy"}
{"question": "자바스크립트에서 배열을 정렬하는 방법은?", "answer": "sort() 메서드를 사용합니다.", "context": "자바스크립트는 웹 개발의 핵심 언어입니다.", "category": "programming", "difficulty": "medium"}
{"question": "세계에서 가장 긴 강은?", "answer": "나일강", "context": "강은 지구의 중요한 수자원입니다.", "category": "geography", "difficulty": "medium"}
EOF
```

**JSONL 형식 설명**:
- **JSONL** = JSON Lines (각 줄마다 하나의 JSON 객체)
- 머신러닝 데이터셋의 표준 형식
- 대용량 데이터를 효율적으로 스트리밍 처리 가능

### 2. 매니페스트 파일 생성

```bash
mkdir -p datasets/manifests
cat > datasets/manifests/custom_benchmark_manifest.yaml << 'EOF'
name: "custom_benchmark"
version: "1.0"
description: "커스텀 벤치마크 데이터셋"
license: "MIT"
language: ["ko", "en"]
domain: "general"
task_type: "text_generation"

source:
  type: "local"
  path: "datasets/raw/custom_benchmark"

splits:
  train:
    file: "raw/custom_benchmark/train.jsonl"
    size: 5
    sha256: "계산된_해시값"
  test:
    file: "raw/custom_benchmark/test.jsonl"
    size: 3
    sha256: "계산된_해시값"

schema:
  input_field: "question"
  output_field: "answer"
  context_field: "context"
  metadata_fields: ["category", "difficulty"]

evaluation:
  evalchemy:
    enabled: true
    tasks: ["custom_task_1", "custom_task_2"]
EOF
```

## 🔍 벤치마크 유형

### Deepeval 적합 벤치마크
- **RAG 평가**: 검색 증강 생성 품질 측정
- **도메인 특화**: 특정 업무/도메인 성능 평가
- **커스텀 메트릭**: 비즈니스 요구사항에 맞춘 평가
- **소규모 데이터셋**: < 1,000 샘플

### Evalchemy 적합 벤치마크
- **표준 벤치마크**: MMLU, ARC, HellaSwag 등
- **대규모 평가**: > 1,000 샘플
- **다국어 지원**: 한국어, 영어 등 다양한 언어
- **GPU 집약적**: 대용량 모델 평가

## 🧪 Deepeval 메트릭 추가

### 1. 메트릭 클래스 생성

```bash
cat >> eval/deepeval_tests/metrics/custom_metric.py <<EOF
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from typing import Optional, List, Dict, Any
import asyncio

class CustomMetric(BaseMetric):
    """
    커스텀 평가 메트릭
    
    Args:
        threshold (float): 통과 기준 점수 (0.0 ~ 1.0)
        model (str): 평가에 사용할 모델명
        include_reason (bool): 평가 이유 포함 여부
    """
    
    def __init__(
        self,
        threshold: float = 0.7,
        model: Optional[str] = None,
        include_reason: bool = True,
        async_mode: bool = True
    ):
        self.threshold = threshold
        self.model = model
        self.include_reason = include_reason
        self.async_mode = async_mode
        
    def measure(self, test_case: LLMTestCase) -> float:
        """동기 평가 실행"""
        if self.async_mode:
            return asyncio.run(self.a_measure(test_case))
        return self._evaluate_sync(test_case)
    
    async def a_measure(self, test_case: LLMTestCase, _show_indicator: bool = True) -> float:
        """비동기 평가 실행"""
        return self._evaluate_sync(test_case)
    
    def _evaluate_sync(self, test_case: LLMTestCase) -> float:
        """실제 평가 로직 구현"""
        # 여기에 평가 로직을 구현합니다
        input_text = test_case.input
        actual_output = test_case.actual_output
        expected_output = test_case.expected_output
        
        # 예시: 간단한 유사도 계산
        score = self._calculate_similarity(actual_output, expected_output)
        
        # 메트릭 속성 설정
        self.score = score
        self.success = score >= self.threshold
        
        if self.include_reason:
            self.reason = self._generate_reason(score, self.threshold)
        
        return score
    
    def _calculate_similarity(self, actual: str, expected: str) -> float:
        """유사도 계산 로직"""
        # 실제 구현에서는 더 정교한 방법을 사용
        from difflib import SequenceMatcher
        return SequenceMatcher(None, actual, expected).ratio()
    
    def _generate_reason(self, score: float, threshold: float) -> str:
        """평가 이유 생성"""
        if score >= threshold:
            return f"✅ 점수 {score:.3f}로 기준 {threshold} 이상 달성"
        else:
            return f"❌ 점수 {score:.3f}로 기준 {threshold} 미달"
    
    def is_successful(self) -> bool:
        """평가 성공 여부 반환"""
        return self.success
    
    @property
    def __name__(self):
        return "Custom Metric"
EOF
```

### 2. 테스트 케이스 작성

```bash
cat >> eval/deepeval_tests/test_custom_metric.py <<EOF
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from .metrics.custom_metric import CustomMetric

class TestCustomMetric:
    """커스텀 메트릭 테스트"""
    
    @pytest.mark.parametrize("threshold", [0.5, 0.7, 0.9])
    def test_custom_metric_threshold(self, threshold):
        """다양한 임계값에서 메트릭 테스트"""
        test_case = LLMTestCase(
            input="테스트 입력",
            actual_output="실제 출력",
            expected_output="예상 출력"
        )
        
        metric = CustomMetric(threshold=threshold)
        assert_test(test_case, [metric])
    
    def test_custom_metric_dataset(self):
        """데이터셋 기반 평가 테스트"""
        dataset = EvaluationDataset(test_cases=[
            LLMTestCase(
                input="질문 1",
                actual_output="답변 1",
                expected_output="정답 1"
            ),
            LLMTestCase(
                input="질문 2", 
                actual_output="답변 2",
                expected_output="정답 2"
            )
        ])
        
        metric = CustomMetric(threshold=0.7)
        dataset.evaluate([metric])
        
        # 결과 검증
        assert len(dataset.test_cases) == 2
        for test_case in dataset.test_cases:
            assert hasattr(test_case, 'metrics_metadata')
EOF
```

### 3. 메트릭 등록

```bash
cat >> eval/deepeval_tests/metrics/__init__.py <<EOF
from .rag_precision import RAGPrecisionMetric
from .custom_metric import CustomMetric

# 사용 가능한 메트릭 목록
AVAILABLE_METRICS = {
    'rag_precision': RAGPrecisionMetric,
    'custom_metric': CustomMetric,
}

def get_metric(metric_name: str, **kwargs):
    """메트릭 팩토리 함수"""
    if metric_name not in AVAILABLE_METRICS:
        raise ValueError(f"Unknown metric: {metric_name}")
    
    return AVAILABLE_METRICS[metric_name](**kwargs)
EOF
```

## ⚡ Evalchemy 벤치마크 추가

Evalchemy에 새로운 벤치마크를 추가하는 과정은 3단계로 이루어집니다:
1.  **YAML 태스크 정의**: `lm-evaluation-harness`가 이해할 수 있는 YAML 형식으로 태스크를 정의합니다.
2.  **`eval_config.json` 등록**: 생성한 태스크를 중앙 설정 파일에 추가하여 관리합니다.
3.  **테스트 및 실행**: `run_evalchemy.sh` 스크립트를 사용하여 벤치마크를 실행하고 검증합니다.

### 1. 태스크 디렉토리 및 초기화 파일 생성

먼저 커스텀 태스크를 위한 디렉토리와 `lm-evaluation-harness`가 태스크를 인식하는 데 필요한 초기화 파일을 생성합니다. 이 작업은 처음에 한 번만 수행하면 됩니다.

```bash
# 태스크 디렉토리 생성 (eval/standard_evalchemy 내부에 위치)
mkdir -p eval/standard_evalchemy/tasks

# __init__.py 파일 생성 (태스크 인식을 위해 필요)
cat > eval/standard_evalchemy/tasks/__init__.py << 'EOF'
"""
커스텀 태스크 모듈

이 파일은 lm_eval이 이 디렉토리를 커스텀 태스크가 포함된
파이썬 패키지로 인식하도록 합니다. YAML 기반 태스크를 주로 사용하더라도
이 파일은 필요합니다.
"""
# 태스크 디렉토리임을 명시
__version__ = "1.0.0"
__author__ = "VLLM Eval Team"
EOF
```

### 2. YAML 태스크 정의 생성

`lm-evaluation-harness` v0.4+ 표준에 따라 YAML 파일로 새로운 태스크를 정의합니다.

```bash
# custom_task_1.yaml 생성
cat > eval/standard_evalchemy/tasks/custom_task_1.yaml << 'EOF'
task: custom_task_1
test_split: test
fewshot_split: train
doc_to_text: "질문: {{question}}\n답변:"
doc_to_target: "{{answer}}"
description: "커스텀 태스크 1 - 간단한 질문답변"
dataset_path: json
dataset_kwargs:
  data_files:
    train: "../../../datasets/raw/custom_benchmark/train.jsonl"
    test: "../../../datasets/raw/custom_benchmark/test.jsonl"
output_type: generate_until
generation_kwargs:
  until: ["\n", "질문:"]
  max_gen_toks: 256
filter_list:
  - name: "whitespace_cleanup"
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
metadata:
  version: 1.0
EOF
```

**주요 YAML 설정**:
- `task`: 태스크의 고유 이름. `eval_config.json`에서 이 이름을 사용합니다.
- `dataset_path`: `json`으로 설정하여ローカル JSON/JSONL 파일을 사용합니다.
- `dataset_kwargs`: 데이터 파일의 상대 경로를 지정합니다. **경로는 `eval/standard_evalchemy/` 디렉토리 기준**으로 작성해야 합니다.
- `doc_to_text`/`doc_to_target`: 모델에 입력될 프롬프트 형식과 정답 필드를 지정합니다.
- `metric_list`: 평가에 사용할 메트릭을 정의합니다.

### 3. `configs/eval_config.json`에 태스크 등록

YAML 파일을 생성한 후, `run_evalchemy.sh` 스크립트가 태스크를 인식하고 실행할 수 있도록 `eval/standard_evalchemy/configs/eval_config.json` 파일에 등록합니다.

```bash
# eval/standard_evalchemy/configs/eval_config.json 파일을 열어 "tasks" 섹션에 다음 내용을 추가합니다.
# "custom_task_1"은 yaml 파일의 'task' 필드와 일치해야 합니다.
```

**`eval/standard_evalchemy/configs/eval_config.json` 수정 예시:**
```json
{
  "benchmarks": {
    // ...
    "custom_eval_group": {
      "enabled": true,
      "description": "내가 만든 커스텀 벤치마크 그룹",
      "tasks": ["custom_task_1"]
    }
  },
  "tasks": {
    // ... 기존 태스크들 ...
    "custom_task_1": {
      "enabled": true,
      "tasks": ["custom_task_1"],
      "num_fewshot": 0,
      "batch_size": 1,
      "limit": null,
      "description": "커스텀 태스크 1 - 간단한 질문답변"
    }
  }
}
```
- **`tasks` 섹션**: `custom_task_1`이라는 새 항목을 추가합니다. 여기서 키 값(`"custom_task_1"`)은 `run_evalchemy.sh` 스크립트 내에서 참조하는 이름이 됩니다. 내부의 `"tasks"` 배열에 있는 `custom_task_1`은 YAML 파일에 정의된 `task` 이름입니다.
- **`benchmarks` 섹션 (선택 사항)**: 여러 태스크를 `custom_eval_group`과 같이 논리적인 그룹으로 묶어 한 번에 실행할 수 있습니다. `enabled: true`로 설정해야 실행됩니다.

## 🧪 테스트 및 검증

새롭게 추가한 벤치마크가 올바르게 동작하는지 확인합니다. 모든 테스트는 `eval/standard_evalchemy` 디렉토리에서 실행하는 것을 기준으로 합니다.

### 1. 설정 파일 및 태스크 유효성 검사

```bash
# 작업 디렉토리로 이동
cd eval/standard_evalchemy

# 설정 파일(eval_config.json)이 유효한 JSON인지 확인
jq empty configs/eval_config.json && echo "✅ eval_config.json is valid"

# 추가한 커스텀 태스크가 lm-evaluation-harness에 의해 인식되는지 확인
# --tasks list 옵션으로 전체 태스크 목록을 확인하고 custom_task_1이 포함되어 있는지 검사합니다.
./run_evalchemy.sh --tasks list | grep custom_task_1
```
> **참고**: `run_evalchemy.sh`는 내부적으로 `lm_eval` 실행 시 `--include_path tasks` 옵션을 자동으로 추가하여 `tasks/` 디렉토리의 커스텀 태스크를 읽어옵니다.

### 2. Dry Run으로 실행 인수 확인

실제 평가를 실행하기 전에, `run_evalchemy.sh`가 생성하는 `lm_eval` 명령어가 올바른지 `--dry-run` 옵션으로 확인합니다.

```bash
# --dry-run 옵션을 사용하여 실제 실행 없이 생성되는 명령어만 출력
# --run-id는 결과가 저장될 디렉토리 이름이므로 테스트 목적에 맞게 지정합니다.
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --run-id test_custom_task_dry_run --dry-run
```

### 3. 소량 샘플로 테스트 실행

`limit` 옵션을 사용하여 적은 수의 샘플로 빠르게 테스트를 완료하고 전체 파이프라인이 정상적으로 동작하는지 확인합니다.

`configs/eval_config.json`에서 `limit` 값을 `5` 정도로 설정합니다.
```json
// ...
    "custom_task_1": {
      "enabled": true,
      "tasks": ["custom_task_1"],
      "limit": 5, // 5개 샘플만 테스트
// ...
```

테스트 실행:
```bash
# 실제 평가 실행 (5개 샘플)
# --batch-size 1은 안정적인 테스트를 위해 권장됩니다.
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --run-id test_custom_task_limit5 --batch-size 1

# 실행 후 결과 확인
cat results/test_custom_task_limit5/evalchemy_summary_test_custom_task_limit5.json | jq
```

### 4. 전체 데이터셋으로 실제 평가 실행

테스트가 성공적으로 완료되면, `limit` 값을 `null`로 변경하여 전체 데이터셋에 대한 평가를 진행합니다.

`configs/eval_config.json`에서 `limit` 값을 `null`로 변경합니다.
```json
// ...
    "custom_task_1": {
      "enabled": true,
      "tasks": ["custom_task_1"],
      "limit": null, // 전체 데이터셋 사용
// ...
```

실행:
```bash
# 프로덕션용 실행
./run_evalchemy.sh --endpoint http://your-vllm-server:8000/v1/completions --run-id custom_task_full_eval_$(date +%Y%m%d)
```
- `run_evalchemy.sh` 스크립트는 이미 `--include_path tasks` 옵션이 포함되어 있어 커스텀 태스크를 자동으로 인식합니다.

## 🔧 문제 해결 (Troubleshooting)

### 1. lm_eval이 커스텀 태스크를 인식하지 못하는 경우

**증상**: `Task 'custom_task_1' not found` 에러

**해결 방법**:
```bash
# 1단계: 작업 디렉토리 확인
# eval/standard_evalchemy 디렉토리에서 실행해야 합니다.
pwd

# 2단계: 태스크 목록 확인
./run_evalchemy.sh --tasks list | grep custom_task_1

# 3단계: YAML 파일 구문 검사
python3 -c "import yaml; print(yaml.safe_load(open('tasks/custom_task_1.yaml')))"

# 4단계: 태스크 디렉토리 구조 확인
ls -la tasks/
# 다음 파일들이 있어야 함:
# - __init__.py
# - custom_task_1.yaml
```

### 2. 데이터셋 로딩 에러

**증상**: `Dataset 'custom_dataset' doesn't exist on the Hub` 또는 `FileNotFoundError`

**원인**: YAML 파일에서 잘못된 데이터셋 경로 참조

**해결 방법**:
```bash
# 1단계: YAML 파일의 dataset_kwargs 경로 확인
# 경로는 eval/standard_evalchemy 디렉토리를 기준으로 한 상대 경로여야 합니다.
cat tasks/custom_task_1.yaml | grep -A 2 data_files

# 2단계: 실제 파일 존재 확인
ls -la ../../../datasets/raw/custom_benchmark/
# train.jsonl과 test.jsonl이 있어야 함
```

### 3. macOS에서 CUDA 에러

**증상**: `AssertionError: Torch not compiled with CUDA enabled`

**해결 방법**:
- `run_evalchemy.sh` 스크립트는 macOS 환경을 자동으로 감지하고 `--device cpu` 옵션을 추가합니다. 만약 스크립트를 사용하지 않고 직접 `lm_eval`을 실행한다면 `--device cpu` 옵션을 명시적으로 추가해야 합니다.

```bash
# 스크립트 사용 시 자동으로 처리됨
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions

# 직접 실행 시
python3 -m lm_eval --device cpu ...
```

### 4. YAML 파일 split 에러

**증상**: `KeyError: 'test'` 또는 `KeyError: 'validation'`

**원인**: 데이터셋에 해당 split이 없거나, JSONL 파일의 키가 잘못 지정됨

**해결 방법**:
```bash
# 1단계: JSONL 파일 내용 확인 (키가 'train', 'test'로 되어 있는지)
# 2단계: YAML 파일에서 올바른 split 사용 (test_split: test)
# 3단계: 사용 가능한 split 확인
python3 -c "
import datasets
ds = datasets.load_dataset('json', data_files={'train': '../../../datasets/raw/custom_benchmark/train.jsonl', 'test': '../../../datasets/raw/custom_benchmark/test.jsonl'})
print('Available splits:', list(ds.keys()))
"
# 위 코드는 eval/standard_evalchemy 디렉토리에서 실행해야 합니다.
```

### 5. 결과 파일이 생성되지 않을 때

**증상**: `results/{run_id}` 디렉토리는 생성되었지만 내용이 비어있음

**원인**: VLLM 엔드포인트 연결 실패, 모델 추론 실패 등

**해결 방법**:
```bash
# 1단계: 에러 로그 확인
cat results/{run_id}/evalchemy_errors_{run_id}.log

# 2단계: VLLM 서버 상태 및 엔드포인트 URL 확인
curl http://your-vllm-server:8000/v1/models

# 3단계: --log-level DEBUG 옵션으로 상세 로그 확인
./run_evalchemy.sh --endpoint ... --log-level DEBUG
```

## 📚 참고 자료

- [lm-evaluation-harness v0.4+ Documentation](https://github.com/EleutherAI/lm-evaluation-harness)
- [Deepeval Documentation](https://docs.confident-ai.com/)
- [VLLM Documentation](https://docs.vllm.ai/)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)

## 🤝 기여하기

새로운 벤치마크를 추가한 후에는:

1. **문서 업데이트**: 이 가이드와 README 업데이트
2. **테스트 추가**: 충분한 단위 테스트 및 통합 테스트 작성
3. **PR 생성**: 상세한 설명과 함께 Pull Request 생성
4. **리뷰 요청**: 팀 멤버들의 코드 리뷰 요청

질문이나 도움이 필요하면 이슈를 생성하거나 팀 채널에 문의해 주세요! 🚀

**주의사항**:
- 방법 1: 전체 태스크 목록에서 `custom_task_1`, `custom_task_2`가 보이면 성공
- 방법 2: macOS에서는 반드시 `--device cpu` 옵션 필요 (CUDA 미지원)
- `--limit 2`는 테스트용이므로 실제 평가에서는 제거해야 함
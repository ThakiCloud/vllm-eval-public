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

### 1. 태스크 디렉토리 및 초기화 파일 생성

먼저 커스텀 태스크를 위한 디렉토리와 필요한 파일들을 생성합니다:

```bash
# 태스크 디렉토리 생성
mkdir -p eval/evalchemy/tasks

# __init__.py 파일 생성 (태스크 인식을 위해 필요)
cat > eval/evalchemy/tasks/__init__.py << 'EOF'
"""
커스텀 태스크 모듈

이 파일은 lm_eval이 커스텀 태스크를 인식할 수 있도록 하는 초기화 파일입니다.
YAML 기반 태스크 정의를 사용하는 경우에도 이 파일이 있어야 합니다.
"""

# 태스크 디렉토리임을 명시
__version__ = "1.0.0"
__author__ = "VLLM Eval Team"
EOF
```

### 2. YAML 태스크 정의 생성

최신 lm_eval (v0.4+)에서는 YAML 파일로 태스크를 정의합니다:

```bash
# custom_task_1.yaml 생성
cat > eval/evalchemy/tasks/custom_task_1.yaml << 'EOF'
task: custom_task_1
test_split: test
fewshot_split: train
fewshot_config:
  sampler: first_n
doc_to_text: "질문: {{question}}\n답변:"
doc_to_target: "{{answer}}"
description: "커스텀 태스크 1 - 질문답변 평가"
dataset_path: json
dataset_kwargs:
  data_files:
    train: "../../datasets/raw/custom_benchmark/train.jsonl"
    test: "../../datasets/raw/custom_benchmark/test.jsonl"
output_type: generate_until
generation_kwargs:
  until: ["\n"]
  max_gen_toks: 100
filter_list:
  - name: "whitespace_cleanup"
    filter:
      - function: "regex"
        regex_pattern: "^\\s*(.*)$"
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
metadata:
  version: 1.0
EOF

# custom_task_2.yaml 생성 (선택사항)
cat > eval/evalchemy/tasks/custom_task_2.yaml << 'EOF'
task: custom_task_2
test_split: test
fewshot_split: train
fewshot_config:
  sampler: first_n
doc_to_text: "질문: {{question}}\n답변:"
doc_to_target: "{{answer}}"
description: "커스텀 태스크 2 - 질문답변 평가"
dataset_path: json
dataset_kwargs:
  data_files:
    train: "../../datasets/raw/custom_benchmark/train.jsonl"
    test: "../../datasets/raw/custom_benchmark/test.jsonl"
output_type: generate_until
generation_kwargs:
  until: ["\n"]
  max_gen_toks: 100
filter_list:
  - name: "whitespace_cleanup"
    filter:
      - function: "regex"
        regex_pattern: "^\\s*(.*)$"
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
metadata:
  version: 1.0
EOF
```

**주요 설정 설명**:
- `dataset_path: json`: JSON/JSONL 파일 사용
- `dataset_kwargs`: 데이터 파일 경로 지정
- `doc_to_text`: 입력 프롬프트 템플릿
- `doc_to_target`: 정답 추출 방법
- `exact_match`: 정확히 일치하는지 평가하는 메트릭

## 🧪 테스트 및 검증

### 1. 커스텀 태스크 인식 확인

```bash
cd eval/evalchemy
python3 -m lm_eval --include_path tasks --tasks list | grep custom
```

### 2. 단위 테스트 실행

```bash
# Deepeval 메트릭 테스트
cd ../..
python3 -m pytest eval/deepeval_tests/test_custom_metric.py -v

# Evalchemy 태스크 테스트 (실제 모델 필요)
cd eval/evalchemy
python3 -m lm_eval --include_path tasks --model hf --model_args pretrained=gpt2 --tasks custom_task_1 --limit 2 --device cpu
```

### 3. 실제 운영 환경에서 실행

```bash
# VLLM 서버와 함께 실행 - root 폴더에서 명령어 실행을 위한 cd ../..
cd ../..
./run_evalchemy.sh --endpoint http://your-vllm-server:8000/v1/completions
```

`run_evalchemy.sh` 스크립트는 이미 `--include_path tasks` 옵션이 포함되어 있어 커스텀 태스크를 자동으로 인식합니다.

### 6. 문제 해결

#### ./run_evalchemy.sh 실행 시 task 인식 안됨
```bash
# 루트 폴더로 이동
```

#### 태스크 인식 안됨
```bash
# 해결: --include_path 확인
python3 -m lm_eval --include_path tasks --tasks list

# YAML 문법 검사
python3 -c "import yaml; print(yaml.safe_load(open('tasks/custom_task_1.yaml')))"
```

#### macOS CUDA 에러
```bash
# CPU 모드 사용
python3 -m lm_eval --include_path tasks --model hf --model_args pretrained=gpt2 --tasks custom_task_1 --device cpu
```

#### 데이터셋 경로 에러
```bash
# 해결: 상대 경로 확인
ls -la ../../datasets/raw/custom_benchmark/
```

#### 답변 공백 문제
```bash
# 해결: " 도쿄"와 같이 앞에 공백이 추가된 경우 yaml파일에 해당 내용 추가
filter_list:
  - name: "whitespace_cleanup"
    filter:
      - function: "regex"
        regex_pattern: "^\\s*(.*)$"
```

## 🔧 문제 해결 (Troubleshooting)

### 1. lm_eval이 커스텀 태스크를 인식하지 못하는 경우

**증상**: `Task 'custom_task_1' not found` 에러

**해결 방법**:
```bash
# 1단계: --include_path 확인
cd eval/evalchemy
python3 -m lm_eval --include_path tasks --tasks list | grep custom

# 2단계: YAML 파일 구문 검사
python3 -c "import yaml; print(yaml.safe_load(open('tasks/custom_task_1.yaml')))"

# 3단계: 태스크 디렉토리 구조 확인
ls -la tasks/
# 다음 파일들이 있어야 함:
# - custom_task_1.yaml
# - custom_task_2.yaml
```

### 2. 데이터셋 로딩 에러

**증상**: `Dataset 'custom_dataset' doesn't exist on the Hub`

**원인**: YAML 파일에서 잘못된 데이터셋 경로 참조

**해결 방법**:
```bash
# 1단계: 데이터 파일 존재 확인
ls -la ../../datasets/raw/custom_benchmark/
# train.jsonl과 test.jsonl이 있어야 함

# 2단계: YAML 설정 확인
cat tasks/custom_task_1.yaml | grep -A 5 dataset_path
# 다음과 같이 설정되어야 함:
# dataset_path: json
# dataset_kwargs:
#   data_files:
#     train: "../../datasets/raw/custom_benchmark/train.jsonl"
#     test: "../../datasets/raw/custom_benchmark/test.jsonl"
```

### 3. macOS에서 CUDA 에러

**증상**: `AssertionError: Torch not compiled with CUDA enabled`

**해결 방법**:
```bash
# 항상 --device cpu 옵션 사용
python3 -m lm_eval --device cpu

# 2단계: 배치 크기 줄이기
python3 -m lm_eval --batch_size 1

# 3단계: 작은 모델 사용
python3 -m lm_eval --model hf --model_args pretrained=distilgpt2
```

### 4. YAML 파일 split 에러

**증상**: `KeyError: 'test'` 또는 `KeyError: 'validation'`

**원인**: 데이터셋에 해당 split이 없음

**해결 방법**:
```bash
# 1단계: 사용 가능한 split 확인
python3 -c "
import datasets
ds = datasets.load_dataset('json', data_files={'train': '../../datasets/raw/custom_benchmark/train.jsonl', 'test': '../../datasets/raw/custom_benchmark/test.jsonl'})
print('Available splits:', list(ds.keys()))
"

# 2단계: YAML 파일에서 올바른 split 사용
# test_split: test  (또는 validation)
```

### 5. 메트릭 계산 에러

**증상**: `TypeError: unsupported operand type(s) for +: 'int' and 'list'`

**원인**: BLEU 같은 복잡한 메트릭에서 데이터 타입 불일치

**해결 방법**:
```yaml
# 간단한 메트릭만 사용
metric_list:
  - metric: exact_match
    aggregation: mean
    higher_is_better: true
# BLEU 메트릭 제거
```

### 6. 경로 문제

**증상**: `FileNotFoundError: [Errno 2] No such file or directory`

**해결 방법**:
```bash
# 1단계: 현재 작업 디렉토리 확인
pwd
# /path/to/vllm-eval/eval/evalchemy 이어야 함

# 2단계: 상대 경로 확인
ls -la ../../datasets/raw/custom_benchmark/

# 3단계: 절대 경로 사용 (필요시)
# YAML 파일에서 절대 경로로 변경
```

### 7. 권한 문제

**증상**: `PermissionError: [Errno 13] Permission denied`

**해결 방법**:
```bash
# 파일 권한 확인 및 수정
chmod 644 datasets/raw/custom_benchmark/*.jsonl
chmod 644 eval/evalchemy/tasks/*.yaml
```

### 8. 메모리 부족

**증상**: `RuntimeError: CUDA out of memory` 또는 시스템 메모리 부족

**해결 방법**:
```bash
# 1단계: CPU 모드 사용
python3 -m lm_eval --device cpu

# 2단계: 배치 크기 줄이기
python3 -m lm_eval --batch_size 1

# 3단계: 작은 모델 사용
python3 -m lm_eval --model hf --model_args pretrained=distilgpt2
```

### 9. 네트워크 연결 문제

**증상**: 모델 다운로드 실패

**해결 방법**:
```bash
# 1단계: 인터넷 연결 확인
ping huggingface.co

# 2단계: 프록시 설정 (필요시)
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port

# 3단계: 캐시 디렉토리 확인
export HF_HOME=/path/to/cache
```

### 10. 일반적인 디버깅 팁

```bash
# 1. 상세 로그 출력
export LOGLEVEL=DEBUG
python3 -m lm_eval --include_path tasks --tasks custom_task_1 --limit 1

# 2. Python 경로 확인
python3 -c "import sys; print('\n'.join(sys.path))"

# 3. 패키지 버전 확인
pip list | grep -E "(lm-eval|datasets|transformers|torch)"

# 4. 단계별 테스트
# 4-1. 태스크 목록 확인
python3 -m lm_eval --include_path tasks --tasks list

# 4-2. 설정 확인
python3 -m lm_eval --include_path tasks --tasks custom_task_1 --help

# 4-3. 최소 실행
python3 -m lm_eval --include_path tasks --model hf --model_args pretrained=gpt2 --tasks custom_task_1 --limit 1 --device cpu
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
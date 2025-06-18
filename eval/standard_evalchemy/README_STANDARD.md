# Evalchemy 벤치마크 관리 가이드

## 개요

`run_evalchemy.sh`는 VLLM 모델의 성능을 평가하기 위한 lm-evaluation-harness 기반 벤치마크 실행 스크립트입니다. 이 가이드는 벤치마크와 태스크를 추가, 제거, 활성화, 비활성화하는 방법을 설명합니다.

## 기본 실행 방법

```bash
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --batch-size 1 --run-id test_macos_run
```

### Run ID란?

`--run-id`는 각 평가 실행을 고유하게 식별하는 식별자입니다:

- **목적**: 여러 평가 실행 결과를 구분하고 추적
- **기본값**: `YYYYMMDD_HHMMSS_PID` 형식 (예: `20240315_143022_12345`)
- **사용처**: 
  - 결과 파일 저장 디렉토리명
  - 로그 파일명
  - 결과 요약 파일의 식별자
- **예시**: `test_macos_run`, `production_v1.2`, `debug_session_001`

## 설정 파일 구조

벤치마크 설정은 `configs/eval_config.json` 파일에서 관리됩니다:

```json
{
  "benchmarks": {
    "benchmark_name": {
      "enabled": true/false,
      "description": "벤치마크 설명",
      "tasks": ["task1", "task2"]
    }
  },
  "tasks": {
    "task_name": {
      "enabled": true/false,
      "tasks": ["specific_task"],
      "num_fewshot": 5,
      "batch_size": 1,
      "limit": 1,
      "description": "태스크 설명"
    }
  }
}
```

## 벤치마크 관리

### 1. 벤치마크 목록 확인

```bash
# 현재 설정된 벤치마크 목록 확인
./run_evalchemy.sh --list-benchmarks

# 특정 설정 파일의 벤치마크 확인
./run_evalchemy.sh --list-benchmarks --config custom_config.json
```

### 2. 벤치마크 활성화/비활성화

`configs/eval_config.json` 파일에서 `benchmarks` 섹션을 수정합니다:

```json
{
  "benchmarks": {
    "arc_easy": {
      "enabled": true,     // ← 이 부분을 true로 변경하면 활성화
      "description": "AI2 Reasoning Challenge (Easy)",
      "tasks": ["arc_easy"]
    },
    "arc_challenge": {
      "enabled": true,     // ← 활성화
      "description": "AI2 Reasoning Challenge (Challenge)",
      "tasks": ["arc_challenge"]
    },
    "hellaswag": {
      "enabled": true,     // ← 활성화
      "description": "HellaSwag - Commonsense reasoning",
      "tasks": ["hellaswag"]
    },
    "mmlu": {
      "enabled": false,    // ← 이 부분을 false로 변경하면 비활성화
      "description": "Massive Multitask Language Understanding",
      "tasks": ["mmlu"]
    }
  }
}
```

**수정 방법:**
1. `configs/eval_config.json` 파일을 텍스트 에디터로 열기
2. `"benchmarks"` 섹션에서 원하는 벤치마크 찾기
3. `"enabled": true` (활성화) 또는 `"enabled": false` (비활성화)로 변경
4. 파일 저장

### 3. 새로운 벤치마크 추가

`configs/eval_config.json` 파일의 `benchmarks` 섹션에 새로운 벤치마크를 추가합니다:

```json
{
  "benchmarks": {
    // ... 기존 벤치마크들 ...
    "new_benchmark": {              // ← 새로운 벤치마크 이름
      "enabled": true,              // ← 활성화 상태
      "description": "새로운 벤치마크 설명",  // ← 설명
      "tasks": ["new_task_name"]    // ← 실행할 태스크 목록
    }
  }
}
```

**추가 방법:**
1. `configs/eval_config.json` 파일 열기
2. `"benchmarks"` 섹션 끝부분에 콤마(,) 추가
3. 위 형식으로 새로운 벤치마크 블록 추가
4. 파일 저장

### 4. 벤치마크 제거

`configs/eval_config.json` 파일에서 해당 벤치마크 블록을 삭제합니다:

**제거 방법:**
1. `configs/eval_config.json` 파일 열기
2. `"benchmarks"` 섹션에서 제거할 벤치마크 블록 전체 삭제
3. 앞뒤 콤마(,) 정리하여 JSON 문법 오류 방지
4. 파일 저장

## 태스크 관리

### 1. 태스크 활성화/비활성화

`configs/eval_config.json` 파일에서 `tasks` 섹션을 수정합니다:

```json
{
  "tasks": {
    "arc_easy": {
      "enabled": true,     // ← 이 부분을 true로 변경하면 활성화
      "tasks": ["arc_easy"],
      "num_fewshot": 25,
      "batch_size": 1,
      "limit": 1,
      "description": "AI2 Reasoning Challenge (Easy)"
    },
    "arc_challenge": {
      "enabled": true,     // ← 활성화
      "tasks": ["arc_challenge"],
      "num_fewshot": 25,
      "batch_size": 1,
      "limit": 1
    },
    "hellaswag": {
      "enabled": true,     // ← 활성화
      "tasks": ["hellaswag"],
      "num_fewshot": 10,
      "batch_size": 1,
      "limit": 1
    },
    "gsm8k": {
      "enabled": false,    // ← 이 부분을 false로 변경하면 비활성화
      "tasks": ["gsm8k"],
      "num_fewshot": 5,
      "batch_size": 1,
      "limit": 1
    }
  }
}
```

**수정 방법:**
1. `configs/eval_config.json` 파일을 텍스트 에디터로 열기
2. `"tasks"` 섹션에서 원하는 태스크 찾기
3. `"enabled": true` (활성화) 또는 `"enabled": false` (비활성화)로 변경
4. 파일 저장

### 2. 새로운 태스크 추가

`configs/eval_config.json` 파일의 `tasks` 섹션에 새로운 태스크를 추가합니다:

```json
{
  "tasks": {
    // ... 기존 태스크들 ...
    "new_task": {                           // ← 새로운 태스크 이름
      "enabled": true,                      // ← 활성화 상태
      "tasks": ["new_specific_task"],       // ← 실행할 구체적인 태스크명
      "num_fewshot": 5,                     // ← Few-shot 예제 개수
      "batch_size": 1,                      // ← 배치 크기
      "limit": 10,                          // ← 테스트할 샘플 수 (null이면 전체)
      "description": "새로운 태스크 설명",      // ← 태스크 설명
      "metrics": ["acc"],                   // ← 평가 메트릭
      "output_path": "results/new_task",    // ← 결과 저장 경로
      "log_samples": true,                  // ← 샘플 로그 저장 여부
      "priority": "medium",                 // ← 우선순위
      "timeout": 1800                       // ← 타임아웃 (초)
    }
  }
}
```

**추가 방법:**
1. `configs/eval_config.json` 파일 열기
2. `"tasks"` 섹션 끝부분에 콤마(,) 추가
3. 위 형식으로 새로운 태스크 블록 추가
4. 파일 저장

### 3. 태스크 설정 수정

`configs/eval_config.json` 파일에서 각 태스크의 설정값을 직접 수정합니다:

#### 주요 설정 항목들:

```json
{
  "tasks": {
    "arc_easy": {
      "enabled": true,
      "tasks": ["arc_easy"],
      "num_fewshot": 25,        // ← Few-shot 예제 개수 (0~25)
      "batch_size": 1,          // ← 배치 크기 (1, 4, 8 등)
      "limit": 1,               // ← 테스트 샘플 수 (1=빠른테스트, null=전체)
      "timeout": 1800           // ← 타임아웃 (초)
    }
  }
}
```

#### 자주 수정하는 설정들:

**1. 빠른 테스트를 위한 limit 설정:**
- `"limit": 1` → 1개 샘플만 테스트 (빠른 테스트용)
- `"limit": 10` → 10개 샘플 테스트
- `"limit": null` → 전체 데이터셋 테스트 (프로덕션용)

**2. Few-shot 예제 개수 조정:**
- `"num_fewshot": 0` → Zero-shot (예제 없음)
- `"num_fewshot": 5` → 5개 예제 제공
- `"num_fewshot": 25` → 25개 예제 제공

**3. 성능 조정:**
- `"batch_size": 1` → 안전한 설정 (메모리 부족 시)
- `"batch_size": 4` → 균형잡힌 설정
- `"batch_size": 8` → 고성능 설정

**수정 방법:**
1. `configs/eval_config.json` 파일 열기
2. `"tasks"` 섹션에서 수정할 태스크 찾기
3. 원하는 설정값 변경
4. 파일 저장

### 4. 태스크 제거

`configs/eval_config.json` 파일에서 해당 태스크 블록을 삭제합니다:

**제거 방법:**
1. `configs/eval_config.json` 파일 열기
2. `"tasks"` 섹션에서 제거할 태스크 블록 전체 삭제
3. 앞뒤 콤마(,) 정리하여 JSON 문법 오류 방지
4. 파일 저장

## 실행 옵션

### 기본 실행

```bash
# 기본 설정으로 실행
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions

# 배치 크기 조정
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --batch-size 1

# 커스텀 Run ID 사용
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --run-id my_evaluation_run
```

### 고급 실행 옵션

```bash
# 커스텀 설정 파일 사용
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --config custom_eval_config.json \
    --run-id custom_run

# 출력 디렉토리 지정
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --output /path/to/results \
    --run-id production_eval

# GPU 설정 (Linux에서만)
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --gpu 0 \
    --batch-size 8

# 고성능 설정
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --batch-size 16 \
    --max-length 4096 \
    --run-id high_performance_eval
```

### 검증 및 디버깅

```bash
# 설정 파일 검증
./run_evalchemy.sh --validate-config

# 드라이런 (실제 실행 없이 명령어만 확인)
./run_evalchemy.sh --dry-run --endpoint http://localhost/vllm/v1/completions

# 디버그 로그 레벨
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --log-level DEBUG \
    --run-id debug_session
```

## 실용적인 사용 예시

### 1. 빠른 테스트용 설정

**설정 파일 수정:**
`configs/eval_config.json`에서 모든 활성화된 태스크의 `limit` 값을 1로 변경:

```json
{
  "tasks": {
    "arc_easy": {
      "enabled": true,
      "limit": 1        // ← 1로 변경 (빠른 테스트)
    },
    "arc_challenge": {
      "enabled": true,
      "limit": 1        // ← 1로 변경
    },
    "hellaswag": {
      "enabled": true,
      "limit": 1        // ← 1로 변경
    }
  }
}
```

**실행:**
```bash
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --run-id quick_test
```

### 2. 특정 벤치마크만 실행

**설정 파일 수정:**
`configs/eval_config.json`에서 원하는 벤치마크만 활성화:

```json
{
  "benchmarks": {
    "arc_easy": {
      "enabled": true     // ← 실행할 벤치마크
    },
    "arc_challenge": {
      "enabled": false    // ← 비활성화
    },
    "hellaswag": {
      "enabled": true     // ← 실행할 벤치마크
    },
    "mmlu": {
      "enabled": false    // ← 비활성화
    }
  }
}
```

**실행:**
```bash
./run_evalchemy.sh --endpoint http://localhost/vllm/v1/completions --run-id selected_benchmarks
```

### 3. 프로덕션 평가

**설정 파일 수정:**
`configs/eval_config.json`에서 중요 벤치마크 활성화 및 전체 데이터셋 사용:

```json
{
  "benchmarks": {
    "arc_easy": {
      "enabled": true     // ← 활성화
    },
    "arc_challenge": {
      "enabled": true     // ← 활성화
    },
    "hellaswag": {
      "enabled": true     // ← 활성화
    }
  },
  "tasks": {
    "arc_easy": {
      "enabled": true,
      "limit": null       // ← 전체 데이터셋 사용
    },
    "arc_challenge": {
      "enabled": true,
      "limit": null       // ← 전체 데이터셋 사용
    },
    "hellaswag": {
      "enabled": true,
      "limit": null       // ← 전체 데이터셋 사용
    }
  }
}
```

**실행:**
```bash
./run_evalchemy.sh \
    --endpoint http://localhost/vllm/v1/completions \
    --batch-size 4 \
    --run-id production_eval_$(date +%Y%m%d)
```

## 결과 확인

평가 완료 후 결과는 다음 위치에 저장됩니다:

```
results/
└── {run_id}/
    ├── evalchemy_{run_id}.log              # 실행 로그
    ├── evalchemy_errors_{run_id}.log       # 에러 로그
    ├── evalchemy_summary_{run_id}.json     # 결과 요약
    ├── {benchmark}_results.json            # 각 벤치마크 상세 결과
    └── {benchmark}_benchmark.log           # 각 벤치마크 실행 로그
```

### 결과 요약 확인

```bash
# 요약 결과 확인
cat results/test_macos_run/evalchemy_summary_test_macos_run.json | jq '.'

# 특정 벤치마크 결과 확인
cat results/test_macos_run/arc_easy_results.json | jq '.results'
```

## 문제 해결

### 1. 설정 검증

```bash
# JSON 문법 검사
jq empty configs/eval_config.json && echo "Valid JSON" || echo "Invalid JSON"

# 설정 파일 검증
./run_evalchemy.sh --validate-config
```

### 2. 의존성 확인

```bash
# 필요한 패키지 설치 확인
python3 -c "import lm_eval, torch, transformers; print('All packages available')"

# 시스템 유틸리티 확인
command -v jq && command -v curl && echo "System utilities OK"
```

### 3. 연결 테스트

```bash
# 엔드포인트 연결 테스트
curl -f http://localhost/vllm/v1/models

# 완성 엔드포인트 테스트
curl -X POST http://localhost/vllm/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-8b","prompt":"Hello","max_tokens":1}'
```

이 가이드를 통해 Evalchemy 벤치마크 시스템을 효과적으로 관리하고 활용할 수 있습니다. 
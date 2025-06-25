# NVIDIA Eval 벤치마크 가이드

NVIDIA에서 제공하는 데이터셋과 평가 방식을 활용해 **LiveCodeBench**와 **AIME** 벤치마크를 수행하는 평가 시스템입니다.

## 📋 개요

이 모듈은 다음 두 가지 주요 벤치마크를 지원합니다:
- **LiveCodeBench**: 최신 코딩 문제 기반 벤치마크 (Avg@8 평가)
- **AIME**: 미국 수학 초청 시험 문제 기반 벤치마크 (Avg@64 평가)

## 🔧 환경 설정

### 필수 의존성
```bash
# 핵심 의존성 설치
pip install vllm==0.7.3 torch==2.5.1 transformers==4.48.2

# 추가 의존성 설치
pip install numpy tqdm sympy pandas antlr4-python3-runtime
```

### 지원 모델
현재 다음 모델들이 사전 구성되어 있습니다:
- `nvidia/AceReason-Nemotron-7B`
- `nvidia/AceReason-Nemotron-14B` 
- `nvidia/AceReason-Nemotron-1.1-7B`
- `qwen3-8b` (테스트용)

## 📁 파일 구조

```
eval/nvidia_eval/
├── data/                           # 평가 데이터셋
│   ├── aime24.jsonl               # AIME 2024 문제
│   ├── aime25.jsonl               # AIME 2025 문제
│   └── livecodebench_split.json   # LiveCodeBench 문제
├── tools/                          # 평가 도구
│   ├── grader.py                  # 수학 답안 채점기
│   ├── code_verifier.py           # 코드 검증기
│   └── convert_ckpt_to_safetensors.py
├── run_livecodebench.sh           # LiveCodeBench 실행 스크립트
├── run_aime.sh                    # AIME 실행 스크립트
├── inference.py                   # 추론 엔진
├── evaluate_*.py                  # 평가 스크립트들
└── README.md                      # 이 문서
```

## 🚀 사용법

### 1. 원클릭 평가 (권장)

**LiveCodeBench 평가**
```bash
bash run_livecodebench.sh <MODEL_PATH> <OUTPUT_PATH> <GPUS> <OUT_SEQ_LEN>

# 예시
bash run_livecodebench.sh qwen3-8b cache/qwen3-8b 1 14444
```

**AIME 평가**
```bash  
bash run_aime.sh <MODEL_PATH> <OUTPUT_PATH> <GPUS> <OUT_SEQ_LEN>

# 예시
bash run_aime.sh qwen3-8b cache/qwen3-8b 1 14444
```

### 2. 개별 구성 요소 실행

**데이터셋 다운로드**
```bash
# LiveCodeBench 데이터셋 자동 다운로드
python download_livecodebench.py
```

**개별 시드로 추론 실행**
```bash
# LiveCodeBench 단일 시드 실행
bash generate_livecodebench.sh <MODEL_PATH> <SEED> <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>

# AIME 단일 시드 실행  
bash generate_aime.sh <MODEL_PATH> <SEED> aime24 <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>
bash generate_aime.sh <MODEL_PATH> <SEED> aime25 <OUTPUT_PATH> <MODEL_TYPE> <GPUS> <OUT_SEQ_LEN>
```

**평가 실행**
```bash
# AIME 평가
python evaluate_aime.py --modelfolder <OUTPUT_PATH> --test_data data/aime24.jsonl

# LiveCodeBench 평가
python evaluate_livecodebench.py -q data/livecodebench_problems.jsonl -g <OUTPUT_PATH>
```

## 📊 출력 결과

평가 완료 후 다음 파일들이 생성됩니다:

### LiveCodeBench 결과
- `<OUTPUT_PATH>/livecodebench_evaluation_results.json`: 원본 평가 결과
- `<OUTPUT_PATH>/standardized/standardized_livecodebench_evaluation_results.json`: 표준화된 결과

### AIME 결과  
- `<OUTPUT_PATH>/aime24_evaluation_results.json`: AIME 2024 평가 결과
- `<OUTPUT_PATH>/aime25_evaluation_results.json`: AIME 2025 평가 결과
- `<OUTPUT_PATH>/standardized/`: 표준화된 결과 디렉토리

## 🛠️ 고급 사용법

### API 서버 모드
`inference.py`를 사용하여 API 서버와 연동한 평가도 가능합니다:
```bash
python inference.py \
    --api-base http://localhost:8000/v1 \
    --load <MODEL_NAME> \
    --datapath data/aime24.jsonl \
    --model-type qwen \
    --output-folder <OUTPUT_PATH>
```

### 데이터셋 커스터마이징
LiveCodeBench 데이터셋의 일부만 사용하려면:
```python
# download_livecodebench.py 수정
# 수정 전
test_data = dataset['test']

# 수정 후 (1개 샘플만 사용)
test_data = dataset['test'].select(range(1))
```

## 🔍 평가 도구

### Grader (수학 채점기)
`tools/grader.py`는 AIME 문제의 수학적 답안을 정확히 채점합니다:
- 수치적 동등성 검사
- 기호적 동등성 검사 (SymPy 활용)
- LaTeX 표현 파싱 지원

### Code Verifier (코드 검증기)
`tools/code_verifier.py`는 LiveCodeBench 코딩 문제의 솔루션을 검증합니다:
- 구문 오류 검사
- 실행 시간 제한
- 테스트 케이스 실행

## 🐛 문제 해결

### 일반적인 문제들

**1. 의존성 오류**
```bash
# ANTLR 관련 오류 시
pip install antlr4-python3-runtime

# SymPy 관련 오류 시  
pip install sympy --upgrade
```

**2. GPU 메모리 부족**
- `OUT_SEQ_LEN` 파라미터를 줄여보세요
- `GPUS` 파라미터를 늘려 병렬 처리하세요

**3. API 연결 오류**
- VLLM 서버가 정상 실행 중인지 확인하세요
- `--api-base` URL이 올바른지 확인하세요

**4. 평가 결과 파일 누락**
- 추론이 완전히 완료되었는지 확인하세요
- 출력 디렉토리 권한을 확인하세요

### 로그 확인
각 스크립트는 상세한 진행 상황을 출력하므로, 문제 발생 시 로그를 확인하여 디버깅하세요.

## 📈 성능 최적화

- **병렬 처리**: 여러 GPU 활용 시 `GPUS` 파라미터 조정
- **배치 크기**: `--batch-size` 파라미터로 추론 속도 조정
- **시퀀스 길이**: `OUT_SEQ_LEN`을 문제 복잡도에 맞게 설정
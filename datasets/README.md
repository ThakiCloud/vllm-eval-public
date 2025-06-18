# 데이터셋 관리

> VLLM 평가 시스템에서 사용되는 데이터셋 관리 가이드

## 🎯 개요

이 디렉토리는 **메타데이터만** 저장하며, 실제 데이터는 MinIO/S3에 저장됩니다. SHA-256 기반 불변 버전 체계를 사용하여 데이터 무결성을 보장합니다.

## 📁 구조

```
datasets/
├── README.md              # 이 파일
├── schema.yaml           # 데이터셋 스키마 정의
├── manifests/            # 데이터셋 매니페스트 파일들
│   ├── deepeval/
│   │   ├── rag-qa-v1.yaml
│   │   └── hallucination-v1.yaml
│   ├── evalchemy/
│   │   ├── arc-easy-v1.yaml
│   │   ├── arc-challenge-v1.yaml
│   │   ├── hellaswag-v1.yaml
│   │   └── mmlu-v1.yaml
│   └── korean/
│       ├── ko-mmlu-v1.yaml
│       └── ko-arc-v1.yaml
└── templates/            # 새 데이터셋 템플릿
    └── dataset-template.yaml
```

## 🔧 데이터셋 스키마

### 매니페스트 형식

```yaml
# dataset-manifest.yaml
apiVersion: v1
kind: Dataset
metadata:
  name: arc-easy
  version: v1.0.0
  created: "2024-01-15T00:00:00Z"
  description: "ARC Easy benchmark dataset"
spec:
  type: evalchemy  # deepeval | evalchemy
  category: reasoning  # reasoning | knowledge | rag | hallucination
  language: en  # en | ko | multi
  size: 2376  # number of samples
  checksum: sha256:abc123def456...
  storage:
    bucket: llm-eval-ds
    path: evalchemy/arc/easy/v1.0.0/
    format: json  # json | jsonl | parquet
  schema:
    input_fields:
      - question: string
      - choices: array[string]
      - answer_key: string
    output_fields:
      - prediction: string
      - confidence: float
  deduplication:
    method: minhash-lsh
    threshold: 0.2
    processed_at: "2024-01-15T01:00:00Z"
    original_size: 2500
    deduplicated_size: 2376
```

## 📊 지원 데이터셋

### Deepeval 데이터셋

| 이름 | 설명 | 크기 | 언어 | 용도 |
|------|------|------|------|------|
| `rag-qa-v1` | RAG 질답 평가 세트 | 1,000 | 한국어 | 정답률, 관련성 |
| `hallucination-v1` | 환각 탐지 세트 | 500 | 한국어 | 환각률 측정 |
| `context-relevance-v1` | 문맥 관련성 세트 | 800 | 한국어 | 문맥 적합성 |

### Evalchemy 데이터셋

| 이름 | 설명 | 크기 | 언어 | 벤치마크 |
|------|------|------|------|---------|
| `arc-easy-v1` | ARC Easy | 2,376 | 영어 | 상식 추론 |
| `arc-challenge-v1` | ARC Challenge | 1,172 | 영어 | 고급 추론 |
| `hellaswag-v1` | HellaSwag | 10,042 | 영어 | 상식 완성 |
| `mmlu-v1` | MMLU | 14,042 | 영어 | 종합 지식 |
| `ko-mmlu-v1` | 한국어 MMLU | 10,000 | 한국어 | 한국어 지식 |
| `ko-arc-v1` | 한국어 ARC | 2,000 | 한국어 | 한국어 추론 |

## 🔄 데이터 중복 제거

### 전략
1. **SHA-1/256 Hash** → Exact Match 제거
2. **Near-Dup (LSH + Levenshtein < 0.2)** 필터
3. **Cross-framework** 중복 제거 (Deepeval ↔ Evalchemy)

### 프로세스
```bash
# 중복 제거 실행
python scripts/dedup_datasets.py --input-manifest datasets/manifests/evalchemy/arc-easy-v1.yaml

# 결과 확인
cat datasets/manifests/evalchemy/arc-easy-v1.yaml
```

### 중복 제거 메트릭
- **원본 크기**: 데이터 수집 시점의 샘플 수
- **중복 제거 후**: 최종 사용되는 샘플 수
- **중복률**: (원본 - 최종) / 원본 × 100%

## 📥 새 데이터셋 추가

### 1. 매니페스트 작성
```bash
# 템플릿 복사
cp datasets/templates/dataset-template.yaml datasets/manifests/deepeval/my-dataset-v1.yaml

# 매니페스트 편집
vim datasets/manifests/deepeval/my-dataset-v1.yaml
```

### 2. 데이터 업로드
```bash
# MinIO에 업로드
mc cp my-dataset.json minio/llm-eval-ds/deepeval/my-dataset/v1.0.0/

# 체크섬 계산
sha256sum my-dataset.json
```

### 3. 매니페스트 업데이트
```yaml
spec:
  checksum: sha256:여기에_실제_체크섬
  size: 실제_샘플_수
```

### 4. 중복 제거 수행
```bash
python scripts/dedup_datasets.py --input-manifest datasets/manifests/deepeval/my-dataset-v1.yaml
```

## 🗄️ 저장소 구조

### MinIO 버킷 구조
```
llm-eval-ds/
├── deepeval/
│   ├── rag-qa/v1.0.0/data.json
│   └── hallucination/v1.0.0/data.json
├── evalchemy/
│   ├── arc/easy/v1.0.0/data.json
│   └── mmlu/v1.0.0/data.json
└── korean/
    ├── ko-mmlu/v1.0.0/data.json
    └── ko-arc/v1.0.0/data.json
```

### 버전 관리
- **Semantic Versioning**: `v{major}.{minor}.{patch}`
- **불변성**: 한 번 생성된 버전은 수정 불가
- **체크섬**: SHA-256으로 데이터 무결성 검증

## 🔧 유틸리티

### 데이터셋 검증
```bash
# 매니페스트 검증
python scripts/validate_manifest.py datasets/manifests/evalchemy/arc-easy-v1.yaml

# 체크섬 검증
python scripts/verify_checksum.py datasets/manifests/evalchemy/arc-easy-v1.yaml
```

### 통계 정보
```bash
# 데이터셋 통계
python scripts/dataset_stats.py

# 중복 분석
python scripts/analyze_duplicates.py
```

## 🚨 주의사항

### 데이터 품질
- **개인정보**: 모든 데이터는 익명화 필수
- **저작권**: 라이선스 확인 후 사용
- **품질**: 최소 95% 정확도 보장

### 보안
- **접근 제어**: MinIO 버킷 접근 권한 관리
- **암호화**: 전송 및 저장 시 암호화
- **감사**: 모든 접근 로그 기록

### 성능
- **캐싱**: 자주 사용되는 데이터셋은 로컬 캐시
- **압축**: 큰 데이터셋은 압축 저장
- **분할**: 대용량 데이터는 청크 단위 분할

## 📞 문의

데이터셋 관련 문의사항:
- **ML 팀**: ml-team@company.com
- **데이터 팀**: data-team@company.com
- **Slack**: #vllm-eval-datasets

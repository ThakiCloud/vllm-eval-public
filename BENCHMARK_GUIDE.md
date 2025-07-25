# VLLM Eval 벤치마크 추가/수정 가이드

이 문서는 `vllm-eval` 프로젝트에 새로운 벤치마크를 추가하거나 기존 벤치마크를 수정하는 절차를 안내합니다.

## 개요

벤치마크 추가/수정 작업은 주로 다음 폴더에 걸쳐 이루어집니다. 각 폴더는 평가 파이프라인의 특정 단계를 담당합니다.

1.  **`datasets`**: 벤치마크에 사용될 원본 데이터셋
2.  **`eval`**: 평가 로직 및 벤치마크 작업 정의
3.  **`configs`**: 평가 도구 및 벤치마크 실행 설정
4.  **`docker`**: 평가 환경 컨테이너 이미지
5.  **`k8s`**: 쿠버네티스 환경에서 평가 Job 실행 정의
6.  **`scripts`**: 로컬 테스트 및 보조 스크립트
7.  **`.github/workflows`**: CI/CD 파이프라인

## 단계별 폴더 설명 및 수정 가이드

### 1. `datasets` - 데이터셋 추가

-   **역할**: 벤치마크 평가에 사용될 데이터셋을 저장합니다.
-   **구조**:
    -   `datasets/raw/{벤치마크_이름}/`: 벤치마크별 원본 데이터셋을 이곳에 저장합니다. (예: `train.jsonl`, `test.jsonl`)
-   **가이드**:
    1.  새로운 벤치마크를 위한 데이터셋이 있다면 `datasets/raw/` 아래에 새 디렉토리를 생성합니다.
    2.  생성한 디렉토리 안에 `train`, `test` 등의 용도에 맞게 데이터 파일을 추가합니다.

### 2. `eval` - 벤치마크 작업 정의

-   **역할**: 실제 평가 로직과 각 벤치마크의 수행 방법을 정의합니다. `lm-evaluation-harness` 기반의 `evalchemy`를 핵심으로 사용합니다.
-   **구조**:
    -   `eval/evalchemy/tasks/`: 각 벤치마크의 설정(프롬프트, 메트릭 등)을 담은 YAML 파일을 저장합니다.
-   **가이드**:
    1.  `eval/evalchemy/tasks/` 디렉토리에 새로운 벤치마크를 위한 YAML 파일을 생성합니다.
    2.  기존 `custom_task_1.yaml` 파일을 참고하여 `task`, `dataset_path`, `doc_to_text`, `metric_list` 등 필요한 필드를 정의합니다.
    3.  `dataset_path`는 `1. datasets`에서 추가한 데이터셋의 경로를 올바르게 지정해야 합니다.

### 3. `configs` - 벤치마크 실행 설정

-   **역할**: 평가 도구의 전반적인 설정을 관리합니다. 어떤 벤치마크를 실행할지 등을 지정할 수 있습니다.
-   **구조**:
    -   `configs/evalchemy.json`: `evalchemy`로 실행할 벤치마크 목록과 설정을 정의합니다.
-   **가이드**:
    1.  `configs/evalchemy.json` 파일을 엽니다.
    2.  `tasks` 목록에 `2. eval`에서 생성한 벤치마크 YAML 파일의 이름(확장자 제외)을 추가하여 파이프라인이 해당 벤치마크를 실행하도록 설정합니다.

### 4. `docker` - 의존성 관리

-   **역할**: 평가를 실행할 환경을 정의하는 Dockerfile을 관리합니다.
-   **구조**:
    -   `docker/evalchemy.Dockerfile`: `evalchemy` 실행 환경을 정의하는 파일입니다.
-   **가이드**:
    1.  새로운 벤치마크가 특정 Python 라이브러리 등 추가적인 의존성을 필요로 하는 경우, `docker/evalchemy.Dockerfile`을 수정합니다.
    2.  `RUN pip install ...` 구문을 추가하여 필요한 패키지를 설치하도록 설정합니다.

### 5. `k8s` - 인프라 및 실행 환경 정의 (필요시)

-   **역할**: 쿠버네티스 클러스터에서 평가 Job을 실행하기 위한 설정을 관리합니다.
-   **구조**:
    -   `k8s/evalchemy-job.yaml`: `evalchemy` 평가 Job의 리소스, 환경 변수 등을 정의합니다.
-   **가이드**:
    1.  새로운 벤치마크가 특별한 컴퓨팅 리소스(예: 특정 GPU 타입)나 환경 변수를 필요로 하는 경우, 이 파일을 수정하여 Job 정의를 변경할 수 있습니다.
    2.  일반적인 벤치마크 추가 시에는 수정이 필요 없을 가능성이 높습니다.

### 6. `scripts` - 보조 스크립트 및 핵심 로직

-   **역할**: 로컬 테스트, 데이터 전처리, 결과 표준화 등 파이프라인의 핵심 로직을 수행하는 스크립트를 포함합니다. 일부 스크립트는 Docker 이미지에 포함되어 컨테이너 환경에서 직접 실행됩니다.
-   **구조**:
    -   `scripts/run_local_evalchemy.py`: 로컬에서 `evalchemy` 벤치마크를 실행하는 테스트용 스크립트입니다.
    -   `scripts/standardize_evalchemy.py`: `evalchemy`의 결과물을 표준 형식으로 변환하는 스크립트로, Docker 이미지에 포함됩니다.
-   **가이드**:
    1.  새로운 벤치마크를 추가한 후, `run_local_evalchemy.py` 와 같은 스크립트를 사용하여 CI/CD에 반영하기 전에 로컬에서 정상적으로 동작하는지 검증할 수 있습니다.
    2.  만약 벤치마크가 특별한 데이터 처리나 결과 변환 로직을 필요로 한다면, 이곳에 새로운 스크립트를 추가하고 필요시 `docker/evalchemy.Dockerfile`에도 해당 스크립트를 복사하도록 수정해야 할 수 있습니다.

### 7. `.github/workflows` - CI/CD 파이프라인 (필요시)

-   **역할**: 코드 변경 시 자동으로 Docker 이미지를 빌드하고 배포하는 CI/CD 파이프라인을 정의합니다.
-   **구조**:
    -   `evalchemy-build.yml`, `evalchemy-deploy.yml`: `evalchemy` 관련 빌드 및 배포 워크플로우입니다.
-   **가이드**:
    1.  일반적인 벤치마크 추가 시에는 수정이 필요하지 않습니다.
    2.  만약 빌드 과정이나 배포 로직 자체에 변경이 필요한 경우에만 이 파일들을 수정합니다.

## 요약

새로운 벤치마크를 추가하는 일반적인 흐름은 다음과 같습니다.

1.  **데이터셋 준비**: `datasets/raw/`에 데이터 추가
2.  **벤치마크 정의**: `eval/evalchemy/tasks/`에 YAML 파일 추가
3.  **벤치마크 활성화**: `configs/evalchemy.json`에 태스크 추가
4.  **(선택 사항) 의존성/스크립트 추가**: `docker/evalchemy.Dockerfile` 수정
5.  **로컬 테스트 및 스크립트 개발**: `scripts/`의 스크립트 활용 및 개발
6.  **Commit & Push**: Git에 변경사항 반영하여 파이프라인 실행 
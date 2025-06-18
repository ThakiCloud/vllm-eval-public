# Configuration Files

이 디렉토리는 VLLM 평가 시스템의 설정 파일들을 포함합니다.

## 파일 설명

### `deepeval.yaml`
- Deepeval 평가 시스템의 주요 설정
- 모델 엔드포인트, 평가 임계값, 데이터셋 경로 등 설정
- 환경 변수를 통한 동적 설정 지원

### `pytest.ini`
- Pytest 테스트 실행 설정
- 테스트 발견, 출력 형식, 마커, 로깅 등 설정
- 병렬 실행 및 커버리지 리포트 설정

## 환경 변수

다음 환경 변수들을 통해 설정을 오버라이드할 수 있습니다:

- `MODEL_ENDPOINT`: VLLM 모델 서버 엔드포인트
- `MODEL_NAME`: 평가할 모델 이름
- `OPENAI_API_KEY`: OpenAI API 키 (참조 모델용)
- `ANTHROPIC_API_KEY`: Anthropic API 키 (참조 모델용)
- `DATASET_PATH`: 평가 데이터셋 경로
- `RESULTS_PATH`: 결과 저장 경로
- `LOG_LEVEL`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)

## Docker 사용 시

Docker 컨테이너에서는 이 설정들이 `/app/configs/`에 복사되어 사용됩니다.
필요에 따라 볼륨 마운트를 통해 커스텀 설정을 제공할 수 있습니다:

```bash
docker run -v $(pwd)/custom-configs:/app/configs \
  vllm-eval/deepeval:latest
``` 
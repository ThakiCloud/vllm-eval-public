# 기여 가이드

> VLLM 모델 성능 자동 평가 시스템에 기여하는 방법

## 🙏 기여해주셔서 감사합니다!

이 프로젝트에 관심을 가져주시고 기여하고자 해주셔서 감사합니다. 이 문서는 효과적이고 일관성 있는 기여를 위한 가이드라인을 제공합니다.

## 📋 목차

- 🛠️ 개발 환경 설정
- 🔄 기여 프로세스
- 🎨 코딩 표준
- 🧪 테스팅 가이드라인
- 📚 문서화
- 🐛 이슈 리포팅
- 🔍 Pull Request 가이드라인
- 👥 코드 리뷰 프로세스

## 🛠️ 개발 환경 설정

### 필수 요구사항

- **Python**: 3.9+
- **Docker**: 24.0+
- **Kubernetes**: 1.26+ (로컬 테스트용)
- **Kind**: 0.20+ (로컬 클러스터)
- **Helm**: 3.12+
- **Git**: 2.30+

### 환경 구성

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/vllm-eval.git
cd vllm-eval

# 2. Python 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate

# 3. 개발 의존성 설치
pip install -r requirements-dev.txt
pip install -r requirements-test.txt

# 4. Pre-commit 훅 설치
pre-commit install

# 5. 테스트 실행으로 설정 확인
pytest eval/deepeval_tests/
```

### IDE 설정

-   **Interpreter**: `./venv/bin/python`
-   **Code style & Linter**: Ruff
-   **Test runner**: pytest

## 🔄 기여 프로세스

### 1. 이슈 확인 또는 생성
- 기존 이슈를 검색해보세요
- 새로운 기능이나 버그는 이슈를 먼저 생성해주세요
- 이슈 템플릿을 사용해주세요

### 2. 브랜치 생성
```bash
# 메인 브랜치에서 시작
git checkout main
git pull origin main

# 기능 브랜치 생성
git checkout -b feature/your-feature-name
# 또는 버그 수정
git checkout -b fix/bug-description
```

### 3. 개발 및 테스트
```bash
# 코드 변경 후 테스트
pytest

# 린팅 및 포맷팅
ruff check . --fix
ruff format .
```

### 4. 커밋
```bash
# 변경사항 커밋 (Conventional Commits 규칙 준수)
git add .
git commit -m "feat: add new evaluation metric for hallucination detection"
```

### 5. Pull Request 생성
```bash
# 브랜치 푸시
git push origin feature/your-feature-name

# GitHub에서 PR 생성
```

## 🎨 코딩 표준

### Python 코드 스타일

**Ruff**를 사용한 자동 린팅 및 포맷팅을 따릅니다:

```python
# ✅ 좋은 예
from typing import Dict, List, Optional

import torch
from deepeval import BaseMetric


class HallucinationMetric(BaseMetric):
    """환각 탐지를 위한 커스텀 메트릭.
    
    Args:
        threshold: 환각 판정 임계값 (0.0-1.0)
        model_name: 사용할 모델명
        
    Returns:
        HallucinationScore: 환각 점수 결과
    """
    
    def __init__(self, threshold: float = 0.5, model_name: str = "gpt-4") -> None:
        self.threshold = threshold
        self.model_name = model_name
        
    def measure(self, test_case: Dict[str, str]) -> float:
        """환각 점수를 측정합니다."""
        # 구현 내용
        pass
```

### 명명 규칙

- **파일명**: `snake_case.py`
- **클래스명**: `PascalCase`
- **함수/변수명**: `snake_case`
- **상수명**: `UPPER_SNAKE_CASE`
- **Private 멤버**: `_leading_underscore`

### 타입 힌팅

모든 함수에는 타입 힌팅을 포함해야 합니다:

```python
from typing import Dict, List, Optional, Union

def evaluate_model(
    model_endpoint: str,
    dataset_path: str,
    metrics: List[str],
    config: Optional[Dict[str, Union[str, int]]] = None
) -> Dict[str, float]:
    """모델을 평가합니다."""
    pass
```

### 에러 처리

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EvaluationError(Exception):
    """평가 과정에서 발생하는 에러."""
    pass

def safe_evaluate(model_endpoint: str) -> Optional[Dict[str, float]]:
    """안전한 모델 평가."""
    try:
        result = evaluate_model(model_endpoint)
        return result
    except ConnectionError as e:
        logger.error(f"모델 연결 실패: {e}")
        return None
    except EvaluationError as e:
        logger.error(f"평가 실패: {e}")
        raise
```

## 🧪 테스팅 가이드라인

### 테스트 구조

-   **Deepeval 테스트**: `eval/deepeval_tests/` 디렉토리 안에 Pytest 기반의 테스트 코드가 위치합니다.
    -   커스텀 메트릭 테스트: `eval/deepeval_tests/test_custom_metric.py`
    -   RAG 평가 테스트: `eval/deepeval_tests/test_llm_rag.py`

### 테스트 작성 규칙

```python
import pytest
from unittest.mock import Mock, patch

from eval.deepeval_tests.metrics.rag_precision import RAGPrecisionMetric


class TestRAGPrecisionMetric:
    """RAG Precision 메트릭 테스트."""
    
    @pytest.fixture
    def metric(self) -> RAGPrecisionMetric:
        """테스트용 메트릭 인스턴스."""
        return RAGPrecisionMetric(threshold=0.8)
    
    def test_init_with_default_params(self) -> None:
        """기본 파라미터로 초기화 테스트."""
        metric = RAGPrecisionMetric()
        assert metric.threshold == 0.7
        assert metric.name == "rag_precision"
    
    @patch('eval.deepeval_tests.metrics.rag_precision.openai_client')
    def test_measure_high_precision(self, mock_client: Mock, metric: RAGPrecisionMetric) -> None:
        """높은 정밀도 케이스 테스트."""
        # Given
        mock_client.return_value = {"score": 0.9}
        test_case = {
            "query": "테스트 질문",
            "context": "관련 문맥",
            "answer": "정답"
        }
        
        # When
        score = metric.measure(test_case)
        
        # Then
        assert score > 0.8
        mock_client.assert_called_once()
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 테스트 파일
pytest tests/unit/test_metrics.py

# 커버리지 포함
pytest --cov=eval --cov-report=html

# 병렬 실행
pytest -n auto
```

## 📚 문서화

### 📝 문서 언어 정책

**모든 새로운 문서는 영어로 작성해야 합니다.**

- **새 문서**: 영어로만 작성
- **기존 한국어 문서**: 점진적으로 영어로 전환 예정
- **코드 주석**: 영어 사용 권장
- **API 문서**: 영어 필수
- **README 파일**: 영어 우선

```markdown
# ✅ 좋은 예 (영어)
## Installation Guide
This section explains how to install the vLLM evaluation system...

# ❌ 피해야 할 예 (새로운 한국어 문서)
## 설치 가이드
이 섹션은 vLLM 평가 시스템 설치 방법을 설명합니다...
```

**이유:**
- 국제적인 협업 환경 지원
- 더 넓은 개발자 커뮤니티 접근성
- 기술 문서의 표준화
- 오픈소스 프로젝트 베스트 프랙티스 준수

> **참고**: 기존 한국어 문서는 마이그레이션 계획에 따라 점진적으로 영어로 전환됩니다.

### Docstring 규칙

Google 스타일 docstring을 사용합니다:

```python
def evaluate_dataset(
    dataset_path: str, 
    metrics: List[str],
    batch_size: int = 32
) -> Dict[str, float]:
    """데이터셋을 평가합니다.
    
    Args:
        dataset_path: 데이터셋 파일 경로
        metrics: 사용할 메트릭 리스트
        batch_size: 배치 크기
        
    Returns:
        메트릭별 점수 딕셔너리
        
    Raises:
        FileNotFoundError: 데이터셋 파일이 없는 경우
        EvaluationError: 평가 중 오류 발생
        
    Example:
        >>> results = evaluate_dataset("data.json", ["accuracy", "f1"])
        >>> print(results["accuracy"])
        0.85
    """
    pass
```

### README 및 문서 업데이트

새로운 기능을 추가할 때는 관련 문서도 함께 업데이트해주세요:

- `README.md`: 주요 기능 변경
- `docs/`: 상세 가이드
- API 문서: 새로운 API 추가 시

## 🐛 이슈 리포팅

### 버그 리포트

이슈 템플릿을 사용하여 다음 정보를 포함해주세요:

- **환경 정보**: OS, Python 버전, 의존성 버전
- **재현 단계**: 단계별 상세 설명
- **예상 동작**: 어떻게 동작해야 하는지
- **실제 동작**: 실제로 무엇이 일어났는지
- **로그**: 관련 에러 로그나 스택 트레이스

### 기능 요청

- **동기**: 왜 이 기능이 필요한지
- **제안**: 어떻게 구현되어야 하는지
- **대안**: 고려된 다른 방법들
- **영향도**: 기존 기능에 미치는 영향

## 🔍 Pull Request 가이드라인

### PR 체크리스트

- [ ] 이슈와 연결되어 있습니다
- [ ] 테스트가 통과합니다
- [ ] 코드 커버리지가 유지되거나 개선됩니다
- [ ] 문서가 업데이트되었습니다
- [ ] CHANGELOG가 업데이트되었습니다 (필요시)
- [ ] Breaking changes가 명시되었습니다 (해당시)

### PR 템플릿

```markdown
## 변경사항 요약
<!-- 무엇을 변경했는지 간단히 설명 -->

## 관련 이슈
<!-- 해결하는 이슈 번호 -->
Closes #123

## 변경 유형
- [ ] 버그 수정
- [ ] 새 기능
- [ ] Breaking change
- [ ] 문서 업데이트

## 테스트
<!-- 어떻게 테스트했는지 설명 -->

## 체크리스트
- [ ] 테스트 추가/업데이트
- [ ] 문서 업데이트
- [ ] 린팅 통과
```

### 커밋 메시지 규칙

[Conventional Commits](https://www.conventionalcommits.org/)을 따릅니다:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 스타일 변경
- `refactor`: 리팩토링
- `test`: 테스트 추가/수정
- `chore`: 기타 변경사항

**Examples:**
```
feat(metrics): add hallucination detection metric

fix(deepeval): resolve memory leak in evaluation loop

docs(readme): update installation instructions

test(rag): add integration tests for RAG metrics
```

## 👥 코드 리뷰 프로세스

### 리뷰어 가이드라인

**리뷰 포인트:**
- 코드 품질 및 가독성
- 테스트 커버리지
- 성능 영향
- 보안 고려사항
- API 일관성

**리뷰 예시:**
```markdown
### 💡 제안
`evaluate_model` 함수에서 에러 처리를 추가하는 것이 좋겠습니다.

### 🐛 이슈
L45: 이 부분에서 메모리 누수가 발생할 수 있습니다.

### ✅ 승인
LGTM! 테스트도 잘 작성되었네요.
```

### 작성자 가이드라인

- 리뷰 피드백에 신속하게 응답
- 변경사항에 대한 명확한 설명
- 테스트 결과 공유
- 의견 불일치 시 건설적 토론

## 🏷️ 릴리스 프로세스

### 버전 관리

- **Semantic Versioning** 사용: `MAJOR.MINOR.PATCH`
- **Pre-release**: `1.0.0-alpha.1`, `1.0.0-beta.1`, `1.0.0-rc.1`

### 릴리스 단계

1. **Feature freeze**: 새 기능 추가 중단
2. **테스팅**: 전체 테스트 스위트 실행
3. **문서 업데이트**: README, CHANGELOG 업데이트
4. **태그 생성**: `git tag v1.0.0`
5. **릴리스 노트**: GitHub 릴리스 페이지 작성

## 🔒 보안 가이드라인

### 보안 이슈 리포팅

보안 취약점은 public 이슈가 아닌 이메일로 신고해주세요:
- **이메일**: security@company.com
- **PGP Key**: [공개키 링크]

### 보안 체크리스트

- 민감한 정보 하드코딩 금지
- 의존성 취약점 정기 검사
- API 엔드포인트 인증/인가 확인
- 로그에 민감한 정보 출력 금지

## 🎉 인정과 감사

모든 기여자는 README의 Contributors 섹션에 등록됩니다. 또한 릴리스 노트에서 기여 내용이 언급됩니다.

## 📞 도움 및 문의

- **일반 질문**: GitHub Discussions
- **기술 지원**: #vllm-eval Slack 채널
- **긴급 문의**: tech-support@company.com

---

**다시 한번 기여해주셔서 감사합니다!** 🙏

질문이나 제안사항이 있으시면 언제든지 연락해주세요.

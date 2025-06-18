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

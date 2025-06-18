"""
Custom metrics for VLLM evaluation system.
""" from .rag_precision import RAGPrecisionMetric
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

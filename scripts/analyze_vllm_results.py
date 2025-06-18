#!/usr/bin/env python3
"""
VLLM 벤치마크 결과 분석 스크립트
VLLM benchmark_serving.py 출력 결과를 분석하고 리포트를 생성합니다.
"""
import json
import os
import sys
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics
from datetime import datetime

def load_vllm_benchmark_results(path: str) -> Dict[str, Any]:
    """VLLM 벤치마크 결과 로드 (파일 또는 디렉토리)"""
    results = {}
    json_files = []
    
    # 입력이 파일인지 디렉토리인지 확인
    if os.path.isfile(path):
        if path.endswith('.json'):
            json_files = [path]
        else:
            print(f"⚠️  JSON 파일이 아닙니다: {path}")
            return results
    elif os.path.isdir(path):
        # 디렉토리인 경우 JSON 파일들 찾기
        json_files = glob.glob(f"{path}/**/*.json", recursive=True)
        if not json_files:
            # 현재 디렉토리에서도 찾기
            json_files = glob.glob(f"{path}/*.json")
    else:
        print(f"⚠️  경로가 존재하지 않습니다: {path}")
        return results
    
    if not json_files:
        print(f"⚠️  JSON 결과 파일을 찾을 수 없습니다: {path}")
        return results
    
    print(f"📁 발견된 JSON 파일들: {len(json_files)}개")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 파일명에서 시나리오 이름 추출
            scenario_name = Path(json_file).stem
            results[scenario_name] = data
            print(f"✅ {scenario_name}: 결과 로드 완료")
            
        except Exception as e:
            print(f"❌ {json_file}: 결과 로드 실패 - {e}")
    
    return results

def analyze_vllm_performance(results: Dict[str, Any]) -> None:
    """VLLM 성능 분석 및 리포트 생성"""
    print("\n" + "="*70)
    print("📊 VLLM 벤치마크 성능 분석 결과")
    print("="*70)
    
    summary = []
    
    for scenario_name, data in results.items():
        print(f"\n🎯 시나리오: {scenario_name}")
        print("-" * 50)
        
        # 기본 통계
        completed_requests = data.get('completed', 0)
        total_requests = data.get('total_requests', completed_requests)
        success_rate = completed_requests / total_requests if total_requests > 0 else 0
        
        print(f"✅ 성공률: {success_rate:.1%} ({completed_requests}/{total_requests})")
        print(f"⏱️  총 소요시간: {data.get('duration', 0):.2f}초")
        
        # 처리량 메트릭
        request_throughput = data.get('request_throughput', 0)
        input_throughput = data.get('input_throughput', 0)
        output_throughput = data.get('output_throughput', 0)
        
        print(f"🔄 요청 처리량: {request_throughput:.2f} req/s")
        print(f"📥 입력 토큰 처리량: {input_throughput:.1f} tok/s")
        print(f"📤 출력 토큰 처리량: {output_throughput:.1f} tok/s")
        
        # 지연시간 메트릭 (TTFT - Time to First Token)
        ttft_mean = data.get('mean_ttft_ms', 0)
        ttft_median = data.get('median_ttft_ms', 0)
        ttft_p95 = data.get('p95_ttft_ms', 0)
        ttft_p99 = data.get('p99_ttft_ms', 0)
        
        print(f"🚀 TTFT 평균: {ttft_mean:.1f}ms")
        print(f"🚀 TTFT 중앙값: {ttft_median:.1f}ms")
        print(f"🚀 TTFT P95: {ttft_p95:.1f}ms")
        print(f"🚀 TTFT P99: {ttft_p99:.1f}ms")
        
        # TPOT (Time per Output Token)
        tpot_mean = data.get('mean_tpot_ms', 0)
        tpot_median = data.get('median_tpot_ms', 0)
        tpot_p95 = data.get('p95_tpot_ms', 0)
        tpot_p99 = data.get('p99_tpot_ms', 0)
        
        print(f"⚡ TPOT 평균: {tpot_mean:.1f}ms")
        print(f"⚡ TPOT 중앙값: {tpot_median:.1f}ms")
        print(f"⚡ TPOT P95: {tpot_p95:.1f}ms")
        print(f"⚡ TPOT P99: {tpot_p99:.1f}ms")
        
        # ITL (Inter-token Latency)
        itl_mean = data.get('mean_itl_ms', 0)
        itl_p95 = data.get('p95_itl_ms', 0)
        
        if itl_mean > 0:
            print(f"🔗 ITL 평균: {itl_mean:.1f}ms")
            print(f"🔗 ITL P95: {itl_p95:.1f}ms")
        
        # E2E Latency (End-to-End)
        e2el_mean = data.get('mean_e2el_ms', 0)
        e2el_median = data.get('median_e2el_ms', 0)
        e2el_p95 = data.get('p95_e2el_ms', 0)
        e2el_p99 = data.get('p99_e2el_ms', 0)
        
        print(f"🔄 E2E 평균: {e2el_mean:.1f}ms")
        print(f"🔄 E2E 중앙값: {e2el_median:.1f}ms")
        print(f"🔄 E2E P95: {e2el_p95:.1f}ms")
        print(f"🔄 E2E P99: {e2el_p99:.1f}ms")
        
        # 토큰 통계
        input_tokens = data.get('total_input_tokens', 0)
        output_tokens = data.get('total_output_tokens', 0)
        
        if input_tokens > 0 or output_tokens > 0:
            print(f"📊 총 입력 토큰: {input_tokens:,}")
            print(f"📊 총 출력 토큰: {output_tokens:,}")
            print(f"📊 평균 입력 길이: {input_tokens/completed_requests:.1f}" if completed_requests > 0 else "")
            print(f"📊 평균 출력 길이: {output_tokens/completed_requests:.1f}" if completed_requests > 0 else "")
        
        # 요약 데이터 수집
        summary.append({
            'scenario': scenario_name,
            'success_rate': success_rate,
            'request_throughput': request_throughput,
            'output_throughput': output_throughput,
            'ttft_p95': ttft_p95,
            'tpot_mean': tpot_mean,
            'e2el_p95': e2el_p95
        })
    
    # 전체 요약 및 성능 평가
    if summary:
        print(f"\n📈 전체 성능 요약")
        print("-" * 50)
        
        avg_success_rate = statistics.mean([s['success_rate'] for s in summary])
        avg_request_throughput = statistics.mean([s['request_throughput'] for s in summary])
        avg_output_throughput = statistics.mean([s['output_throughput'] for s in summary])
        avg_ttft_p95 = statistics.mean([s['ttft_p95'] for s in summary])
        avg_tpot_mean = statistics.mean([s['tpot_mean'] for s in summary])
        avg_e2el_p95 = statistics.mean([s['e2el_p95'] for s in summary])
        
        print(f"평균 성공률: {avg_success_rate:.1%}")
        print(f"평균 요청 처리량: {avg_request_throughput:.2f} req/s")
        print(f"평균 출력 토큰 처리량: {avg_output_throughput:.1f} tok/s")
        print(f"평균 TTFT P95: {avg_ttft_p95:.1f}ms")
        print(f"평균 TPOT: {avg_tpot_mean:.1f}ms")
        print(f"평균 E2E P95: {avg_e2el_p95:.1f}ms")
        
        # 성능 등급 판정
        grade, issues = evaluate_performance(
            avg_success_rate, avg_output_throughput, 
            avg_ttft_p95, avg_tpot_mean, avg_e2el_p95
        )
        
        print(f"\n🏆 종합 성능 등급: {grade}")
        if issues:
            print("⚠️  개선 필요 사항:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✨ 모든 성능 지표가 우수합니다!")

def evaluate_performance(success_rate: float, throughput: float, 
                        ttft_p95: float, tpot_mean: float, e2el_p95: float) -> tuple:
    """성능 등급 평가"""
    grade = "A"
    issues = []
    
    # 성공률 체크
    if success_rate < 0.95:
        grade = "C"
        issues.append(f"낮은 성공률 ({success_rate:.1%})")
    elif success_rate < 0.98:
        grade = "B"
        issues.append(f"보통 성공률 ({success_rate:.1%})")
    
    # 처리량 체크
    if throughput < 10:
        grade = "C"
        issues.append(f"낮은 처리량 ({throughput:.1f} tok/s)")
    elif throughput < 50:
        grade = "B" if grade == "A" else grade
        issues.append(f"보통 처리량 ({throughput:.1f} tok/s)")
    
    # TTFT 체크
    if ttft_p95 > 500:
        grade = "C"
        issues.append(f"높은 TTFT P95 ({ttft_p95:.1f}ms)")
    elif ttft_p95 > 200:
        grade = "B" if grade == "A" else grade
        issues.append(f"보통 TTFT P95 ({ttft_p95:.1f}ms)")
    
    # TPOT 체크
    if tpot_mean > 100:
        grade = "C"
        issues.append(f"높은 TPOT ({tpot_mean:.1f}ms)")
    elif tpot_mean > 50:
        grade = "B" if grade == "A" else grade
        issues.append(f"보통 TPOT ({tpot_mean:.1f}ms)")
    
    # E2E 지연시간 체크
    if e2el_p95 > 5000:
        grade = "C"
        issues.append(f"높은 E2E P95 ({e2el_p95:.1f}ms)")
    elif e2el_p95 > 2000:
        grade = "B" if grade == "A" else grade
        issues.append(f"보통 E2E P95 ({e2el_p95:.1f}ms)")
    
    return grade, issues

def generate_summary_report(results: Dict[str, Any], output_file: str) -> None:
    """요약 리포트 JSON 생성"""
    summary_data = {
        "timestamp": datetime.now().isoformat(),
        "total_scenarios": len(results),
        "scenarios": {}
    }
    
    for scenario_name, data in results.items():
        summary_data["scenarios"][scenario_name] = {
            "success_rate": data.get('completed', 0) / max(data.get('total_requests', 1), 1),
            "request_throughput": data.get('request_throughput', 0),
            "output_throughput": data.get('output_throughput', 0),
            "ttft_p95_ms": data.get('p95_ttft_ms', 0),
            "tpot_mean_ms": data.get('mean_tpot_ms', 0),
            "e2el_p95_ms": data.get('p95_e2el_ms', 0)
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 요약 리포트 생성: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 analyze_vllm_results.py <results_path> [output_summary.json]")
        print("예시: python3 analyze_vllm_results.py /results/benchmark.json summary.json")
        print("      python3 analyze_vllm_results.py /results summary.json")
        sys.exit(1)
    
    results_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(results_path):
        print(f"❌ 결과 경로가 존재하지 않습니다: {results_path}")
        sys.exit(1)
    
    print(f"📁 결과 경로: {results_path}")
    
    # 결과 로드 및 분석
    results = load_vllm_benchmark_results(results_path)
    
    if not results:
        print("❌ 분석할 결과가 없습니다.")
        sys.exit(1)
    
    # 성능 분석
    analyze_vllm_performance(results)
    
    # 요약 리포트 생성 (옵션)
    if output_file:
        generate_summary_report(results, output_file)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
VLLM 성능 벤치마크 결과 분석 스크립트
"""
import json
import os
import sys
import glob
from pathlib import Path
from typing import Dict, List, Any
import statistics

def load_benchmark_results(results_dir: str) -> Dict[str, Any]:
    """벤치마크 결과 로드"""
    results = {}
    
    for scenario_dir in glob.glob(f"{results_dir}/*_*"):
        if not os.path.isdir(scenario_dir):
            continue
            
        scenario_name = os.path.basename(scenario_dir).split('_')[0]
        
        # JSON 결과 파일 찾기
        json_files = glob.glob(f"{scenario_dir}/*.json")
        if not json_files:
            print(f"⚠️  {scenario_name}: JSON 결과 파일 없음")
            continue
            
        # 가장 최근 파일 사용
        latest_file = max(json_files, key=os.path.getctime)
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
                results[scenario_name] = data
                print(f"✅ {scenario_name}: 결과 로드 완료")
        except Exception as e:
            print(f"❌ {scenario_name}: 결과 로드 실패 - {e}")
    
    return results

def analyze_performance(results: Dict[str, Any]) -> None:
    """성능 분석 및 리포트 생성"""
    print("\n" + "="*60)
    print("📊 VLLM 성능 벤치마크 분석 결과")
    print("="*60)
    
    summary = []
    
    for scenario_name, data in results.items():
        print(f"\n🎯 시나리오: {scenario_name}")
        print("-" * 40)
        
        # 기본 메트릭 (올바른 필드명 사용)
        completed_requests = data.get('completed', 0)
        total_requests = data.get('num_prompts', completed_requests)
        success_rate = completed_requests / total_requests if total_requests > 0 else 0
        
        print(f"✅ 성공률: {success_rate:.1%} ({completed_requests}/{total_requests})")
        print(f"⏱️  총 소요시간: {data.get('duration', 0):.1f}초")
        print(f"🔄 요청 처리량: {data.get('request_throughput', 0):.2f} req/s")
        print(f"📤 토큰 처리량: {data.get('output_throughput', 0):.1f} tok/s")
        
        # TTFT (Time to First Token)
        ttft_mean = data.get('mean_ttft_ms', 0)
        ttft_p95 = data.get('p95_ttft_ms', 0)
        print(f"🚀 TTFT 평균: {ttft_mean:.1f}ms")
        print(f"🚀 TTFT P95: {ttft_p95:.1f}ms")
        
        # TPOT (Time per Output Token)
        tpot_mean = data.get('mean_tpot_ms', 0)
        tpot_p95 = data.get('p95_tpot_ms', 0)
        print(f"⚡ TPOT 평균: {tpot_mean:.1f}ms")
        print(f"⚡ TPOT P95: {tpot_p95:.1f}ms")
        
        # E2E Latency
        e2el_mean = data.get('mean_e2el_ms', 0)
        e2el_p95 = data.get('p95_e2el_ms', 0)
        print(f"🔄 E2E 평균: {e2el_mean:.1f}ms")
        print(f"🔄 E2E P95: {e2el_p95:.1f}ms")
        
        # 요약 데이터 수집
        summary.append({
            'scenario': scenario_name,
            'success_rate': success_rate,
            'throughput': data.get('output_throughput', 0),
            'ttft_p95': ttft_p95,
            'tpot_mean': tpot_mean,
            'e2el_p95': e2el_p95
        })
    
    # 전체 요약
    if summary:
        print(f"\n📈 전체 요약")
        print("-" * 40)
        
        avg_success_rate = statistics.mean([s['success_rate'] for s in summary])
        avg_throughput = statistics.mean([s['throughput'] for s in summary])
        avg_ttft_p95 = statistics.mean([s['ttft_p95'] for s in summary])
        avg_tpot_mean = statistics.mean([s['tpot_mean'] for s in summary])
        
        print(f"평균 성공률: {avg_success_rate:.1%}")
        print(f"평균 처리량: {avg_throughput:.1f} tok/s")
        print(f"평균 TTFT P95: {avg_ttft_p95:.1f}ms")
        print(f"평균 TPOT: {avg_tpot_mean:.1f}ms")
        
        # 성능 등급 판정
        grade = "A"
        issues = []
        
        if avg_success_rate < 0.95:
            grade = "C"
            issues.append(f"낮은 성공률 ({avg_success_rate:.1%})")
        
        if avg_ttft_p95 > 200:
            grade = "B" if grade == "A" else grade
            issues.append(f"높은 TTFT P95 ({avg_ttft_p95:.1f}ms)")
        
        if avg_tpot_mean > 50:
            grade = "B" if grade == "A" else grade
            issues.append(f"높은 TPOT ({avg_tpot_mean:.1f}ms)")
        
        if avg_throughput < 10:
            grade = "C"
            issues.append(f"낮은 처리량 ({avg_throughput:.1f} tok/s)")
        
        print(f"\n🏆 종합 성능 등급: {grade}")
        if issues:
            print("⚠️  개선 필요 사항:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✨ 모든 성능 지표가 우수합니다!")

def main():
    if len(sys.argv) != 2:
        print("사용법: python3 analyze_performance_results.py <results_directory>")
        sys.exit(1)
    
    results_dir = sys.argv[1]
    
    if not os.path.exists(results_dir):
        print(f"❌ 결과 디렉토리가 존재하지 않습니다: {results_dir}")
        sys.exit(1)
    
    print(f"📁 결과 디렉토리: {results_dir}")
    
    # 결과 로드 및 분석
    results = load_benchmark_results(results_dir)
    
    if not results:
        print("❌ 분석할 결과가 없습니다.")
        sys.exit(1)
    
    analyze_performance(results)

if __name__ == "__main__":
    main() 
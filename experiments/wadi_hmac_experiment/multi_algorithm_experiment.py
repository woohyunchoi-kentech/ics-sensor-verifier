#!/usr/bin/env python3
"""
통합 다중 알고리즘 실험 러너
==========================
HMAC, RSA, AES-GCM, ECDSA 알고리즘을 순차적으로 실험
"""

import asyncio
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
import csv
from typing import Dict, List, Any

# 기존 알고리즘들 import
from base_experiment import CryptoAlgorithm, BaseExperiment
from rsa_experiment import RSAAlgorithm
from aes_gcm_experiment import AESGCMAlgorithm
from ecdsa_experiment import ECDSAAlgorithm

class HMACAlgorithm(CryptoAlgorithm):
    """HMAC-SHA256 알고리즘 (기존 성공한 버전)"""
    
    def __init__(self):
        super().__init__("HMAC", "hmac")
        self.key = b"default-insecure-key-change-in-production"
    
    def generate_message(self, sensor_id: str, timestamp: int, value: float) -> str:
        """HMAC 메시지 생성"""
        return f"{sensor_id}|{timestamp}|{value:.6f}"
    
    def generate_auth_data(self, sensor_id: str, timestamp: int, value: float) -> Dict[str, Any]:
        """HMAC 생성"""
        message = self.generate_message(sensor_id, timestamp, value)
        hmac_value = hmac.new(self.key, message.encode(), hashlib.sha256).hexdigest()
        
        return {
            "hmac": hmac_value
        }
    
    def get_payload(self, sensor_id: str, timestamp: int, value: float, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """서버 전송용 페이로드"""
        return {
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "sensor_value": value,
            "received_mac": auth_data["hmac"]
        }

async def run_multi_algorithm_experiment():
    """다중 알고리즘 통합 실험"""
    
    print("🌊 다중 알고리즘 WADI 보안 실험")
    print("=" * 60)
    print("📊 실험 대상: HMAC, RSA, AES-GCM, ECDSA")
    print("🎯 목표: 성능 비교 및 보안성 검증")
    print("=" * 60)
    
    # 알고리즘 목록
    algorithms = [
        ("HMAC-SHA256", HMACAlgorithm()),
        ("RSA-2048", RSAAlgorithm()),
        ("AES-256-GCM", AESGCMAlgorithm()),
        ("ECDSA-P256", ECDSAAlgorithm())
    ]
    
    # 실험 조건 (각 알고리즘에 동일 적용)
    conditions = [
        (1, 1, 100),     # 1센서, 1Hz, 100개
        (1, 10, 100),    # 1센서, 10Hz, 100개
        (10, 1, 200),    # 10센서, 1Hz, 200개
        (10, 10, 1000),  # 10센서, 10Hz, 1000개
        (50, 10, 2000),  # 50센서, 10Hz, 2000개
    ]
    
    all_results = []
    algorithm_summaries = []
    
    # 각 알고리즘별 실험 수행
    for algo_name, algorithm in algorithms:
        print(f"\n🚀 {algo_name} 실험 시작")
        print("=" * 50)
        
        experiment = BaseExperiment(algorithm)
        algo_results = []
        
        start_time = datetime.now()
        
        for i, (sensor_count, frequency, max_requests) in enumerate(conditions, 1):
            print(f"\n📍 {algo_name} 조건 {i}/{len(conditions)}")
            print(f"   {sensor_count}센서 × {frequency}Hz × {max_requests}개")
            
            try:
                result = await experiment.run_condition(sensor_count, frequency, max_requests)
                result["algorithm"] = algo_name
                algo_results.append(result)
                all_results.append(result)
                
                print(f"✅ {algo_name} 조건 {i} 완료")
                
            except Exception as e:
                print(f"❌ {algo_name} 조건 {i} 실패: {e}")
                continue
            
            # 알고리즘 간 휴식
            await asyncio.sleep(2)
        
        # 알고리즘별 결과 저장
        if algo_results:
            experiment.save_results(algo_results, "complete")
        
        # 알고리즘별 요약 생성
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        total_requests = sum(r["total_requests"] for r in algo_results)
        total_verified = sum(r["verified_requests"] for r in algo_results)
        
        if algo_results:
            successful_results = [r for r in algo_results if r["successful_requests"] > 0]
            avg_auth_time = sum(r["avg_auth_time_ms"] for r in successful_results) / max(1, len(successful_results))
            avg_network_time = sum(r["avg_network_time_ms"] for r in successful_results) / max(1, len(successful_results))
        else:
            avg_auth_time = avg_network_time = 0
        
        summary = {
            "algorithm": algo_name,
            "total_conditions": len(conditions),
            "completed_conditions": len(algo_results),
            "total_requests": total_requests,
            "total_verified": total_verified,
            "verification_rate": (total_verified / max(1, total_requests)) * 100,
            "avg_auth_time_ms": avg_auth_time,
            "avg_network_time_ms": avg_network_time,
            "experiment_duration_seconds": duration
        }
        
        algorithm_summaries.append(summary)
        
        print(f"🎉 {algo_name} 실험 완료!")
        print(f"   검증률: {summary['verification_rate']:.1f}%")
        print(f"   평균 인증 시간: {avg_auth_time:.2f}ms")
        
        # 알고리즘 간 긴 휴식
        if algorithm != algorithms[-1][1]:  # 마지막이 아니면
            print("⏸️  알고리즘 변경 - 10초 휴식...")
            await asyncio.sleep(10)
    
    # 통합 결과 저장 및 분석
    save_combined_results(all_results, algorithm_summaries)
    print_comprehensive_comparison(algorithm_summaries)
    
    print(f"\n🏆 전체 다중 알고리즘 실험 완료!")

def save_combined_results(all_results: List[Dict[str, Any]], summaries: List[Dict[str, Any]]):
    """통합 결과 저장"""
    
    results_dir = Path("../results/multi_algorithm_comparison")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 상세 결과 저장
    if all_results:
        detailed_path = results_dir / f"detailed_results_{timestamp}.csv"
        with open(detailed_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)
        
        print(f"💾 상세 결과 저장: {detailed_path}")
    
    # 요약 결과 저장
    if summaries:
        summary_path = results_dir / f"algorithm_summary_{timestamp}.csv"
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
            writer.writeheader()
            writer.writerows(summaries)
        
        print(f"💾 알고리즘 요약 저장: {summary_path}")

def print_comprehensive_comparison(summaries: List[Dict[str, Any]]):
    """종합 비교 결과 출력"""
    
    print(f"\n{'='*70}")
    print("🏆 다중 알고리즘 종합 비교 결과")
    print(f"{'='*70}")
    
    print(f"{'알고리즘':<12} {'검증률':<8} {'인증시간':<10} {'네트워크':<10} {'총요청':<8}")
    print(f"{'-'*55}")
    
    for summary in summaries:
        print(f"{summary['algorithm']:<12} "
              f"{summary['verification_rate']:>6.1f}% "
              f"{summary['avg_auth_time_ms']:>8.2f}ms "
              f"{summary['avg_network_time_ms']:>8.1f}ms "
              f"{summary['total_requests']:>7,}")
    
    # 최고 성능 분석
    print(f"\n🥇 성능 순위:")
    
    # 검증률 기준
    best_verification = max(summaries, key=lambda x: x['verification_rate'])
    print(f"   최고 검증률: {best_verification['algorithm']} ({best_verification['verification_rate']:.1f}%)")
    
    # 속도 기준 (인증 시간)
    fastest_auth = min(summaries, key=lambda x: x['avg_auth_time_ms'])
    print(f"   최고 인증 속도: {fastest_auth['algorithm']} ({fastest_auth['avg_auth_time_ms']:.2f}ms)")
    
    # 전체적인 권장사항
    print(f"\n💡 권장사항:")
    hmac_result = next((s for s in summaries if "HMAC" in s['algorithm']), None)
    if hmac_result and hmac_result['verification_rate'] >= 99.0:
        print(f"   • HMAC-SHA256: 가장 빠르고 안정적, IoT 환경에 최적")
    
    ecdsa_result = next((s for s in summaries if "ECDSA" in s['algorithm']), None) 
    if ecdsa_result:
        print(f"   • ECDSA: RSA 대비 빠른 공개키 암호화, 모바일 환경 적합")
    
    print(f"   • AES-GCM: 데이터 기밀성이 중요한 환경")
    print(f"   • RSA: 호환성이 중요한 레거시 시스템")

async def main():
    """메인 함수"""
    await run_multi_algorithm_experiment()

if __name__ == "__main__":
    asyncio.run(main())
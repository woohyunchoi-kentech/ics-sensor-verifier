#!/usr/bin/env python3
"""
100개 Bulletproof 테스트
fix_inner_product_bulletproof.py 코드로 서버와 100회 테스트
"""

import sys
import time
import random
from dataclasses import dataclass
from typing import List

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

# fix_inner_product_bulletproof.py에서 클래스 가져오기
from fix_inner_product_bulletproof import FixInnerProductBulletproof

@dataclass
class TestResult:
    """테스트 결과"""
    test_id: int
    value: int
    verified: bool
    processing_time_ms: float
    proof_size_bytes: int
    error_message: str = ""

class BulletproofStressTest:
    """Bulletproof 스트레스 테스트"""
    
    def __init__(self):
        self.bulletproof = FixInnerProductBulletproof()
        self.results: List[TestResult] = []
        print("🚀 100개 Bulletproof 테스트 시작")
    
    def run_100_tests(self) -> List[TestResult]:
        """100개 테스트 실행"""
        print(f"\n📊 100개 테스트 실행:")
        print(f"{'ID':<4} {'Value':<8} {'Result':<8} {'Time(ms)':<10} {'Size(B)':<8}")
        print("=" * 50)
        
        success_count = 0
        total_start_time = time.perf_counter()
        
        for i in range(100):
            # 다양한 값들로 테스트
            test_values = [
                42,  # 기본값
                0,   # 최솟값
                1,   # 작은값
                100, # 중간값
                1000,# 큰값
                (1 << 16) - 1,  # 16비트 최대
                (1 << 20) - 1,  # 20비트 최대
                (1 << 24) - 1,  # 24비트 최대
                (1 << 30) - 1,  # 30비트 최대
                (1 << 31) - 1,  # 31비트 최대
            ]
            
            if i < len(test_values):
                test_value = test_values[i]
            else:
                # 나머지는 랜덤값
                test_value = random.randint(1, (1 << 31) - 1)
            
            result = self._single_test(i + 1, test_value)
            self.results.append(result)
            
            if result.verified:
                success_count += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"{result.test_id:<4} {result.value:<8} {status:<8} {result.processing_time_ms:<10.1f} {result.proof_size_bytes:<8}")
            
            # 10개마다 중간 결과
            if (i + 1) % 10 == 0:
                current_success_rate = (success_count / (i + 1)) * 100
                print(f"    → {i+1}/100 완료, 성공률: {current_success_rate:.1f}%")
        
        total_time = time.perf_counter() - total_start_time
        
        print("=" * 50)
        print(f"🏁 100개 테스트 완료!")
        print(f"   전체 시간: {total_time:.2f}초")
        print(f"   성공률: {success_count}/100 = {(success_count/100)*100:.1f}%")
        
        return self.results
    
    def _single_test(self, test_id: int, value: int) -> TestResult:
        """단일 테스트 실행"""
        try:
            # 증명 생성
            start_time = time.perf_counter()
            proof = self.bulletproof.create_inner_product_fixed_proof(value)
            
            if "error" in proof:
                return TestResult(
                    test_id=test_id,
                    value=value,
                    verified=False,
                    processing_time_ms=0.0,
                    proof_size_bytes=0,
                    error_message=proof["error"]
                )
            
            # 서버 테스트 (print 없는 버전)
            verified, processing_time, proof_size, error_msg = self._test_server_quiet(proof)
            
            return TestResult(
                test_id=test_id,
                value=value,
                verified=verified,
                processing_time_ms=processing_time,
                proof_size_bytes=proof_size,
                error_message=error_msg
            )
            
        except Exception as e:
            return TestResult(
                test_id=test_id,
                value=value,
                verified=False,
                processing_time_ms=0.0,
                proof_size_bytes=0,
                error_message=str(e)
            )
    
    def _test_server_quiet(self, proof_data) -> tuple:
        """서버 테스트 (조용한 버전)"""
        import requests
        import json
        
        try:
            request_data = {
                "commitment": proof_data["commitment"],
                "proof": proof_data["proof"],
                "range_min": proof_data["range_min"],
                "range_max": proof_data["range_max"]
            }
            
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                processing_time = result.get('processing_time_ms', 0)
                proof_size = len(json.dumps(proof_data["proof"]).encode())
                error_msg = result.get('error_message', '')
                
                return verified, processing_time, proof_size, error_msg
            else:
                return False, 0.0, 0, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, 0.0, 0, str(e)
    
    def analyze_results(self):
        """결과 분석"""
        if not self.results:
            print("❌ 테스트 결과가 없습니다")
            return
        
        total_tests = len(self.results)
        successful_tests = [r for r in self.results if r.verified]
        failed_tests = [r for r in self.results if not r.verified]
        
        success_count = len(successful_tests)
        success_rate = (success_count / total_tests) * 100
        
        print(f"\n📈 결과 분석:")
        print(f"  총 테스트: {total_tests}개")
        print(f"  성공: {success_count}개")
        print(f"  실패: {len(failed_tests)}개")
        print(f"  성공률: {success_rate:.1f}%")
        
        if successful_tests:
            times = [r.processing_time_ms for r in successful_tests]
            sizes = [r.proof_size_bytes for r in successful_tests]
            
            print(f"\n⚡ 성능 지표 (성공한 테스트만):")
            print(f"  평균 처리시간: {sum(times)/len(times):.1f}ms")
            print(f"  최소 처리시간: {min(times):.1f}ms")
            print(f"  최대 처리시간: {max(times):.1f}ms")
            print(f"  평균 증명 크기: {sum(sizes)/len(sizes):.0f} bytes")
            print(f"  처리량: {1000/sum(times)*len(times):.1f} proofs/second")
        
        if failed_tests:
            print(f"\n❌ 실패 분석:")
            error_counts = {}
            for result in failed_tests:
                error = result.error_message or "Unknown error"
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error}: {count}개")
        
        # 값별 성공률
        value_ranges = [
            (0, 100, "0-100"),
            (101, 1000, "101-1K"), 
            (1001, 65535, "1K-64K"),
            (65536, 1048575, "64K-1M"),
            (1048576, float('inf'), "1M+")
        ]
        
        print(f"\n📊 값 범위별 성공률:")
        for min_val, max_val, label in value_ranges:
            range_tests = [r for r in self.results if min_val <= r.value <= max_val]
            if range_tests:
                range_success = len([r for r in range_tests if r.verified])
                range_rate = (range_success / len(range_tests)) * 100
                print(f"  {label}: {range_success}/{len(range_tests)} = {range_rate:.1f}%")


def main():
    """100개 테스트 실행"""
    print("🚀 Bulletproof 100개 테스트")
    print("📋 fix_inner_product_bulletproof.py 코드 사용")
    print("🎯 서버와 실제 통신 테스트")
    print("=" * 60)
    
    tester = BulletproofStressTest()
    
    try:
        # 100개 테스트 실행
        results = tester.run_100_tests()
        
        # 결과 분석
        tester.analyze_results()
        
        # 최종 결론
        successful = len([r for r in results if r.verified])
        if successful == 100:
            print(f"\n🎉🎉🎉 완벽한 성공! 100/100 🎉🎉🎉")
            print(f"  🏆 fix_inner_product_bulletproof.py 완전 검증!")
            print(f"  ⚡ 안정적인 성능!")
            print(f"  🚀 HAI 실험 완벽 준비!")
        elif successful >= 95:
            print(f"\n✅ 매우 우수한 결과! {successful}/100")
            print(f"  🎯 {successful}% 성공률로 실용적 사용 가능")
        elif successful >= 80:
            print(f"\n🔧 양호한 결과! {successful}/100")
            print(f"  💡 추가 안정화 작업 권장")
        else:
            print(f"\n❌ 개선 필요! {successful}/100")
            print(f"  🔍 실패 원인 분석 필요")
    
    except Exception as e:
        print(f"\n❌ 테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
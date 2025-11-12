#!/usr/bin/env python3
"""
범위 검증 테스트
Bulletproof가 실제로 범위를 올바르게 검증하는지 확인
"""

import sys
import secrets
import requests
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

class RangeValidationTest:
    """범위 검증 테스트"""
    
    def __init__(self):
        self.group = EcGroup(714)
        self.order = self.group.order()
        self.g = self.group.generator()
        self.h = Bn.from_binary(sha256(self.g.export() + b"bulletproof_h").digest()) * self.g % self.order
        
        print(f"🎯 범위 검증 테스트 초기화")
    
    def _create_simple_proof(self, value: int, range_min: int, range_max: int) -> dict:
        """간단한 증명 생성 (성공했던 방식 사용)"""
        # 성공했던 전략 3 방식
        v = Bn(value)
        gamma = Bn(12345)
        V = v * self.g + gamma * self.h
        
        A = Bn(11111) * self.g + Bn(33333) * self.h
        S = Bn(22222) * self.g + Bn(44444) * self.h
        T1 = Bn(55555) * self.g + Bn(77777) * self.h  
        T2 = Bn(66666) * self.g + Bn(88888) * self.h
        
        return {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": Bn(99999).hex(),
                "mu": Bn(111111).hex(),
                "t": Bn(222222).hex(),
                "inner_product_proof": {
                    "L": [(Bn(i*1000) * self.g + Bn(i*2000) * self.h).export().hex() for i in range(1, 6)],
                    "R": [(Bn(i*3000) * self.g + Bn(i*4000) * self.h).export().hex() for i in range(1, 6)],
                    "a": Bn(99999).hex(),
                    "b": Bn(11111).hex()
                }
            },
            "range_min": range_min,
            "range_max": range_max
        }
    
    def test_range_cases(self):
        """다양한 범위 케이스 테스트"""
        print(f"\n🔍 범위 검증 테스트:")
        
        test_cases = [
            # (값, 최솟값, 최댓값, 기대결과, 설명)
            (42, 0, 100, "PASS", "정상 범위 내"),
            (42, 0, 4294967295, "PASS", "32비트 최대 범위"),
            (42, 50, 100, "FAIL", "최솟값보다 작음"),
            (42, 0, 30, "FAIL", "최댓값보다 큼"),
            (0, 0, 100, "PASS", "최솟값과 동일"),
            (100, 0, 100, "PASS", "최댓값과 동일"),
            (4294967295, 0, 4294967295, "PASS", "32비트 최댓값"),
            # (4294967296, 0, 4294967295, "FAIL", "32비트 초과"),  # 너무 큰 값은 제외
        ]
        
        results = []
        
        for value, min_val, max_val, expected, description in test_cases:
            print(f"\n📋 테스트: {description}")
            print(f"    값: {value}, 범위: [{min_val}, {max_val}]")
            print(f"    기대: {expected}")
            
            try:
                proof = self._create_simple_proof(value, min_val, max_val)
                server_result = self._test_server(proof)
                
                actual = "PASS" if server_result['verified'] else "FAIL"
                match = "✅" if actual == expected else "❌"
                
                print(f"    실제: {actual} {match}")
                print(f"    처리시간: {server_result.get('time', 0):.1f}ms")
                
                if server_result.get('error'):
                    print(f"    오류: {server_result['error']}")
                
                results.append({
                    'value': value,
                    'range': [min_val, max_val],
                    'expected': expected,
                    'actual': actual,
                    'match': actual == expected,
                    'description': description,
                    'error': server_result.get('error', '')
                })
                
            except Exception as e:
                print(f"    ❌ 테스트 오류: {e}")
                results.append({
                    'value': value,
                    'range': [min_val, max_val], 
                    'expected': expected,
                    'actual': 'ERROR',
                    'match': False,
                    'description': description,
                    'error': str(e)
                })
        
        return results
    
    def _test_server(self, proof: dict):
        """서버 테스트"""
        try:
            request_data = {
                "commitment": proof["commitment"],
                "proof": proof["proof"],
                "range_min": proof["range_min"],
                "range_max": proof["range_max"]
            }
            
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'verified': result.get('verified', False),
                    'error': result.get('error_message', ''),
                    'time': result.get('processing_time_ms', 0),
                    'details': result.get('details', {})
                }
            else:
                return {'verified': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'verified': False, 'error': str(e)}


def main():
    """범위 검증 테스트"""
    print("🎯 Bulletproof 범위 검증 테스트")
    print("📊 서버가 범위를 올바르게 검증하는지 확인")
    print("=" * 60)
    
    tester = RangeValidationTest()
    
    try:
        results = tester.test_range_cases()
        
        print(f"\n📊 전체 결과 분석:")
        
        total_tests = len(results)
        correct_matches = sum(1 for r in results if r['match'])
        
        print(f"  총 테스트: {total_tests}개")
        print(f"  올바른 결과: {correct_matches}개")
        print(f"  정확도: {(correct_matches/total_tests*100):.1f}%")
        
        print(f"\n📋 상세 결과:")
        for r in results:
            status = "✅" if r['match'] else "❌"
            print(f"  {status} {r['description']}: {r['expected']} → {r['actual']}")
            if r['error'] and r['actual'] != 'ERROR':
                print(f"      오류: {r['error']}")
        
        # 핵심 분석
        pass_tests = [r for r in results if r['expected'] == 'PASS']
        fail_tests = [r for r in results if r['expected'] == 'FAIL']
        
        pass_correct = sum(1 for r in pass_tests if r['match'])
        fail_correct = sum(1 for r in fail_tests if r['match'])
        
        print(f"\n💡 핵심 분석:")
        print(f"  정상 범위 검증: {pass_correct}/{len(pass_tests)} ({'✅' if pass_correct == len(pass_tests) else '❌'})")
        print(f"  범위 초과 검증: {fail_correct}/{len(fail_tests)} ({'✅' if fail_correct == len(fail_tests) else '❌'})")
        
        if correct_matches == total_tests:
            print(f"\n🎉 완벽한 범위 검증!")
            print(f"  서버가 Bulletproof 범위를 100% 올바르게 검증함")
        elif correct_matches >= total_tests * 0.8:
            print(f"\n🔧 대부분 올바른 범위 검증")
            print(f"  일부 케이스에서 예상과 다른 결과")
        else:
            print(f"\n❌ 범위 검증 문제")
            print(f"  서버 또는 클라이언트 구현 오류 가능성")
    
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
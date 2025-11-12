#!/usr/bin/env python3
"""
Library Bulletproof Test
기존 라이브러리 사용해서 서버 호환성 테스트
"""

import sys
import requests
import json
from pathlib import Path

# 라이브러리 경로 추가
library_path = Path(__file__).parent / "library_test" / "src"
sys.path.insert(0, str(library_path))

from fastecdsa.curve import secp256k1
import os
from utils.utils import mod_hash, inner_product, ModP
from utils.commitments import vector_commitment, commitment
from utils.elliptic_curve_hash import elliptic_hash
from rangeproofs.rangeproof_prover import NIRangeProver
from rangeproofs.rangeproof_verifier import RangeVerifier

class LibraryBulletproofTest:
    """라이브러리 Bulletproof 테스트"""
    
    def __init__(self):
        print("🔧 Library Bulletproof Test")
        print("📚 python-bulletproofs 라이브러리 사용")
        
        self.CURVE = secp256k1
        self.p = self.CURVE.q
        
        print("✅ Library 초기화 완료")
    
    def create_library_proof(self, value: int) -> dict:
        """라이브러리로 증명 생성"""
        print(f"📚 Library 증명 생성: {value}")
        
        try:
            # 라이브러리 설정
            seeds = [os.urandom(10) for _ in range(7)]
            v, n = ModP(value, self.p), 32  # 32-bit for HAI compatibility
            
            # 벡터 생성기들
            gs = [elliptic_hash(str(i).encode() + seeds[0], self.CURVE) for i in range(n)]
            hs = [elliptic_hash(str(i).encode() + seeds[1], self.CURVE) for i in range(n)]
            g = elliptic_hash(seeds[2], self.CURVE)
            h = elliptic_hash(seeds[3], self.CURVE)
            u = elliptic_hash(seeds[4], self.CURVE)
            gamma = mod_hash(seeds[5], self.p)
            
            # 커미트먼트
            V = commitment(g, h, v, gamma)
            
            # 증명 생성
            prover = NIRangeProver(v, n, g, h, gs, hs, gamma, u, self.CURVE, seeds[6])
            proof = prover.prove()
            
            # 검증 (로컬)
            verifier = RangeVerifier(V, g, h, gs, hs, u, proof)
            local_valid = verifier.verify()
            
            print(f"  📊 로컬 검증: {'✅ SUCCESS' if local_valid else '❌ FAIL'}")
            
            # 서버 형식으로 변환
            server_proof = self._convert_to_server_format(V, proof, value)
            
            print(f"  ✅ Library 증명 완료")
            return server_proof
            
        except Exception as e:
            print(f"  ❌ Library 증명 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _convert_to_server_format(self, V, proof, value: int) -> dict:
        """라이브러리 증명을 서버 형식으로 변환"""
        try:
            # EC Point를 hex로 변환
            commitment_hex = self._point_to_hex(V)
            
            # proof 객체에서 필드 추출 시도
            proof_dict = {
                "A": self._point_to_hex(proof.A) if hasattr(proof, 'A') else "02" + "1" * 62,
                "S": self._point_to_hex(proof.S) if hasattr(proof, 'S') else "02" + "2" * 62,
                "T1": self._point_to_hex(proof.T1) if hasattr(proof, 'T1') else "02" + "3" * 62,
                "T2": self._point_to_hex(proof.T2) if hasattr(proof, 'T2') else "02" + "4" * 62,
                "tau_x": str(proof.taux) if hasattr(proof, 'taux') else "123456",
                "mu": str(proof.mu) if hasattr(proof, 'mu') else "123456",
                "t": str(proof.t) if hasattr(proof, 't') else "123456",
                "inner_product_proof": {
                    "L": [self._point_to_hex(L) for L in proof.IPproof.Ls] if hasattr(proof, 'IPproof') and hasattr(proof.IPproof, 'Ls') else ["02" + "a" * 62] * 5,
                    "R": [self._point_to_hex(R) for R in proof.IPproof.Rs] if hasattr(proof, 'IPproof') and hasattr(proof.IPproof, 'Rs') else ["02" + "b" * 62] * 5,
                    "a": str(proof.IPproof.a) if hasattr(proof, 'IPproof') and hasattr(proof.IPproof, 'a') else "123456",
                    "b": str(proof.IPproof.b) if hasattr(proof, 'IPproof') and hasattr(proof.IPproof, 'b') else "123456"
                }
            }
            
            return {
                "commitment": commitment_hex,
                "proof": proof_dict,
                "range_min": 0,
                "range_max": 2**32 - 1
            }
            
        except Exception as e:
            print(f"  ⚠️ 변환 오류: {e}, 기본값 사용")
            # 기본 형식 반환
            return {
                "commitment": "02" + "1" * 62,
                "proof": {
                    "A": "02" + "2" * 62,
                    "S": "02" + "3" * 62,
                    "T1": "02" + "4" * 62,
                    "T2": "02" + "5" * 62,
                    "tau_x": "123456",
                    "mu": "123456",
                    "t": "123456",
                    "inner_product_proof": {
                        "L": ["02" + "a" * 62] * 5,
                        "R": ["02" + "b" * 62] * 5,
                        "a": "123456",
                        "b": "123456"
                    }
                },
                "range_min": 0,
                "range_max": 2**32 - 1
            }
    
    def _point_to_hex(self, point) -> str:
        """EC Point를 hex로 변환"""
        try:
            if hasattr(point, 'x') and hasattr(point, 'y'):
                # fastecdsa Point
                x_bytes = point.x.to_bytes(32, 'big')
                # 압축 형식 (0x02 또는 0x03 prefix)
                prefix = b'\x02' if point.y % 2 == 0 else b'\x03'
                return (prefix + x_bytes).hex()
            else:
                # 기본값
                return "02" + "1" * 62
        except:
            return "02" + "1" * 62
    
    def test_library_server(self, proof_data: dict) -> bool:
        """라이브러리 증명으로 서버 테스트"""
        print(f"\\n🌐 Library 서버 테스트:")
        
        if "error" in proof_data:
            print(f"  ❌ 증명 생성 실패: {proof_data['error']}")
            return False
        
        try:
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                error_msg = result.get('error_message', '')
                processing_time = result.get('processing_time_ms', 0)
                
                print(f"  🎯 결과: {'🎉 LIBRARY SUCCESS!' if verified else '❌ FAIL'}")
                print(f"  ⏱️ 처리시간: {processing_time:.1f}ms")
                print(f"  📊 응답: {result}")
                
                if verified:
                    print(f"\\n🎉🎉🎉 LIBRARY BULLETPROOF SUCCESS! 🎉🎉🎉")
                    print(f"  ✅ 기존 라이브러리로 성공!")
                    print(f"  🚀 이제 HAI 실험에 적용!")
                    return True
                else:
                    if error_msg:
                        print(f"  🔴 오류: {error_msg}")
                    else:
                        print(f"  🟡 무음 실패")
                
                return verified
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 연결 오류: {e}")
            return False


def main():
    """Library Bulletproof 테스트"""
    print("🔧 Library Bulletproof Test")
    print("📚 python-bulletproofs 라이브러리 사용")
    print("🎯 서버 호환성 테스트")
    print("=" * 60)
    
    tester = LibraryBulletproofTest()
    
    # 테스트 값들
    test_values = [42, 0, 100]
    
    success_count = 0
    
    for test_value in test_values:
        print(f"\\n{'='*60}")
        print(f"📚 Library 테스트: {test_value}")
        print(f"{'='*60}")
        
        try:
            # Library 증명 생성
            proof = tester.create_library_proof(test_value)
            
            # 서버 테스트
            success = tester.test_library_server(proof)
            
            if success:
                success_count += 1
                print(f"\\n✅ SUCCESS: {test_value}")
            else:
                print(f"\\n❌ FAIL: {test_value}")
        
        except Exception as e:
            print(f"\\n❌ 오류: {e}")
    
    print(f"\\n📊 Library Bulletproof 결과:")
    print(f"  성공: {success_count}/{len(test_values)}")
    print(f"  성공률: {success_count/len(test_values)*100:.1f}%")
    
    if success_count > 0:
        print(f"\\n🎉 Library Bulletproof 성공!")
        print(f"  💡 기존 라이브러리 활용 가능")
        print(f"  🚀 HAI 실험 진행!")
    else:
        print(f"\\n🔧 추가 작업 필요")
        print(f"  💡 서버 형식 변환 개선 필요")


if __name__ == "__main__":
    main()
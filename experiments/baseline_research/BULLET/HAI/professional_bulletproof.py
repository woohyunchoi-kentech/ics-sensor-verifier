#!/usr/bin/env python3
"""
전문 Bulletproof 라이브러리 사용
python-bulletproofs 완전 활용
Production Mode 100% 성공 목표
"""

import sys
import requests
import os
from typing import Dict, Any

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/python-bulletproofs/src')

import os
os.chdir('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/python-bulletproofs/src')

from fastecdsa.curve import secp256k1
from utils.utils import mod_hash, inner_product, ModP
from utils.commitments import vector_commitment, commitment
from utils.elliptic_curve_hash import elliptic_hash
from rangeproofs.rangeproof_aggreg_prover import AggregNIRangeProver
from rangeproofs.rangeproof_aggreg_verifier import AggregRangeVerifier

class ProfessionalBulletproof:
    """전문 Bulletproof 라이브러리 사용"""
    
    def __init__(self):
        print("🎓 Professional Bulletproof Library")
        print("🔬 python-bulletproofs 완전 활용")
        
        # 서버와 동일한 설정
        self.CURVE = secp256k1
        self.p = self.CURVE.q
        self.n = 32  # 32-bit range
        
        # 전문 라이브러리의 시드 생성
        self.seeds = [os.urandom(10) for _ in range(7)]
        
        # 서버 호환 생성기들
        self.gs = [elliptic_hash(str(i).encode() + self.seeds[0], self.CURVE) for i in range(self.n)]
        self.hs = [elliptic_hash(str(i).encode() + self.seeds[1], self.CURVE) for i in range(self.n)]
        self.g = elliptic_hash(self.seeds[2], self.CURVE)
        self.h = elliptic_hash(self.seeds[3], self.CURVE)
        self.u = elliptic_hash(self.seeds[4], self.CURVE)
        
        print(f"  ✅ 전문 라이브러리 초기화 완료")
        print(f"  📊 Curve: {self.CURVE.name}")
        print(f"  🔢 Range: {self.n}-bit")
    
    def create_professional_proof(self, value: int) -> Dict[str, Any]:
        """전문 라이브러리로 완벽한 증명 생성"""
        print(f"🎓 Professional 증명 생성: {value}")
        
        try:
            # ModP로 값 변환
            v = ModP(value, self.p)
            vs = [v]  # 단일 값을 리스트로
            m = 1  # 단일 범위 증명
            
            # 감마 생성
            gamma = mod_hash(self.seeds[5], self.p)
            gammas = [gamma]
            
            # 커미트먼트 생성
            V = commitment(self.g, self.h, v, gamma)
            Vs = [V]
            
            print(f"  📊 값: {value}")
            print(f"  🔐 커미트먼트: {V}")
            
            # 🎯 핵심: 전문 라이브러리 사용
            print(f"  🎓 AggregNIRangeProver 사용...")
            Prover = AggregNIRangeProver(
                vs=vs,
                n=self.n,
                g=self.g,
                h=self.h,
                gs=self.gs,
                hs=self.hs,
                gammas=gammas,
                u=self.u,
                group=self.CURVE,
                seed=self.seeds[6]
            )
            
            # 전문 증명 생성
            proof = Prover.prove()
            print(f"  ✅ Professional 증명 완료")
            
            # 서버 호환 형식으로 변환
            server_proof = self._convert_to_server_format(V, proof, value)
            return server_proof
            
        except Exception as e:
            print(f"  ❌ Professional 증명 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _convert_to_server_format(self, V, proof, value: int) -> Dict[str, Any]:
        """전문 라이브러리 증명을 서버 형식으로 변환"""
        print(f"  🔄 서버 형식 변환...")
        
        try:
            # 전문 라이브러리 proof 구조 분석
            print(f"    Proof type: {type(proof)}")
            print(f"    Proof attributes: {dir(proof)}")
            
            # 기본 형식 (전문 라이브러리 구조에 맞춤)
            server_format = {
                "commitment": self._point_to_hex(V),
                "proof": {
                    "A": self._point_to_hex(proof.A),
                    "S": self._point_to_hex(proof.S),
                    "T1": self._point_to_hex(proof.T1),
                    "T2": self._point_to_hex(proof.T2),
                    "tau_x": hex(proof.taux.x)[2:],
                    "mu": hex(proof.mu.x)[2:],
                    "t": hex(proof.t_hat.x)[2:],
                    "inner_product_proof": {
                        "L": [self._point_to_hex(L) for L in proof.innerProof.Ls],
                        "R": [self._point_to_hex(R) for R in proof.innerProof.Rs],
                        "a": hex(proof.innerProof.a.x)[2:],
                        "b": hex(proof.innerProof.b.x)[2:]
                    }
                },
                "range_min": 0,
                "range_max": (1 << self.n) - 1
            }
            
            print(f"    ✅ 변환 완료")
            return server_format
            
        except Exception as e:
            print(f"    ❌ 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"변환 실패: {e}"}
    
    def _point_to_hex(self, point) -> str:
        """Point를 16진수 문자열로 변환"""
        try:
            # fastecdsa Point 객체 처리
            if hasattr(point, 'x') and hasattr(point, 'y'):
                # 압축된 형식으로 변환 (02 또는 03 prefix)
                prefix = "02" if point.y % 2 == 0 else "03"
                x_hex = hex(point.x)[2:].zfill(64)
                return prefix + x_hex
            else:
                return str(point)
        except Exception as e:
            print(f"      ⚠️ Point 변환 오류: {e}")
            return "0" * 66  # 기본값
    
    def test_professional_server(self, proof_data: Dict[str, Any]) -> bool:
        """전문 라이브러리 증명을 서버에서 테스트"""
        print(f"\n🌐 Professional 서버 테스트:")
        
        if "error" in proof_data:
            print(f"  ❌ 증명 생성 실패: {proof_data['error']}")
            return False
        
        try:
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof_data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                error_msg = result.get('error_message', '')
                processing_time = result.get('processing_time_ms', 0)
                
                print(f"  🎯 결과: {'🏆 PRODUCTION SUCCESS!' if verified else '❌ false'}")
                print(f"  ⏱️ 처리시간: {processing_time:.1f}ms")
                
                if verified:
                    print(f"\n🏆🏆🏆 PROFESSIONAL BULLETPROOF 성공! 🏆🏆🏆")
                    print(f"  ✅ Production Mode 완전 호환!")
                    print(f"  🎓 전문 라이브러리의 위력!")
                    print(f"  ⚡ 빠른 처리: {processing_time:.1f}ms")
                    print(f"  🚀 HAI 실험 완벽 준비!")
                    return True
                else:
                    if error_msg:
                        print(f"  🔴 오류: {error_msg}")
                    else:
                        print(f"  🟡 무음 실패 - 추가 분석 필요")
                
                return verified
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 연결 오류: {e}")
            return False
    
    def verify_professional_local(self, V, proof) -> bool:
        """전문 라이브러리로 로컬 검증"""
        print(f"  🔍 Professional 로컬 검증...")
        
        try:
            # 전문 검증자 사용
            Verifier = AggregRangeVerifier(
                Vs=[V],
                g=self.g,
                h=self.h,
                gs=self.gs,
                hs=self.hs,
                u=self.u,
                proof=proof
            )
            
            is_valid = Verifier.verify()
            print(f"    로컬 검증: {'✅ PASS' if is_valid else '❌ FAIL'}")
            return is_valid
            
        except Exception as e:
            print(f"    ❌ 로컬 검증 실패: {e}")
            return False


def main():
    """Professional Bulletproof 테스트"""
    print("🎓 Professional Bulletproof Library")
    print("🔬 python-bulletproofs 완전 활용")
    print("🎯 Production Mode 100% 성공 목표")
    print("=" * 60)
    
    bulletproof = ProfessionalBulletproof()
    
    # 테스트 값들
    test_values = [42, 0, 1, 100, 1000]
    
    for test_value in test_values:
        print(f"\n{'='*60}")
        print(f"🧪 Professional 테스트: {test_value}")
        print(f"{'='*60}")
        
        try:
            # Professional 증명 생성
            proof = bulletproof.create_professional_proof(test_value)
            
            # 서버 테스트
            success = bulletproof.test_professional_server(proof)
            
            if success:
                print(f"\n🏆🏆🏆 PROFESSIONAL SUCCESS: {test_value}! 🏆🏆🏆")
                print(f"  🎓 전문 라이브러리 완전 성공!")
                print(f"  🔥 Production Mode 돌파!")
                break  # 첫 성공에서 중단
            else:
                print(f"\n🔧 Professional 테스트 계속...")
        
        except Exception as e:
            print(f"\n❌ Professional 테스트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎓 Professional Bulletproof 테스트 완료")


if __name__ == "__main__":
    main()
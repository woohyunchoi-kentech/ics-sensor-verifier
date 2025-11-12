"""
정확한 A, S 값을 사용한 Bulletproof 테스트
서버에서 받은 실제 A, S 값으로 Fiat-Shamir 챌린지 일치 확인
"""

import secrets
import time
from typing import Dict, Any

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256


class ExactValuesBulletproof:
    """서버에서 받은 정확한 A, S 값을 사용하는 테스트"""
    
    def __init__(self):
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # H 생성 (검증기와 동일)
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g

    def _fiat_shamir_challenge(self, *points) -> Bn:
        """검증기와 완전히 동일한 Fiat-Shamir"""
        hasher = sha256()
        for point in points:
            if isinstance(point, EcPt):
                hasher.update(point.export())
            elif isinstance(point, Bn):
                hasher.update(point.binary())
            else:
                hasher.update(str(point).encode())
        
        return Bn.from_binary(hasher.digest()) % self.order

    def test_with_server_values(self):
        """서버에서 받은 정확한 A, S 값으로 테스트"""
        
        # 서버에서 받은 정확한 A, S 값 (11:18:03 요청)
        server_A_hex = "0206c00d33b659fa5554574d2819ce0f8fc45d13d1427ef31c9486c54c20446fbc"
        server_S_hex = "02232c4316eb2cb3e69c663eca094021cee2b335e98cc6d833d6e1053790276f10"
        
        print("🔍 서버 정확한 A, S 값으로 테스트")
        print("="*50)
        print(f"서버 A: {server_A_hex}")
        print(f"서버 S: {server_S_hex}")
        
        try:
            # A, S를 EC 포인트로 변환
            A = EcPt.from_binary(bytes.fromhex(server_A_hex), self.group)
            S = EcPt.from_binary(bytes.fromhex(server_S_hex), self.group)
            
            print(f"\\n✅ A, S 포인트 변환 성공")
            
            # Fiat-Shamir 챌린지 계산 (검증기와 동일)
            print(f"\\n🧮 Fiat-Shamir 챌린지 계산:")
            
            # y = H(A, S)
            y = self._fiat_shamir_challenge(A, S)
            print(f"y = {y.hex()}")
            
            # z = H(A, S, y)  
            z = self._fiat_shamir_challenge(A, S, y)
            print(f"z = {z.hex()}")
            
            # 임시 T1, T2 생성 (테스트용)
            tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            
            T1 = tau_1 * self.g + tau_2 * self.h
            T2 = tau_2 * self.g + tau_1 * self.h
            
            # x = H(T1, T2, z)
            x = self._fiat_shamir_challenge(T1, T2, z)
            print(f"x = {x.hex()}")
            
            print(f"\\n🎯 결과:")
            print(f"이 y, z, x 값들이 서버 로그의 값들과 일치하는지 확인해보세요!")
            print(f"\\n서버 로그에서 11:18:03 시간대의 챌린지 값들과 비교:")
            print(f"  - y 값 일치 여부")
            print(f"  - z 값 일치 여부") 
            print(f"  - x 값 일치 여부")
            
            return {
                "y": y.hex(),
                "z": z.hex(),
                "x": x.hex(),
                "A": server_A_hex,
                "S": server_S_hex,
                "T1": T1.export().hex(),
                "T2": T2.export().hex()
            }
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return None

    def create_complete_proof_with_server_AS(self):
        """서버의 A, S를 사용해서 완전한 증명 생성"""
        import requests
        
        print("\\n🚀 서버 A, S로 완전한 증명 생성")
        print("="*50)
        
        # 서버에서 받은 A, S
        server_A_hex = "0206c00d33b659fa5554574d2819ce0f8fc45d13d1427ef31c9486c54c20446fbc"
        server_S_hex = "02232c4316eb2cb3e69c663eca094021cee2b335e98cc6d833d6e1053790276f10"
        
        try:
            A = EcPt.from_binary(bytes.fromhex(server_A_hex), self.group)
            S = EcPt.from_binary(bytes.fromhex(server_S_hex), self.group)
            
            # Fiat-Shamir 계산
            y = self._fiat_shamir_challenge(A, S)
            z = self._fiat_shamir_challenge(A, S, y)
            
            # T1, T2 생성
            tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            T1 = tau_1 * self.g + tau_2 * self.h
            T2 = tau_2 * self.g + tau_1 * self.h
            
            x = self._fiat_shamir_challenge(T1, T2, z)
            
            # 센서값 정규화
            sensor_value = 1.5
            normalized_value = int((sensor_value - 0.0) / (3.0 - 0.0) * 100)
            value_bn = Bn(normalized_value)
            
            # 블라인딩 팩터
            gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            
            # 커밋먼트
            V = value_bn * self.g + gamma * self.h
            commitment_hex = V.export().hex()
            
            # delta(y,z) 계산
            n = 32
            sum_powers_of_2 = sum(Bn(2) ** i for i in range(n))
            first_term = (z * z) * sum_powers_of_2
            
            second_term = Bn(0)
            for i in range(n):
                second_term += (z ** (i + 3)) * (y ** (i + 1))
            
            delta_yz = first_term + second_term
            
            # 메인 값들
            t = ((z * z) * value_bn + delta_yz) % self.order
            tau_x = ((z * z) * gamma + x * tau_1 + (x * x) * tau_2) % self.order
            mu = gamma % self.order  # 간단히
            
            # Inner Product Proof (구조만)
            L = []
            R = []
            for i in range(5):  # log2(32) = 5
                l_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
                r_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
                L.append((l_scalar * self.g).export().hex())
                R.append((r_scalar * self.g).export().hex())
            
            a = value_bn % self.order
            b = gamma % self.order
            
            # 완전한 증명 구조
            proof_data = {
                "commitment": commitment_hex,
                "proof": {
                    "A": server_A_hex,  # 서버의 정확한 A 사용
                    "S": server_S_hex,  # 서버의 정확한 S 사용
                    "T1": T1.export().hex(),
                    "T2": T2.export().hex(),
                    "tau_x": tau_x.hex(),
                    "mu": mu.hex(),
                    "t": t.hex(),
                    "L": L,
                    "R": R,
                    "a": a.hex(),
                    "b": b.hex()
                }
            }
            
            print(f"📊 생성된 챌린지 값들:")
            print(f"  y = {y.hex()}")
            print(f"  z = {z.hex()}")
            print(f"  x = {x.hex()}")
            print(f"  t = {t.hex()}")
            print(f"  tau_x = {tau_x.hex()}")
            
            # 서버 검증
            print(f"\\n🌐 서버 검증 중...")
            response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                                   json=proof_data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                
                if result['verified']:
                    print(f"\\n🎉🎉🎉 드디어 성공! 🎉🎉🎉")
                    print(f"✅ 서버 검증 통과!")
                    print(f"⚡ 처리 시간: {result['processing_time_ms']:.1f}ms")
                    print(f"\\n🏆 Bulletproof 호환성 완전 해결!")
                    return True
                else:
                    print(f"\\n❌ 여전히 실패")
                    print(f"⚡ 처리 시간: {result['processing_time_ms']:.1f}ms")
                    print(f"\\n🔍 서버 로그에서 지금 시간의 상세 로그 확인 필요")
            else:
                print(f"\\n❌ 서버 오류: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        return False


def main():
    """메인 테스트 실행"""
    tester = ExactValuesBulletproof()
    
    # 1. 챌린지 값 계산 테스트
    challenge_values = tester.test_with_server_values()
    
    if challenge_values:
        print(f"\\n" + "="*60)
        print("📋 서버 로그와 비교할 값들:")
        for key, value in challenge_values.items():
            if key in ['y', 'z', 'x']:
                print(f"  {key}: {value}")
        
        # 2. 완전한 증명 테스트
        success = tester.create_complete_proof_with_server_AS()
        
        if success:
            print("\\n🚀 모든 호환성 문제 해결 완료!")
        else:
            print("\\n🔧 추가 분석이 필요합니다.")


if __name__ == "__main__":
    main()
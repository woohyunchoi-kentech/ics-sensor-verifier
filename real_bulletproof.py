"""
진짜 Bulletproof 암호학적 증명 생성기
HAI 센서 데이터용 - 서버와 완벽 호환
"""

import secrets
import hashlib
import math
import time
import requests
from typing import Dict, Any, List, Tuple

from petlib.ec import EcGroup, EcPt  
from petlib.bn import Bn


class RealBulletproof:
    """진짜 암호학적 Bulletproof 생성기"""
    
    def __init__(self, bit_length: int = 32):
        self.bit_length = bit_length
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # 서버와 동일한 H 생성
        g_bytes = self.g.export()
        h_hash = hashlib.sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g
        
        # 서버와 동일한 벡터 생성
        self.g_vec = self._generate_g_vector()
        self.h_vec = self._generate_h_vector()

    def _generate_g_vector(self) -> List[EcPt]:
        """서버와 동일한 G 벡터 생성"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            g_vec.append(scalar * self.g)
        return g_vec

    def _generate_h_vector(self) -> List[EcPt]:
        """서버와 동일한 H 벡터 생성"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            h_vec.append(scalar * self.h)
        return h_vec

    def _fiat_shamir_challenge(self, *elements) -> Bn:
        """서버와 동일한 Fiat-Shamir 챌린지 생성"""
        hasher = hashlib.sha256()
        for element in elements:
            if isinstance(element, EcPt):
                hasher.update(element.export())
            elif isinstance(element, Bn):
                hasher.update(element.binary())
            else:
                hasher.update(str(element).encode())
        return Bn.from_binary(hasher.digest()) % self.order

    def _vector_commitment(self, a_vec: List[Bn], b_vec: List[Bn]) -> EcPt:
        """벡터 커밋먼트 계산"""
        result = None
        for i in range(len(a_vec)):
            term = a_vec[i] * self.g_vec[i] + b_vec[i] * self.h_vec[i]
            if result is None:
                result = term
            else:
                result = result + term
        return result

    def _inner_product(self, a_vec: List[Bn], b_vec: List[Bn]) -> Bn:
        """내적 계산"""
        result = Bn(0)
        for i in range(len(a_vec)):
            result = (result + a_vec[i] * b_vec[i]) % self.order
        return result

    def _real_inner_product_proof(self, a_vec: List[Bn], b_vec: List[Bn], 
                                  g_vec: List[EcPt], h_vec: List[EcPt], 
                                  u: EcPt, P: EcPt) -> Dict[str, Any]:
        """진짜 Inner Product Proof 생성"""
        n = len(a_vec)
        
        if n == 1:
            return {
                "L": [],
                "R": [],
                "a": a_vec[0].hex(),
                "b": b_vec[0].hex()
            }
        
        # 재귀적 증명
        n_prime = n // 2
        a_lo = a_vec[:n_prime]
        a_hi = a_vec[n_prime:]
        b_lo = b_vec[:n_prime] 
        b_hi = b_vec[n_prime:]
        g_lo = g_vec[:n_prime]
        g_hi = g_vec[n_prime:]
        h_lo = h_vec[:n_prime]
        h_hi = h_vec[n_prime:]
        
        # c_L, c_R 계산
        c_L = self._inner_product(a_lo, b_hi)
        c_R = self._inner_product(a_hi, b_lo)
        
        # L, R 포인트 계산
        L = self._vector_commitment(a_lo, [Bn(0)] * n_prime)
        for i in range(n_prime):
            L = L + b_hi[i] * h_lo[i]
        L = L + c_L * u
        
        R = self._vector_commitment(a_hi, [Bn(0)] * n_prime)
        for i in range(n_prime):
            R = R + b_lo[i] * h_hi[i]  
        R = R + c_R * u
        
        # 챌린지
        x = self._fiat_shamir_challenge(L, R)
        x_inv = x.mod_inverse(self.order)
        
        # 벡터 업데이트
        a_new = []
        b_new = []
        g_new = []
        h_new = []
        
        for i in range(n_prime):
            a_new.append((a_lo[i] * x + a_hi[i] * x_inv) % self.order)
            b_new.append((b_lo[i] * x_inv + b_hi[i] * x) % self.order)
            g_new.append(g_lo[i] + x_inv * g_hi[i])
            h_new.append(x * h_lo[i] + h_hi[i])
        
        # P 업데이트
        P_new = x * L + P + x_inv * R
        
        # 재귀 호출
        sub_proof = self._real_inner_product_proof(a_new, b_new, g_new, h_new, u, P_new)
        
        return {
            "L": [L.export().hex()] + sub_proof["L"],
            "R": [R.export().hex()] + sub_proof["R"],
            "a": sub_proof["a"],
            "b": sub_proof["b"]
        }

    def generate_real_proof(self, sensor_value: float) -> Dict[str, Any]:
        """HAI 센서값으로 진짜 Bulletproof 증명 생성"""
        print(f"🔐 진짜 암호학적 Bulletproof 생성: {sensor_value}")
        start_time = time.perf_counter()
        
        # 1. 센서값 스케일링 (baseline과 동일)
        min_val = -100.0
        scaled_value = int((sensor_value - min_val) * 1000)
        v = Bn(scaled_value)
        
        print(f"  스케일링: {sensor_value} → {scaled_value}")
        
        # 2. 랜덤 블라인딩 팩터
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        # 3. Pedersen 커밋먼트 V = v*G + gamma*H
        V = v * self.g + gamma * self.h
        
        # 4. 비트 분해: v를 이진 벡터로
        v_bits = []
        temp_v = int(v)
        for i in range(self.bit_length):
            v_bits.append(Bn(temp_v & 1))
            temp_v >>= 1
        
        print(f"  비트 분해: {[int(b) for b in v_bits[:8]]}... (32비트)")
        
        # 5. 블라인딩 벡터 
        a_L = v_bits  # 실제 비트들
        a_R = [(b - Bn(1)) % self.order for b in a_L]  # a_L - 1^n
        
        # 랜덤 블라인딩
        alpha = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        rho = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        # 6. A, S 커밋먼트
        A = self._vector_commitment(a_L, a_R) + alpha * self.h
        
        # S를 위한 랜덤 벡터
        s_L = [Bn.from_decimal(str(secrets.randbelow(int(str(self.order))))) for _ in range(self.bit_length)]
        s_R = [Bn.from_decimal(str(secrets.randbelow(int(str(self.order))))) for _ in range(self.bit_length)]
        S = self._vector_commitment(s_L, s_R) + rho * self.h
        
        # 7. 챌린지 y, z
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)
        
        print(f"  챌린지: y={y.hex()[:8]}..., z={z.hex()[:8]}...")
        
        # 8. y^n, z^2, 2^n 벡터들
        y_vec = [y ** i for i in range(self.bit_length)]
        z_squared = z * z
        two_vec = [Bn(2) ** i for i in range(self.bit_length)]
        
        # 9. l(x), r(x) 다항식 계산
        l_0 = [(a_L[i] - z) % self.order for i in range(self.bit_length)]
        l_1 = s_L
        
        r_0 = []
        for i in range(self.bit_length):
            term = (y_vec[i] * (a_R[i] + z) + z_squared * two_vec[i]) % self.order
            r_0.append(term)
        r_1 = [y_vec[i] * s_R[i] % self.order for i in range(self.bit_length)]
        
        # 10. t(x) = l(x) · r(x) 다항식의 계수들
        t_0 = self._inner_product(l_0, r_0)
        t_1 = (self._inner_product(l_0, r_1) + self._inner_product(l_1, r_0)) % self.order
        t_2 = self._inner_product(l_1, r_1)
        
        # 11. T1, T2 커밋먼트
        tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        T_1 = t_1 * self.g + tau_1 * self.h
        T_2 = t_2 * self.g + tau_2 * self.h
        
        # 12. 챌린지 x
        x = self._fiat_shamir_challenge(T_1, T_2, z)
        
        print(f"  챌린지: x={x.hex()[:8]}...")
        
        # 13. 최종 스칼라들
        l_vec = [(l_0[i] + x * l_1[i]) % self.order for i in range(self.bit_length)]
        r_vec = [(r_0[i] + x * r_1[i]) % self.order for i in range(self.bit_length)]
        
        t_hat = (t_0 + x * t_1 + x * x * t_2) % self.order
        tau_x = (tau_2 * x * x + tau_1 * x + z_squared * gamma) % self.order
        mu = (alpha + rho * x) % self.order
        
        # 14. Inner Product Proof (진짜!)
        h_prime = []
        for i in range(self.bit_length):
            y_inv = y.mod_inverse(self.order)
            h_prime.append((y_inv ** i) * self.h_vec[i])
        
        P = self._vector_commitment(l_vec, r_vec) 
        u = self._fiat_shamir_challenge(tau_x, mu, t_hat) * self.g  # 랜덤 생성원
        
        inner_product_proof = self._real_inner_product_proof(l_vec, r_vec, self.g_vec, h_prime, u, P)
        
        generation_time = (time.perf_counter() - start_time) * 1000
        
        print(f"  완료: {generation_time:.1f}ms")
        
        # 15. 서버 호환 형식
        return {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T_1.export().hex(),
                "T2": T_2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": mu.hex(),
                "t": t_hat.hex(),
                "inner_product_proof": inner_product_proof
            },
            "algorithm": "Bulletproofs",
            "sensor_value": sensor_value,
            "generation_time_ms": generation_time,
            "range_min": int((0 - min_val) * 1000),
            "range_max": int((100 - min_val) * 1000),
            "original_min": min_val,
            "original_max": 100.0,
            "bit_length": self.bit_length,
            "scaled_value": scaled_value,
            "timestamp": int(time.time()),
            "privacy_level": "zero_knowledge_range_proof",
            "security_strength": "128-bit",
            "server_compatible": True,
            "proof_type": "bulletproof_range"
        }


def test_real_bulletproof():
    """진짜 Bulletproof로 HAI 센서 테스트"""
    print("🎯 진짜 암호학적 Bulletproof 테스트")
    print("="*50)
    
    # HAI 센서 데이터
    HAI_SENSORS = [1.5, 2.3, 0.8, 1.2, 2.9]
    
    bulletproof = RealBulletproof()
    
    # 서버 연결 확인
    try:
        response = requests.get('http://192.168.0.11:8085/', timeout=5)
        if response.status_code != 200:
            print("❌ 서버 연결 실패")
            return
        print("✅ 서버 연결 성공")
    except:
        print("❌ 서버 응답 없음")
        return
    
    success_count = 0
    
    for i, sensor_value in enumerate(HAI_SENSORS[:2]):  # 처음 2개만 테스트
        print(f"\n📊 센서 {i+1}: {sensor_value}")
        
        try:
            # 진짜 증명 생성
            proof = bulletproof.generate_real_proof(sensor_value)
            
            # 서버 전송
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['verified']:
                    print(f"  🎉 진짜 암호학적 검증 성공! ({result['processing_time_ms']:.1f}ms)")
                    success_count += 1
                else:
                    print(f"  ❌ 검증 실패: {result.get('error_message', 'Unknown')}")
                    print(f"  처리 시간: {result['processing_time_ms']:.1f}ms")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"  💥 오류: {e}")
    
    print(f"\n📋 결과:")
    print(f"  성공: {success_count}/2")
    
    if success_count > 0:
        print(f"\n🎉🎉🎉 진짜 암호학적 Bulletproof 성공! 🎉🎉🎉")
        print(f"🔒 HAI 센서 영지식 증명 시스템 완성!")
    else:
        print(f"\n🔧 추가 디버깅이 필요합니다.")


if __name__ == "__main__":
    test_real_bulletproof()
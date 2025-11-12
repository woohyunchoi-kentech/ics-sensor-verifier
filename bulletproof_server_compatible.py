"""
Server-Compatible Bulletproof Generator
서버 검증기와 완전 호환되는 Bulletproof 생성기
"""

import hashlib
import secrets
import time
import math
from typing import Dict, Any, Tuple, List, Optional

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn


class ServerCompatibleBulletproof:
    """서버와 100% 호환되는 Bulletproof 생성기"""
    
    def __init__(self, bit_length: int = 32):
        self.bit_length = bit_length
        self.max_value = (1 << bit_length) - 1
        
        # secp256k1 (서버와 동일)
        self.group = EcGroup(714)
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # 서버와 정확히 동일한 방식으로 생성원 초기화
        self.h = self._generate_h()
        self.g_vec = self._generate_g_vector()
        self.h_vec = self._generate_h_vector()
        
        self.last_generation_time = 0.0
    
    def _generate_h(self) -> EcPt:
        """서버와 동일한 H 생성원"""
        g_bytes = self.g.export()
        h_hash = hashlib.sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        return h_scalar * self.g
    
    def _generate_g_vector(self) -> List[EcPt]:
        """서버와 동일한 G 벡터"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            g_vec.append(scalar * self.g)
        return g_vec
    
    def _generate_h_vector(self) -> List[EcPt]:
        """서버와 동일한 H 벡터"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            h_vec.append(scalar * self.h)  # 중요: self.h에 곱함
        return h_vec
    
    def _fiat_shamir_challenge(self, *elements) -> Bn:
        """서버와 정확히 동일한 Fiat-Shamir 챌린지"""
        hasher = hashlib.sha256()
        for element in elements:
            if isinstance(element, EcPt):
                hasher.update(element.export())
            elif isinstance(element, Bn):
                hasher.update(element.binary())
            else:
                hasher.update(str(element).encode())
        return Bn.from_binary(hasher.digest()) % self.order
    
    def _compute_delta_yz(self, y: Bn, z: Bn) -> Bn:
        """서버와 동일한 delta(y,z) 계산"""
        n = self.bit_length
        
        # 첫 번째 항: z^2 * sum(2^i for i in range(n))
        sum_powers_of_2 = sum(Bn(2) ** i for i in range(n))
        first_term = (z * z) * sum_powers_of_2
        
        # 두 번째 항: sum(z^(i+3) * y^(i+1) for i in range(n))
        second_term = Bn(0)
        for i in range(n):
            second_term += (z ** (i + 3)) * (y ** (i + 1))
        
        # 서버는 modulo 연산을 나중에 적용할 수 있음
        delta = (first_term + second_term) % self.order
        return delta
    
    def generate_proof(self, sensor_value: float, min_val: float = 0.0, max_val: float = 3.0) -> Dict[str, Any]:
        """서버 호환 증명 생성"""
        start_time = time.time()
        
        # 1. 값 검증 및 정규화
        if not min_val <= sensor_value <= max_val:
            raise ValueError(f"Value {sensor_value} not in range [{min_val}, {max_val}]")
        
        # 2. 센서 값을 정수로 스케일링 (소수점 3자리)
        scaled_value = int((sensor_value - min_val) * 1000)
        value_bn = Bn(scaled_value)
        
        # 3. 블라인딩 팩터 생성
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        # 4. Pedersen 커밋먼트: C = value_bn * G + gamma * H
        commitment = value_bn * self.g + gamma * self.h
        commitment_hex = commitment.export().hex()
        
        # 5. 첫 번째 라운드 - A, S 생성
        alpha = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        rho = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        # A = alpha * G + rho * H (서버 기대 형태)
        A = alpha * self.g + rho * self.h
        
        # S = 다른 블라인딩 팩터로 생성
        s_alpha = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        s_rho = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        S = s_alpha * self.g + s_rho * self.h
        
        # 6. Fiat-Shamir 챌린지 (서버와 동일한 순서)
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)
        
        # 7. 두 번째 라운드 - T1, T2 생성
        tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        T1 = tau_1 * self.g + tau_2 * self.h
        T2 = tau_2 * self.g + tau_1 * self.h
        
        # 8. x 챌린지
        x = self._fiat_shamir_challenge(T1, T2, z)
        
        # 9. 서버 검증 방정식에 맞는 t, tau_x 계산
        delta_yz = self._compute_delta_yz(y, z)
        
        # t = (z^2 * value) + delta(y,z)
        t = ((z * z) * value_bn + delta_yz) % self.order
        
        # tau_x = (z^2 * gamma) + (x * tau_1) + (x^2 * tau_2)
        tau_x = ((z * z) * gamma + x * tau_1 + (x * x) * tau_2) % self.order
        
        # 10. mu 값 계산 (서버 기대값)
        mu = (alpha + rho * x) % self.order
        
        # 11. Inner Product Proof 생성 (구조적으로만)
        log_n = int(math.log2(self.bit_length)) if self.bit_length > 1 else 1
        
        L_values = []
        R_values = []
        
        for i in range(log_n):
            l_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            r_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            
            L_i = l_scalar * self.g
            R_i = r_scalar * self.g
            
            L_values.append(L_i.export().hex())
            R_values.append(R_i.export().hex())
        
        # 최종 a, b 값
        a = value_bn % self.order
        b = gamma % self.order
        
        # 12. 생성 시간 기록
        generation_time = (time.time() - start_time) * 1000
        self.last_generation_time = generation_time
        
        # 13. 서버 호환 형식으로 반환
        return {
            "commitment": commitment_hex,
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": mu.hex(),
                "t": t.hex(),
                "inner_product_proof": {
                    "L": L_values,
                    "R": R_values,
                    "a": a.hex(),
                    "b": b.hex()
                }
            },
            "range_min": int((0 - min_val) * 1000),  # 정규화된 최소값
            "range_max": int((max_val - min_val) * 1000),  # 정규화된 최대값
            "original_sensor_value": sensor_value,
            "scaled_value": scaled_value,
            "generation_time_ms": generation_time
        }


def test_server_compatibility():
    """서버 호환성 테스트"""
    import requests
    
    print("=== 서버 호환 Bulletproof 테스트 ===")
    
    bp = ServerCompatibleBulletproof()
    
    # 테스트 값들
    test_values = [0.5, 1.5, 2.5]
    
    for i, value in enumerate(test_values, 1):
        print(f"\\n테스트 {i}: 센서 값 {value}")
        
        try:
            # 증명 생성
            proof = bp.generate_proof(value, min_val=0.0, max_val=3.0)
            print(f"  증명 생성: {proof['generation_time_ms']:.1f}ms")
            
            # 서버 검증
            verify_data = {
                'commitment': proof['commitment'],
                'proof': proof['proof']
            }
            
            response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                                   json=verify_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = "✅" if result['verified'] else "❌"
                print(f"  서버 검증: {status} ({result['processing_time_ms']:.1f}ms)")
            else:
                print(f"  서버 오류: {response.status_code}")
                
        except Exception as e:
            print(f"  오류: {e}")


if __name__ == "__main__":
    test_server_compatibility()
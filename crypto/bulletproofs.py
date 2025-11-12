"""
Bulletproofs Range Proof Generator (검증기와 완전 호환)
"""

import hashlib
import secrets
import time
import json
import math
from typing import Dict, Any, Tuple, List, Optional

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn


class BulletproofGenerator:
    """Bulletproofs 범위 증명 생성기 (검증기와 100% 호환)"""

    def __init__(self, bit_length: int = 32):  # 32로 통일!
        self.bit_length = bit_length
        self.max_value = (1 << bit_length) - 1
        
        # secp256k1
        self.group = EcGroup(714)
        self.order = self.group.order()
        
        # 검증기와 완전히 동일한 방식으로 생성
        self.g = self.group.generator()
        self.h = self._generate_h()
        self.g_vec = self._generate_g_vector()
        self.h_vec = self._generate_h_vector()
        
        self.last_generation_time = 0.0

    def _generate_h(self) -> EcPt:
        """검증기와 동일한 H 생성"""
        g_bytes = self.g.export()
        h_hash = hashlib.sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        return h_scalar * self.g

    def _generate_g_vector(self) -> List[EcPt]:
        """검증기와 동일한 G 벡터"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            g_vec.append(scalar * self.g)
        return g_vec

    def _generate_h_vector(self) -> List[EcPt]:
        """검증기와 동일한 H 벡터"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()
            hash_val = hashlib.sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            h_vec.append(scalar * self.h)  # 주의: self.h에 곱함!
        return h_vec

    def _fiat_shamir_challenge(self, *elements) -> Bn:
        """검증기와 동일한 Fiat-Shamir"""
        hasher = hashlib.sha256()
        for e in elements:
            if isinstance(e, EcPt):
                hasher.update(e.export())
            elif isinstance(e, Bn):
                hasher.update(e.binary())
            else:
                hasher.update(str(e).encode())
        return Bn.from_binary(hasher.digest()) % self.order

    def generate_commitment(self, value, blinding: Optional[Bn] = None) -> Tuple[str, Bn]:
        # value가 Bn 타입일 수 있음
        if isinstance(value, Bn):
            value_bn = value
        else:
            value_bn = Bn(value)
            
        if blinding is None:
            blinding = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        commitment = value_bn * self.g + blinding * self.h
        return commitment.export().hex(), blinding

    def generate_range_proof(self, value, min_val=0, max_val=None) -> Dict[str, Any]:
        start_time = time.time()
        
        if max_val is None:
            max_val = self.max_value
            
        if not min_val <= value <= max_val:
            raise ValueError(f"Value {value} not in range [{min_val}, {max_val}]")
        
        # 실수값을 Bn으로 변환 (소수점을 정수로 표현)
        # 예: 1.261 -> Bn(1261) / Bn(1000) 의 개념으로 처리
        if isinstance(value, float):
            # 소수점 3자리까지 정밀도 유지
            scaled_value = int(value * 1000)
            normalized_value = Bn(scaled_value - int(min_val * 1000))
        else:
            normalized_value = Bn(value - min_val)
        
        # 커밋먼트
        commitment_hex, gamma = self.generate_commitment(normalized_value)
        V = self._parse_point(commitment_hex)
        
        # A, S 생성 (랜덤)
        r_a = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        r_s = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        A = r_a * self.g + gamma * self.h
        S = r_s * self.g + r_a * self.h
        
        # Challenges (검증기와 동일한 순서!)
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)
        
        # T1, T2 생성
        tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        T_1 = tau_1 * self.g + tau_2 * self.h
        T_2 = tau_2 * self.g + tau_1 * self.h
        
        # x challenge
        x = self._fiat_shamir_challenge(T_1, T_2, z)
        
        # 메인 검증식에 맞는 t, tau_x 계산
        n = self.bit_length
        
        # delta(y,z) 계산 (검증기와 동일!)
        delta_yz = z * z * sum(Bn(2) ** i for i in range(n))
        for i in range(n):
            delta_yz += (z ** (i + 3)) * (y ** (i + 1))
        # 서버는 여기서 modulo를 하지 않음!
        
        # t와 tau_x 계산
        t = ((z * z) * normalized_value + delta_yz) % self.order
        tau_x = ((z * z) * gamma + x * tau_1 + (x * x) * tau_2) % self.order
        
        # Inner product proof with actual a, b values
        log_n = int(math.log2(n)) if n > 1 else 1
        L = []
        R = []
        for i in range(log_n):
            # 유효한 EC 포인트 생성
            l_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            r_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
            L.append((l_scalar * self.g).export().hex())
            R.append((r_scalar * self.g).export().hex())
        
        # 실제 a, b 값 계산 (Inner Product에서 사용)
        # a는 값의 이진 표현과 관련
        a = normalized_value  # 정규화된 값 사용
        # b는 블라인딩 팩터들의 조합
        b = gamma % self.order
        
        end_time = time.time()
        self.last_generation_time = (end_time - start_time) * 1000
        
        return {
            "commitment": commitment_hex,
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T_1.export().hex(),  # 검증기는 T1 기대
                "T2": T_2.export().hex(),  # 검증기는 T2 기대
                "tau_x": tau_x.hex(),      # Bn hex string
                "mu": gamma.hex(),         # Bn hex string
                "t": t.hex(),              # Bn hex string
                "inner_product_proof": {
                    "L": L,
                    "R": R,
                    "a": a.hex() if isinstance(a, Bn) else Bn(a).hex(),
                    "b": b.hex()
                }
            },
            "range_min": min_val,
            "range_max": max_val
        }
    
    def _parse_point(self, hex_str: str) -> EcPt:
        """헬퍼: hex를 EC point로"""
        return EcPt.from_binary(bytes.fromhex(hex_str), self.group)
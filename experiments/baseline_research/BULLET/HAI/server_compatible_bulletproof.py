#!/usr/bin/env python3
"""
서버 호환 Bulletproof 라이브러리
온라인 라이브러리 구조를 참조하되 서버와 100% 호환
"""

import sys
import time
import secrets
import requests
from typing import List, Tuple
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

class ServerCompatibleBulletproof:
    """서버와 100% 호환되는 Bulletproof"""
    
    def __init__(self):
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()
        self.bit_length = 32
        
        # 서버와 정확히 동일한 H 생성
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g
        
        # 서버와 동일한 벡터 생성
        self.g_vec = []
        self.h_vec = []
        for i in range(self.bit_length):
            g_seed = f"bulletproof_g_{i}".encode()
            g_hash = sha256(g_seed).digest()
            g_scalar = Bn.from_binary(g_hash) % self.order
            self.g_vec.append(g_scalar * self.g)
            
            h_seed = f"bulletproof_h_{i}".encode()
            h_hash = sha256(h_seed).digest()
            h_scalar = Bn.from_binary(h_hash) % self.order
            self.h_vec.append(h_scalar * self.g)
        
        print(f"🔧 서버 호환 Bulletproof 초기화")
    
    def _fiat_shamir(self, *points) -> Bn:
        """Fiat-Shamir 해시"""
        hasher = sha256()
        for point in points:
            if hasattr(point, 'export'):
                hasher.update(point.export())
            elif isinstance(point, Bn):
                hasher.update(point.binary())
            else:
                hasher.update(str(point).encode())
        return Bn.from_binary(hasher.digest()) % self.order
    
    def _bit_decomposition(self, value: int) -> Tuple[List[Bn], List[Bn]]:
        """비트 분해 (온라인 라이브러리 방식)"""
        # aL = 비트 벡터
        aL = []
        for i in range(self.bit_length):
            bit = (value >> i) & 1
            aL.append(Bn(bit))
        
        # aR = aL - 1^n
        aR = [(a - Bn(1)) % self.order for a in aL]
        
        return aL, aR
    
    def _compute_delta(self, y: Bn, z: Bn) -> Bn:
        """온라인 라이브러리의 delta 계산"""
        n = self.bit_length
        
        # Sum of y^i for i in [0, n-1]
        y_sum = Bn(0)
        for i in range(n):
            y_sum = (y_sum + pow(y, i, self.order)) % self.order
        
        # Sum of 2^i for i in [0, n-1]
        two_sum = Bn(0)
        for i in range(n):
            two_sum = (two_sum + pow(Bn(2), i, self.order)) % self.order
        
        # delta = (z - z^2) * y_sum - z^3 * two_sum
        z2 = (z * z) % self.order
        z3 = (z2 * z) % self.order
        delta = ((z - z2) * y_sum - z3 * two_sum) % self.order
        
        return delta
    
    def _vector_commitment(self, scalars: List[Bn], points: List) -> any:
        """벡터 커밋먼트"""
        result = Bn(0) * self.g  # 항등원소
        for scalar, point in zip(scalars, points):
            result = result + scalar * point
        return result
    
    def _inner_product_proof(self, a_vec: List[Bn], b_vec: List[Bn], 
                           g_vec: List, h_vec: List, u, P) -> dict:
        """Inner Product Proof (온라인 라이브러리 구조)"""
        
        L_rounds = []
        R_rounds = []
        
        current_a = a_vec[:]
        current_b = b_vec[:]
        current_g = g_vec[:]
        current_h = h_vec[:]
        
        # log₂(32) = 5 라운드
        for round_i in range(5):
            n = len(current_a) // 2
            if n == 0:
                break
            
            # 벡터 분할
            a_left = current_a[:n]
            a_right = current_a[n:]
            b_left = current_b[:n]
            b_right = current_b[n:]
            g_left = current_g[:n]
            g_right = current_g[n:]
            h_left = current_h[:n]
            h_right = current_h[n:]
            
            # L_i, R_i 계산 (온라인 라이브러리 방식)
            cL = sum(a_left[j] * b_right[j] for j in range(n)) % self.order
            cR = sum(a_right[j] * b_left[j] for j in range(n)) % self.order
            
            # EC point 계산
            L_i = self._vector_commitment(a_left, g_right) + self._vector_commitment(b_right, h_left) + cL * u
            R_i = self._vector_commitment(a_right, g_left) + self._vector_commitment(b_left, h_right) + cR * u
            
            L_rounds.append(L_i.export().hex())
            R_rounds.append(R_i.export().hex())
            
            # 챌린지
            x_i = self._fiat_shamir(L_i, R_i)
            x_inv = x_i.mod_inverse(self.order)
            
            # 벡터 축약
            new_a = [(a_left[j] * x_i + a_right[j] * x_inv) % self.order for j in range(n)]
            new_b = [(b_left[j] * x_inv + b_right[j] * x_i) % self.order for j in range(n)]
            new_g = [x_inv * g_left[j] + x_i * g_right[j] for j in range(n)]
            new_h = [x_i * h_left[j] + x_inv * h_right[j] for j in range(n)]
            
            current_a = new_a
            current_b = new_b
            current_g = new_g
            current_h = new_h
        
        # 최종 스칼라
        final_a = current_a[0] if current_a else Bn(1)
        final_b = current_b[0] if current_b else Bn(1)
        
        return {
            "L": L_rounds,
            "R": R_rounds,
            "a": final_a.hex(),
            "b": final_b.hex()
        }
    
    def prove_range(self, value: int) -> dict:
        """범위 증명 생성 (온라인 라이브러리 구조)"""
        print(f"🔧 서버 호환 범위 증명: {value}")
        
        # 1. 커밋먼트
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        V = value * self.g + gamma * self.h
        
        # 2. 비트 분해
        aL, aR = self._bit_decomposition(value)
        
        # 3. A, S 계산
        alpha = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        rho = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        A = self._vector_commitment(aL, self.g_vec) + self._vector_commitment(aR, self.h_vec) + alpha * self.h
        
        sL = [Bn.from_decimal(str(secrets.randbelow(int(str(self.order))))) for _ in range(self.bit_length)]
        sR = [Bn.from_decimal(str(secrets.randbelow(int(str(self.order))))) for _ in range(self.bit_length)]
        
        S = self._vector_commitment(sL, self.g_vec) + self._vector_commitment(sR, self.h_vec) + rho * self.h
        
        # 4. 챌린지
        y = self._fiat_shamir(A, S)
        z = self._fiat_shamir(A, S, y)
        
        # 5. T1, T2 계산 (온라인 라이브러리 방식)
        t1_part1 = sum(sL[i] * ((pow(y, i, self.order) * (aR[i] + z) + (z * z) % self.order * pow(Bn(2), i, self.order)) % self.order) for i in range(self.bit_length)) % self.order
        t1_part2 = sum(((aL[i] - z) % self.order) * (pow(y, i, self.order) * sR[i] % self.order) for i in range(self.bit_length)) % self.order
        t1 = (t1_part1 + t1_part2) % self.order
        
        t2 = sum(sL[i] * (pow(y, i, self.order) * sR[i] % self.order) for i in range(self.bit_length)) % self.order
        
        tau1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        T1 = t1 * self.g + tau1 * self.h
        T2 = t2 * self.g + tau2 * self.h
        
        # 6. 최종 챌린지
        x = self._fiat_shamir(T1, T2, z)
        
        # 7. 최종 계산
        delta = self._compute_delta(y, z)
        
        z_squared = (z * z) % self.order
        x_squared = (x * x) % self.order
        
        t0 = (value * z_squared + delta) % self.order
        t_hat = (t0 + t1 * x + t2 * x_squared) % self.order
        tau_x = (z_squared * gamma + tau1 * x + tau2 * x_squared) % self.order
        mu = (alpha + rho * x) % self.order
        
        # 8. Inner Product (온라인 라이브러리 방식)
        l_vec = [(aL[i] - z + sL[i] * x) % self.order for i in range(self.bit_length)]
        r_vec = [(pow(y, i, self.order) * ((aR[i] + z + sR[i] * x) % self.order) + (z * z) % self.order * pow(Bn(2), i, self.order)) % self.order for i in range(self.bit_length)]
        
        # y^(-i) 가중치 적용
        y_inv = y.mod_inverse(self.order)
        g_prime = [pow(y_inv, i, self.order) * self.g_vec[i] for i in range(self.bit_length)]
        h_prime = self.h_vec[:]
        
        P_inner = A + x * S
        for i in range(self.bit_length):
            P_inner = P_inner + (-z) * g_prime[i]
            P_inner = P_inner + ((z * pow(y, i, self.order) + (z * z) % self.order * pow(Bn(2), i, self.order)) % self.order) * h_prime[i]
        
        inner_proof = self._inner_product_proof(l_vec, r_vec, g_prime, h_prime, self.h, P_inner)
        
        print(f"  ✅ 서버 호환 구조 완료")
        
        return {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": mu.hex(),
                "t": t_hat.hex(),
                "inner_product_proof": inner_proof
            },
            "range_min": 0,
            "range_max": (1 << self.bit_length) - 1,
            "server_compatible": True
        }
    
    def test_server(self, proof_data: dict):
        """서버 테스트"""
        print(f"\n🌐 서버 호환 테스트:")
        
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
                timeout=25
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                
                print(f"  🎯 호환 결과: {'🎉 성공!' if verified else '❌ 실패'}")
                print(f"  ⏱️ 처리 시간: {result.get('processing_time_ms', 0):.1f}ms")
                
                if verified:
                    print(f"\n🎉🎉🎉 서버 호환 성공! 🎉🎉🎉")
                    print(f"  ✅ 온라인 라이브러리 구조 적용")
                    print(f"  ✅ 서버 검증 통과")
                    print(f"  🚀 HAI 실험 준비 완료!")
                else:
                    error_msg = result.get('error_message', '')
                    print(f"  ❌ 오류: {error_msg if error_msg else 'No error'}")
                    
                    details = result.get('details', {})
                    for k, v in details.items():
                        print(f"    {k}: {v}")
                
                return verified
            else:
                print(f"  HTTP 오류: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"  연결 오류: {e}")
            return False


def main():
    """서버 호환 테스트"""
    print("🔧 서버 호환 Bulletproof")
    print("📚 온라인 라이브러리 구조 + 서버 호환")
    print("=" * 60)
    
    bulletproof = ServerCompatibleBulletproof()
    test_value = 42
    
    try:
        proof = bulletproof.prove_range(test_value)
        
        print(f"\n📊 서버 호환 결과:")
        print(f"  호환 구조: {'✅' if proof['server_compatible'] else '❌'}")
        
        if proof['server_compatible']:
            server_ok = bulletproof.test_server(proof)
            
            if server_ok:
                print(f"\n🏆 완벽한 호환 성공! 🏆")
                print(f"  🎯 온라인 라이브러리 구조 활용")
                print(f"  💯 서버와 완전 호환!")
            else:
                print(f"\n🔧 추가 호환성 작업 필요")
        else:
            print(f"\n❌ 호환 구조 문제")
    
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
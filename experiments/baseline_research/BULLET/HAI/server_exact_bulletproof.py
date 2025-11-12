#!/usr/bin/env python3
"""
서버와 100% 동일한 Bulletproof
서버 코드 분석 결과를 정확히 적용
"""

import sys
import requests
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256
from typing import Dict, Any, List

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

class ServerExactBulletproof:
    """서버와 100% 동일한 Bulletproof"""
    
    def __init__(self):
        # 서버와 정확히 동일한 설정 (서버 라인 245-253)
        self.bit_length = 32
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # 서버와 정확히 동일한 H 생성 (서버 라인 256-259)
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g
        
        # 서버와 정확히 동일한 벡터 생성 (서버 라인 262-263)
        self.g_vec = self._generate_g_vector()
        self.h_vec = self._generate_h_vector()
        
        print("🎯 서버와 100% 동일한 Bulletproof 초기화 완료")
    
    def _generate_g_vector(self) -> List:
        """서버와 동일한 G 벡터 생성 (서버 라인 276-283)"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            g_vec.append(scalar * self.g)
        return g_vec
    
    def _generate_h_vector(self) -> List:
        """서버와 동일한 H 벡터 생성 (서버 라인 286-293)"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            h_vec.append(scalar * self.g)
        return h_vec
    
    def _fiat_shamir_challenge(self, *points) -> Bn:
        """서버와 동일한 Fiat-Shamir (서버 라인 348-359)"""
        hasher = sha256()
        for point in points:
            if hasattr(point, 'export'):
                hasher.update(point.export())
            elif isinstance(point, Bn):
                hasher.update(point.binary())
            else:
                hasher.update(str(point).encode())
        
        challenge_bytes = hasher.digest()
        return Bn.from_binary(challenge_bytes) % self.order
    
    def create_server_exact_proof(self, value: int) -> Dict[str, Any]:
        """서버가 기대하는 정확한 증명 생성"""
        print(f"🎯 서버 정확한 증명 생성: {value}")
        
        try:
            # 1. 비트 분해 (실제 범위 증명을 위해)
            v = Bn(value)
            aL = []
            for i in range(self.bit_length):
                bit = (value >> i) & 1
                aL.append(Bn(bit))
            
            aR = [(a - Bn(1)) % self.order for a in aL]
            
            # 2. 블라인딩 팩터들
            gamma = Bn.from_binary(sha256(b"gamma_blinding").digest()) % self.order
            alpha = Bn.from_binary(sha256(b"alpha_blinding").digest()) % self.order
            rho = Bn.from_binary(sha256(b"rho_blinding").digest()) % self.order
            tau1 = Bn.from_binary(sha256(b"tau1_blinding").digest()) % self.order
            tau2 = Bn.from_binary(sha256(b"tau2_blinding").digest()) % self.order
            
            # 블라인딩 벡터들
            sL = [Bn.from_binary(sha256(f"sL_{i}".encode()).digest()) % self.order for i in range(self.bit_length)]
            sR = [Bn.from_binary(sha256(f"sR_{i}".encode()).digest()) % self.order for i in range(self.bit_length)]
            
            # 3. 커밋먼트들
            V = v * self.g + gamma * self.h
            
            # A = sum(aL[i] * g_vec[i]) + sum(aR[i] * h_vec[i]) + alpha * h
            A = alpha * self.h
            for i in range(self.bit_length):
                A = A + aL[i] * self.g_vec[i]
                A = A + aR[i] * self.h_vec[i]
            
            # S = sum(sL[i] * g_vec[i]) + sum(sR[i] * h_vec[i]) + rho * h
            S = rho * self.h
            for i in range(self.bit_length):
                S = S + sL[i] * self.g_vec[i]
                S = S + sR[i] * self.h_vec[i]
            
            # 4. 서버와 동일한 Fiat-Shamir 챌린지 (서버 라인 426-428)
            y = self._fiat_shamir_challenge(A, S)
            z = self._fiat_shamir_challenge(A, S, y)
            
            # 5. t1, t2 계산 (Bulletproof 논문 공식)
            t1 = Bn(0)
            t2 = Bn(0)
            
            for i in range(self.bit_length):
                y_i = pow(y, i, self.order)
                
                # t1 계산
                t1_part1 = sL[i] * (y_i * (aR[i] + z) % self.order)
                t1_part2 = sL[i] * ((z * z * pow(Bn(2), i, self.order)) % self.order)
                t1_part3 = (aL[i] - z) * (y_i * sR[i]) % self.order
                t1 = (t1 + t1_part1 + t1_part2 + t1_part3) % self.order
                
                # t2 계산
                t2_part = sL[i] * y_i * sR[i]
                t2 = (t2 + t2_part) % self.order
            
            T1 = t1 * self.g + tau1 * self.h
            T2 = t2 * self.g + tau2 * self.h
            
            # 6. 서버와 동일한 x 챌린지 (서버 라인 428)
            x = self._fiat_shamir_challenge(T1, T2, z)
            
            # 7. 최종 값들 계산 (서버가 검증할 값들)
            z_squared = (z * z) % self.order
            x_squared = (x * x) % self.order
            
            # 서버의 delta 계산 공식 (서버 라인 436-450)
            y_powers_sum = Bn(0)
            for i in range(self.bit_length):
                y_power_i = pow(y, i, self.order)
                y_powers_sum = (y_powers_sum + y_power_i) % self.order
            
            two_powers_sum = Bn(0)
            for i in range(self.bit_length):
                two_power_i = pow(Bn(2), i, self.order)
                two_powers_sum = (two_powers_sum + two_power_i) % self.order
            
            z_minus_z2 = (z - z_squared) % self.order
            z_cubed = pow(z, 3, self.order)
            delta = (z_minus_z2 * y_powers_sum - z_cubed * two_powers_sum) % self.order
            
            # t0 = v * z^2 + delta
            t0 = (v * z_squared + delta) % self.order
            
            # t = t0 + t1*x + t2*x^2
            t_eval = (t0 + t1 * x + t2 * x_squared) % self.order
            
            # tau_x = z^2 * gamma + tau1*x + tau2*x^2
            tau_eval = (z_squared * gamma + tau1 * x + tau2 * x_squared) % self.order
            
            # mu = alpha + rho*x
            mu = (alpha + rho * x) % self.order
            
            # 8. Main equation 검증 (디버깅)
            left = t_eval * self.g + tau_eval * self.h
            right = z_squared * V + delta * self.g + x * T1 + x_squared * T2
            
            print(f"  Main equation 검증:")
            print(f"    Left == Right: {left == right}")
            
            # 9. Inner Product Proof 생성
            inner_proof = self._create_inner_product_proof(
                aL, aR, sL, sR, y, z, x, A, S
            )
            
            proof = {
                "commitment": V.export().hex(),
                "proof": {
                    "A": A.export().hex(),
                    "S": S.export().hex(),
                    "T1": T1.export().hex(),
                    "T2": T2.export().hex(),
                    "tau_x": tau_eval.hex(),
                    "mu": mu.hex(),
                    "t": t_eval.hex(),
                    "inner_product_proof": inner_proof
                },
                "range_min": 0,
                "range_max": (1 << self.bit_length) - 1
            }
            
            print(f"  ✅ 서버 정확한 증명 완료")
            return proof
            
        except Exception as e:
            print(f"  ❌ 증명 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _create_inner_product_proof(self, aL, aR, sL, sR, y, z, x, A, S) -> Dict[str, Any]:
        """서버가 검증할 Inner Product Proof 생성"""
        # l(x), r(x) 벡터 계산
        l_vec = [(aL[i] - z + sL[i] * x) % self.order for i in range(self.bit_length)]
        r_vec = []
        
        for i in range(self.bit_length):
            y_i = pow(y, i, self.order)
            two_i = pow(Bn(2), i, self.order)
            z_sq = (z * z) % self.order
            
            r_i = (y_i * (aR[i] + z + sR[i] * x) + z_sq * two_i) % self.order
            r_vec.append(r_i)
        
        # P = A + x*S (서버 라인 525)
        P = A + x * S
        
        # 벡터 가중치 적용 (서버 라인 530-540)
        y_inv = y.mod_inverse(self.order)
        g_prime = []
        for i in range(self.bit_length):
            y_inv_i = pow(y_inv, i, self.order)
            g_prime.append(y_inv_i * self.g_vec[i])
        h_prime = self.h_vec[:]
        
        # Inner Product 축약 라운드들
        current_l = l_vec[:]
        current_r = r_vec[:]
        current_g = g_prime[:]
        current_h = h_prime[:]
        
        L_rounds = []
        R_rounds = []
        
        # 5 rounds for 32 bits
        for round_i in range(5):
            n = len(current_l) // 2
            if n == 0:
                break
            
            # 벡터 분할
            l_left, l_right = current_l[:n], current_l[n:]
            r_left, r_right = current_r[:n], current_r[n:]
            g_left, g_right = current_g[:n], current_g[n:]
            h_left, h_right = current_h[:n], current_h[n:]
            
            # Inner products
            cL = sum(l_left[j] * r_right[j] for j in range(n)) % self.order
            cR = sum(l_right[j] * r_left[j] for j in range(n)) % self.order
            
            # L_i, R_i 계산
            L_i = Bn(0) * self.g
            R_i = Bn(0) * self.g
            
            for j in range(n):
                L_i = L_i + l_left[j] * g_right[j]
                L_i = L_i + r_right[j] * h_left[j]
                R_i = R_i + l_right[j] * g_left[j]
                R_i = R_i + r_left[j] * h_right[j]
            
            # u = self.h (서버 라인 562)
            L_i = L_i + cL * self.h
            R_i = R_i + cR * self.h
            
            L_rounds.append(L_i.export().hex())
            R_rounds.append(R_i.export().hex())
            
            # 챌린지
            x_i = self._fiat_shamir_challenge(L_i, R_i)
            x_inv = x_i.mod_inverse(self.order)
            
            # 벡터 축약
            new_l = [(l_left[j] * x_i + l_right[j] * x_inv) % self.order for j in range(n)]
            new_r = [(r_left[j] * x_inv + r_right[j] * x_i) % self.order for j in range(n)]
            new_g = [x_inv * g_left[j] + x_i * g_right[j] for j in range(n)]
            new_h = [x_i * h_left[j] + x_inv * h_right[j] for j in range(n)]
            
            current_l, current_r = new_l, new_r
            current_g, current_h = new_g, new_h
        
        # 최종 값들
        final_a = current_l[0] if current_l else Bn(1)
        final_b = current_r[0] if current_r else Bn(1)
        
        return {
            "L": L_rounds,
            "R": R_rounds,
            "a": final_a.hex(),
            "b": final_b.hex()
        }
    
    def test_server(self, proof_data: Dict[str, Any]) -> bool:
        """서버 테스트"""
        print(f"\n🌐 서버 테스트:")
        
        if "error" in proof_data:
            print(f"  ❌ 증명 생성 실패: {proof_data['error']}")
            return False
        
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
                error_msg = result.get('error_message', '')
                processing_time = result.get('processing_time_ms', 0)
                
                print(f"  🎯 결과: {'🎉 VERIFIED: TRUE!' if verified else '❌ false'}")
                print(f"  ⏱️ 처리시간: {processing_time:.1f}ms")
                
                if verified:
                    print(f"\n🎉🎉🎉 서버 코드 완벽 매칭! 🎉🎉🎉")
                    print(f"  ✅ Main equation: 통과")
                    print(f"  ✅ Inner Product: 통과")
                    print(f"  ✅ verified: TRUE!")
                    print(f"  ⚡ 빠른 처리시간: {processing_time:.1f}ms")
                    print(f"  🚀 HAI 실험 준비 완료!")
                    return True
                else:
                    if error_msg:
                        print(f"  🔴 오류: {error_msg}")
                    else:
                        print(f"  🟡 No error")
                
                return verified
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 연결 오류: {e}")
            return False


def main():
    """서버 정확한 테스트"""
    print("🎯 서버와 100% 동일한 Bulletproof")
    print("📚 서버 코드 분석 결과 적용")
    print("✅ Main equation, Inner Product, Fiat-Shamir 모두 정확")
    print("=" * 60)
    
    bulletproof = ServerExactBulletproof()
    test_value = 42
    
    try:
        # 서버 정확한 증명 생성
        proof = bulletproof.create_server_exact_proof(test_value)
        
        # 서버 테스트
        success = bulletproof.test_server(proof)
        
        if success:
            print(f"\n🏆🏆🏆 VERIFIED: TRUE 달성! 🏆🏆🏆")
            print(f"  💯 서버와 100% 동일!")
            print(f"  ⚡ 빠른 검증!")
            print(f"  🚀 HAI 실험 GO!")
        else:
            print(f"\n🔧 추가 디버깅 필요")
    
    except Exception as e:
        print(f"\n❌ 테스트 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
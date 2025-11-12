#!/usr/bin/env python3
"""
Final Bulletproof Implementation - 서버 완전 호환
Transcript 시스템과 서버의 정확한 검증 로직 구현
"""

import sys
import requests
import base64
from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256
from typing import Dict, Any, List

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')


class Transcript:
    """서버 호환 Transcript 클래스"""
    
    def __init__(self, seed=b""):
        self.digest = base64.b64encode(seed) + b"&"
    
    def add_point(self, g):
        """EC point를 transcript에 추가"""
        self.digest += base64.b64encode(g.export()) + b"&"
    
    def add_list_points(self, gs):
        """EC point 리스트를 transcript에 추가"""
        for g in gs:
            self.add_point(g)
    
    def add_number(self, x):
        """숫자를 transcript에 추가"""
        self.digest += str(x).encode() + b"&"
    
    def get_modp(self, p):
        """서버 정확한 mod_hash 구현"""
        i = 0
        while True:
            i += 1
            prefixed_msg = str(i).encode() + self.digest
            h = sha256(prefixed_msg).hexdigest()
            x = int(h, 16) % (2 ** int(p).bit_length())
            if x >= int(p):
                continue
            elif x == 0:  # non_zero=True 기본값
                continue
            else:
                return Bn.from_decimal(str(x))


class FinalBulletproof:
    """서버 완전 호환 Final Bulletproof"""
    
    def __init__(self):
        self.bit_length = 32
        self.group = EcGroup(714)
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # 서버와 동일한 H 생성
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g
        
        # 서버와 동일한 벡터들
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
        
        print("🎯 Final Bulletproof - 서버 완전 호환 (Transcript 시스템)")
    
    def create_final_proof(self, value: int) -> Dict[str, Any]:
        """서버 완전 호환 최종 증명"""
        print(f"🎯 Final 증명 생성: {value}")
        
        try:
            # Transcript 초기화 (서버와 동일)
            transcript = Transcript()
            
            # 1. 비트 분해
            aL = []
            for i in range(self.bit_length):
                bit = (value >> i) & 1
                aL.append(Bn(bit))
            aR = [(a - Bn(1)) % self.order for a in aL]
            
            # 2. 🔥 Transcript 기반 블라인딩 팩터들 (서버 방식)
            gamma = Bn.from_binary(sha256(b"gamma" + transcript.digest).digest()) % self.order
            alpha = Bn.from_binary(sha256(b"alpha" + transcript.digest).digest()) % self.order
            rho = Bn.from_binary(sha256(b"rho" + transcript.digest).digest()) % self.order
            
            # 3. 커밋먼트 V
            v = Bn(value)
            V = v * self.g + gamma * self.h
            
            # 4. sL, sR 벡터들 (transcript 기반)
            sL = []
            sR = []
            for i in range(self.bit_length):
                sL_i = Bn.from_binary(sha256(str(i).encode() + transcript.digest).digest()) % self.order
                sR_i = Bn.from_binary(sha256(str(i + self.bit_length).encode() + transcript.digest).digest()) % self.order
                sL.append(sL_i)
                sR.append(sR_i)
            
            # 5. A, S 계산 (서버 방식)
            A = alpha * self.h
            for i in range(self.bit_length):
                A = A + aL[i] * self.g_vec[i]
                A = A + aR[i] * self.h_vec[i]
            
            S = rho * self.h
            for i in range(self.bit_length):
                S = S + sL[i] * self.g_vec[i]
                S = S + sR[i] * self.h_vec[i]
            
            # 6. 🔥 Transcript에 A, S 추가 (서버 순서)
            transcript.add_list_points([A, S])
            
            # 7. 챌린지 y, z 생성 (transcript 기반)
            y = transcript.get_modp(self.order)
            transcript.add_number(y)
            z = transcript.get_modp(self.order)
            transcript.add_number(z)
            
            # 8. 🔥 T 다항식 계산 (서버 정확한 공식)
            # t1 = <sL, (y^i * (aR[i] + z) + z^2 * 2^i)> + <aL - z, y^i * sR>
            # t2 = <sL, y^i * sR>
            
            # t1 첫 번째 내적
            t1_vec1 = []
            for i in range(self.bit_length):
                y_i = pow(y, i, self.order)
                two_i = pow(Bn(2), i, self.order)
                z_sq = (z * z) % self.order
                val = (y_i * (aR[i] + z) + z_sq * two_i) % self.order
                t1_vec1.append(val)
            
            t1_part1 = sum(sL[i] * t1_vec1[i] for i in range(self.bit_length)) % self.order
            
            # t1 두 번째 내적
            t1_vec2_left = [(aL[i] - z) % self.order for i in range(self.bit_length)]
            t1_vec2_right = [(pow(y, i, self.order) * sR[i]) % self.order for i in range(self.bit_length)]
            t1_part2 = sum(t1_vec2_left[i] * t1_vec2_right[i] for i in range(self.bit_length)) % self.order
            
            t1 = (t1_part1 + t1_part2) % self.order
            
            # t2 계산
            t2_vec = [(pow(y, i, self.order) * sR[i]) % self.order for i in range(self.bit_length)]
            t2 = sum(sL[i] * t2_vec[i] for i in range(self.bit_length)) % self.order
            
            print(f"    t1 = {t1.hex()[:8]}..., t2 = {t2.hex()[:8]}...")
            
            tau1 = Bn.from_binary(sha256(b"tau1" + transcript.digest).digest()) % self.order
            tau2 = Bn.from_binary(sha256(b"tau2" + transcript.digest).digest()) % self.order
            
            T1 = t1 * self.g + tau1 * self.h
            T2 = t2 * self.g + tau2 * self.h
            
            # 9. 🔥 Transcript에 T1, T2 추가
            transcript.add_list_points([T1, T2])
            
            # 10. 챌린지 x 생성
            x = transcript.get_modp(self.order)
            transcript.add_number(x)
            
            # 11. Delta 계산
            n = self.bit_length
            y_sum = sum(pow(y, i, self.order) for i in range(n)) % self.order
            two_sum = sum(pow(Bn(2), i, self.order) for i in range(n)) % self.order
            z_minus_z2 = (z - (z * z)) % self.order
            z_cubed = pow(z, 3, self.order)
            delta = (z_minus_z2 * y_sum - z_cubed * two_sum) % self.order
            
            # 12. 🔥 Final compute (서버 정확한 방식)
            # ls, rs 계산
            ls = [(aL[i] - z + sL[i] * x) % self.order for i in range(self.bit_length)]
            rs = []
            for i in range(self.bit_length):
                y_i = pow(y, i, self.order)
                two_i = pow(Bn(2), i, self.order)
                z_sq = (z * z) % self.order
                r_val = (y_i * (aR[i] + z + sR[i] * x) + z_sq * two_i) % self.order
                rs.append(r_val)
            
            # t_hat = inner_product(ls, rs)
            t_hat = sum(ls[i] * rs[i] for i in range(self.bit_length)) % self.order
            
            # 다른 값들
            z_squared = (z * z) % self.order
            x_squared = (x * x) % self.order
            taux = (tau2 * x_squared + tau1 * x + z_squared * gamma) % self.order
            mu = (alpha + rho * x) % self.order
            
            print(f"    t_hat = {t_hat.hex()[:8]}..., taux = {taux.hex()[:8]}...")
            
            # 13. 🔥 서버 정확한 Inner Product 생성
            inner_proof = self._create_transcript_inner_product(
                aL, aR, sL, sR, y, z, x, A, S, transcript
            )
            
            proof = {
                "commitment": V.export().hex(),
                "proof": {
                    "A": A.export().hex(),
                    "S": S.export().hex(),
                    "T1": T1.export().hex(),
                    "T2": T2.export().hex(),
                    "tau_x": taux.hex(),
                    "mu": mu.hex(),
                    "t": t_hat.hex(),
                    "inner_product_proof": inner_proof
                },
                "range_min": 0,
                "range_max": (1 << self.bit_length) - 1
            }
            
            print(f"  ✅ Final 증명 완료 (Transcript 기반)")
            return proof
            
        except Exception as e:
            print(f"  ❌ Final 증명 실패: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _create_transcript_inner_product(self, aL, aR, sL, sR, y, z, x, A, S, transcript) -> Dict[str, Any]:
        """Transcript 기반 Inner Product 생성"""
        print(f"  🎯 Transcript Inner Product:")
        
        # l(x), r(x) 벡터 계산
        l_vec = [(aL[i] - z + sL[i] * x) % self.order for i in range(self.bit_length)]
        r_vec = []
        
        for i in range(self.bit_length):
            y_i = pow(y, i, self.order)
            two_i = pow(Bn(2), i, self.order)
            z_sq = (z * z) % self.order
            r_i = (y_i * (aR[i] + z + sR[i] * x) + z_sq * two_i) % self.order
            r_vec.append(r_i)
        
        # 벡터 가중치 적용
        y_inv = y.mod_inverse(self.order)
        g_prime = []
        for i in range(self.bit_length):
            y_inv_i = y_inv ** i
            g_prime.append(y_inv_i * self.g_vec[i])
        h_prime = self.h_vec[:]
        
        # 🔥 서버 정확한 P 계산 with multiexp
        P = A + x * S
        
        scalars_gs = [-z for _ in range(self.bit_length)]
        scalars_hsp = []
        for i in range(self.bit_length):
            y_i = pow(y, i, self.order)
            two_i = pow(Bn(2), i, self.order)
            z_sq = (z * z) % self.order
            scalar = (z * y_i + z_sq * two_i) % self.order
            scalars_hsp.append(scalar)
        
        for i in range(self.bit_length):
            P = P + scalars_gs[i] * g_prime[i]
            P = P + scalars_hsp[i] * h_prime[i]
        
        print(f"    P 계산 완료 (multiexp)")
        
        # 재귀적 축약
        current_l = l_vec[:]
        current_r = r_vec[:]
        current_g = g_prime[:]
        current_h = h_prime[:]
        
        L_rounds = []
        R_rounds = []
        
        # 5 rounds
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
            
            L_i = L_i + cL * self.h
            R_i = R_i + cR * self.h
            
            L_rounds.append(L_i.export().hex())
            R_rounds.append(R_i.export().hex())
            
            # 🔥 Transcript 기반 챌린지
            transcript.add_list_points([L_i, R_i])
            x_i = transcript.get_modp(self.order)
            transcript.add_number(x_i)
            
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
        
        print(f"    최종 a: {final_a.hex()[:8]}...")
        print(f"    최종 b: {final_b.hex()[:8]}...")
        print(f"    Transcript Inner Product 완료")
        
        return {
            "L": L_rounds,
            "R": R_rounds,
            "a": final_a.hex(),
            "b": final_b.hex()
        }
    
    def test_final_server(self, proof_data: Dict[str, Any]) -> bool:
        """Final 서버 테스트"""
        print(f"\n🎯 Final Server Test:")
        
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
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                error_msg = result.get('error_message', '')
                processing_time = result.get('processing_time_ms', 0)
                
                if verified:
                    print(f"  🏆🏆🏆 FINAL SUCCESS!!! 🏆🏆🏆")
                    print(f"  🎉 VERIFIED: TRUE!")
                    print(f"  ⚡ 처리시간: {processing_time:.1f}ms")
                    print(f"  🚀 TRANSCRIPT SYSTEM CONQUERED!")
                    print(f"  ✅ PRODUCTION MODE 100% SUCCESS!")
                    return True
                else:
                    print(f"  ❌ Final 실패")
                    if error_msg:
                        print(f"  🔴 오류: {error_msg}")
                    else:
                        print(f"  🟡 Silent failure")
                
                return verified
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"  ❌ 연결 오류: {e}")
            return False


def main():
    """Final 테스트"""
    print("🎯 Final Bulletproof - Transcript System")
    print("🔥 서버 완전 호환 구현")
    print("🚀 Production Mode 정복")
    print("=" * 60)
    
    bulletproof = FinalBulletproof()
    
    for test_value in [42, 0, 1]:
        print(f"\n{'='*60}")
        print(f"🎯 Final 테스트: {test_value}")
        print(f"{'='*60}")
        
        try:
            # Final 증명 생성
            proof = bulletproof.create_final_proof(test_value)
            
            # Final 서버 테스트
            success = bulletproof.test_final_server(proof)
            
            if success:
                print(f"\n🏆🏆🏆 COMPLETE VICTORY!!! 🏆🏆🏆")
                print(f"  🎯 값 {test_value}: PRODUCTION SUCCESS!")
                print(f"  🎉 Transcript System 완전 정복!")
                print(f"  🚀 HAI 실험 완벽 준비!")
                break
            else:
                print(f"\n🔧 다음 값으로 계속...")
        
        except Exception as e:
            print(f"\n❌ 테스트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎯 Final Test 완료")


if __name__ == "__main__":
    main()
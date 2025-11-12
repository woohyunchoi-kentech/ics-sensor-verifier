"""
Bulletproof tau_x 계산 방식 테스트 - 다양한 변형 시도
서버 API 구현과 매칭되는 정확한 계산 방식 찾기
"""

import secrets
from typing import Dict, Any, List

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256


class TauVariantsTester:
    """tau_x 계산 방식 변형들을 테스트"""
    
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
        """Fiat-Shamir 챌린지"""
        hasher = sha256()
        for point in points:
            if isinstance(point, EcPt):
                hasher.update(point.export())
            elif isinstance(point, Bn):
                hasher.update(point.binary())
            else:
                hasher.update(str(point).encode())
        
        return Bn.from_binary(hasher.digest()) % self.order

    def test_tau_variants(self, sensor_value: float = 1.5) -> List[Dict[str, Any]]:
        """다양한 tau_x 계산 방식들 테스트"""
        print("🧪 tau_x 계산 방식 변형 테스트")
        print("="*50)
        
        # 공통 값들 준비
        normalized_value = int((sensor_value - 0.0) / (3.0 - 0.0) * 100)
        value_bn = Bn(normalized_value)
        
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        alpha = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))  
        rho = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        V = value_bn * self.g + gamma * self.h
        A = alpha * self.g + rho * self.h
        S = alpha * self.g + gamma * self.h
        
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)
        
        tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        T1 = tau_1 * self.g + tau_2 * self.h
        T2 = tau_2 * self.g + tau_1 * self.h
        
        x = self._fiat_shamir_challenge(T1, T2, z)
        
        # delta(y,z) 계산
        n = 32
        sum_powers_of_2 = sum(Bn(2) ** i for i in range(n))
        first_term = (z * z) * sum_powers_of_2
        
        second_term = Bn(0)
        for i in range(n):
            second_term += (z ** (i + 3)) * (y ** (i + 1))
        
        delta_yz = first_term + second_term
        t = ((z * z) * value_bn + delta_yz) % self.order
        mu = (alpha + rho * x) % self.order
        
        print(f"공통 값들 준비 완료")
        print(f"  z = {z.hex()[:16]}...")
        print(f"  x = {x.hex()[:16]}...")
        
        # tau_x 계산 방식 변형들
        variants = []
        
        # 변형 1: 표준 공식
        tau_x_1 = ((z * z) * gamma + x * tau_1 + (x * x) * tau_2) % self.order
        variants.append({
            "name": "표준 공식",
            "formula": "z²γ + xτ₁ + x²τ₂", 
            "tau_x": tau_x_1,
            "values": (gamma, tau_1, tau_2, z, x)
        })
        
        # 변형 2: tau_1, tau_2 순서 바뀜
        tau_x_2 = ((z * z) * gamma + x * tau_2 + (x * x) * tau_1) % self.order
        variants.append({
            "name": "tau 순서 바뀜",
            "formula": "z²γ + xτ₂ + x²τ₁",
            "tau_x": tau_x_2,
            "values": (gamma, tau_2, tau_1, z, x)
        })
        
        # 변형 3: z² 없이
        tau_x_3 = (gamma + x * tau_1 + (x * x) * tau_2) % self.order
        variants.append({
            "name": "z² 항 없음",
            "formula": "γ + xτ₁ + x²τ₂",
            "tau_x": tau_x_3,
            "values": (gamma, tau_1, tau_2, z, x)
        })
        
        # 변형 4: x, x² 순서 바뀜
        tau_x_4 = ((z * z) * gamma + (x * x) * tau_1 + x * tau_2) % self.order
        variants.append({
            "name": "x 지수 순서 바뀜",
            "formula": "z²γ + x²τ₁ + xτ₂",
            "tau_x": tau_x_4,
            "values": (gamma, tau_1, tau_2, z, x)
        })
        
        # 변형 5: 부호 변경
        tau_x_5 = ((z * z) * gamma - x * tau_1 + (x * x) * tau_2) % self.order
        variants.append({
            "name": "중간항 음수",
            "formula": "z²γ - xτ₁ + x²τ₂",
            "tau_x": tau_x_5,
            "values": (gamma, tau_1, tau_2, z, x)
        })
        
        return self._test_variants_with_server(variants, V, A, S, T1, T2, t, mu, value_bn, gamma)
    
    def _test_variants_with_server(self, variants: List[Dict], V, A, S, T1, T2, t, mu, value_bn, gamma) -> List[Dict]:
        """각 변형을 서버와 테스트"""
        import requests
        
        results = []
        
        for i, variant in enumerate(variants, 1):
            print(f"\n🧪 변형 {i}: {variant['name']}")
            print(f"   공식: {variant['formula']}")
            print(f"   tau_x = {variant['tau_x'].hex()[:16]}...")
            
            # Inner Product Proof (간단하게)
            L = []
            R = []
            for j in range(5):
                l_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
                r_scalar = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
                L.append((l_scalar * self.g).export().hex())
                R.append((r_scalar * self.g).export().hex())
            
            a = value_bn % self.order
            b = gamma % self.order
            
            # 증명 데이터
            proof_data = {
                "commitment": V.export().hex(),
                "proof": {
                    "A": A.export().hex(),
                    "S": S.export().hex(),
                    "T1": T1.export().hex(),
                    "T2": T2.export().hex(),
                    "tau_x": variant['tau_x'].hex(),
                    "mu": mu.hex(),
                    "t": t.hex(),
                    "L": L,
                    "R": R,
                    "a": a.hex(),
                    "b": b.hex()
                }
            }
            
            # 서버 테스트
            try:
                response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                                       json=proof_data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    status = "✅ 성공!" if result['verified'] else "❌ 실패"
                    time_ms = result['processing_time_ms']
                    print(f"   서버 결과: {status} ({time_ms:.1f}ms)")
                    
                    variant['server_result'] = result['verified']
                    variant['processing_time'] = time_ms
                    
                    if result['verified']:
                        print(f"\n🎉 발견! 변형 {i}이 서버와 호환됩니다!")
                        print(f"올바른 tau_x 공식: {variant['formula']}")
                        results.append(variant)
                        return results  # 성공하면 즉시 반환
                        
                else:
                    print(f"   서버 오류: {response.status_code}")
                    variant['server_result'] = False
                    
            except Exception as e:
                print(f"   통신 오류: {e}")
                variant['server_result'] = False
            
            results.append(variant)
        
        return results


def main():
    """tau_x 변형 테스트 실행"""
    tester = TauVariantsTester()
    
    results = tester.test_tau_variants()
    
    successful_variants = [r for r in results if r.get('server_result', False)]
    
    if successful_variants:
        print(f"\n🎉 성공한 변형들:")
        for variant in successful_variants:
            print(f"  - {variant['name']}: {variant['formula']}")
        print(f"\n🚀 이제 올바른 tau_x 공식을 알았습니다!")
    else:
        print(f"\n😞 모든 변형이 실패했습니다.")
        print(f"더 복잡한 tau_x 계산 방식이나 다른 이슈가 있을 수 있습니다.")


if __name__ == "__main__":
    main()
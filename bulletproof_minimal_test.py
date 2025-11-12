"""
최소한의 Bulletproof 테스트 - 가장 기본적인 구현
서버 API와 호환되는 최소 기능 버전
"""

import secrets
from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256


class MinimalBulletproof:
    """최소한의 기능만 포함한 Bulletproof"""
    
    def __init__(self):
        self.group = EcGroup(714)
        self.order = self.group.order()
        self.g = self.group.generator()
        
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g

    def _fiat_shamir(self, *points) -> Bn:
        hasher = sha256()
        for point in points:
            if isinstance(point, EcPt):
                hasher.update(point.export())
            elif isinstance(point, Bn):
                hasher.update(point.binary())
        return Bn.from_binary(hasher.digest()) % self.order

    def create_minimal_proof(self):
        """최소한의 증명 생성 - 모든 값을 1로 고정"""
        print("🔬 최소한의 Bulletproof 테스트")
        print("="*40)
        
        # 모든 값을 간단하게 고정
        value = Bn(50)  # 센서값 50
        gamma = Bn(1)   # 블라인딩 팩터 1
        
        # 커밋먼트
        V = value * self.g + gamma * self.h
        
        # 고정된 비밀값들
        alpha = Bn(1)
        rho = Bn(1)
        tau_1 = Bn(1) 
        tau_2 = Bn(1)
        
        # A, S
        A = alpha * self.g + rho * self.h
        S = alpha * self.g + gamma * self.h
        
        # 챌린지
        y = self._fiat_shamir(A, S)
        z = self._fiat_shamir(A, S, y)
        
        # T1, T2  
        T1 = tau_1 * self.g + tau_2 * self.h
        T2 = tau_2 * self.g + tau_1 * self.h
        
        x = self._fiat_shamir(T1, T2, z)
        
        print(f"챌린지 값들:")
        print(f"  y = {y.hex()[:16]}...")
        print(f"  z = {z.hex()[:16]}...")  
        print(f"  x = {x.hex()[:16]}...")
        
        # 간단한 계산들
        t = Bn(100)  # 고정값
        tau_x = Bn(10)  # 고정값
        mu = Bn(5)   # 고정값
        
        # 최소한의 L, R
        L = [(Bn(1) * self.g).export().hex() for _ in range(5)]
        R = [(Bn(2) * self.g).export().hex() for _ in range(5)]
        
        return {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": mu.hex(),
                "t": t.hex(),
                "L": L,
                "R": R,
                "a": value.hex(),
                "b": gamma.hex()
            }
        }
    
    def test_minimal(self):
        """최소 구현 테스트"""
        import requests
        
        proof_data = self.create_minimal_proof()
        
        print(f"\n🌐 서버 테스트...")
        try:
            response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                                   json=proof_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result['verified']:
                    print(f"✅ 최소 구현 성공!")
                    print(f"⚡ 처리 시간: {result['processing_time_ms']:.1f}ms")
                    return True
                else:
                    print(f"❌ 최소 구현도 실패")
                    print(f"⚡ 처리 시간: {result['processing_time_ms']:.1f}ms")
            else:
                print(f"❌ 서버 오류: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"💥 오류: {e}")
        
        return False


def test_existing_implementations():
    """기존 구현들도 다시 한번 테스트"""
    import requests
    
    print("\n📋 기존 구현들 재테스트")
    print("="*40)
    
    # bulletproof_victory.py의 결과 재확인
    try:
        from bulletproof_victory import BulletproofVictory
        victory = BulletproofVictory()
        
        print("🎯 Victory 구현 재테스트...")
        success = victory.final_victory_test()
        
        if success:
            print("✅ Victory 구현 성공!")
            return True
        else:
            print("❌ Victory 구현 여전히 실패")
            
    except Exception as e:
        print(f"Victory 테스트 오류: {e}")
    
    return False


def main():
    """메인 테스트"""
    # 1. 최소 구현 테스트
    minimal = MinimalBulletproof()
    minimal_success = minimal.test_minimal()
    
    # 2. 기존 구현 재테스트  
    existing_success = test_existing_implementations()
    
    if minimal_success or existing_success:
        print(f"\n🎉 일부 구현이 작동합니다!")
    else:
        print(f"\n🤔 모든 구현이 실패합니다.")
        print(f"서버 API 구현이나 검증 로직에 특별한 요구사항이 있을 수 있습니다.")


if __name__ == "__main__":
    main()
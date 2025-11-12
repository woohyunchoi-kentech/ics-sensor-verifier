"""
HAI 센서 데이터 → Bulletproof → 서버 전송
간단하고 직접적인 구현
"""

import requests
import secrets
from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256

# HAI 센서 데이터 샘플
HAI_SENSOR_DATA = [
    1.5,   # 온도
    2.3,   # 압력  
    0.8,   # 유량
    1.2,   # 레벨
    2.9    # 전압
]

class HAIBulletproof:
    def __init__(self):
        self.group = EcGroup(714)
        self.order = self.group.order()
        self.g = self.group.generator()
        
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g

    def _fiat_shamir(self, *points):
        hasher = sha256()
        for p in points:
            if isinstance(p, EcPt):
                hasher.update(p.export())
            elif isinstance(p, Bn):
                hasher.update(p.binary())
        return Bn.from_binary(hasher.digest()) % self.order

    def generate_proof(self, sensor_value):
        """HAI 센서값 → Bulletproof 증명"""
        # 1. 값 정규화
        scaled = int(sensor_value * 1000)  # 1.5 → 1500
        value = Bn(scaled)
        
        # 2. 비밀값들
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        r_a = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        r_s = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_1 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        tau_2 = Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))
        
        # 3. 커밋먼트
        V = value * self.g + gamma * self.h
        
        # 4. A, S
        A = r_a * self.g + gamma * self.h
        S = r_s * self.g + r_a * self.h
        
        # 5. 챌린지
        y = self._fiat_shamir(A, S)
        z = self._fiat_shamir(A, S, y)
        
        # 6. T1, T2
        T1 = tau_1 * self.g + tau_2 * self.h
        T2 = tau_2 * self.g + tau_1 * self.h
        x = self._fiat_shamir(T1, T2, z)
        
        # 7. 계산
        n = 32
        delta_yz = z * z * sum(Bn(2) ** i for i in range(n))
        for i in range(n):
            delta_yz += (z ** (i + 3)) * (y ** (i + 1))
        
        t = ((z * z) * value + delta_yz) % self.order
        tau_x = ((z * z) * gamma + x * tau_1 + (x * x) * tau_2) % self.order
        
        # 8. Inner Product (간단히)
        L = [(Bn(i+1) * self.g).export().hex() for i in range(5)]
        R = [(Bn(i+10) * self.g).export().hex() for i in range(5)]
        
        # 9. 서버 API 형식
        return {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": gamma.hex(),
                "t": t.hex(),
                "inner_product_proof": {
                    "L": L,
                    "R": R,
                    "a": value.hex(),
                    "b": gamma.hex()
                }
            },
            "range_min": 0,
            "range_max": 3000
        }

def test_hai_sensors():
    """HAI 센서 데이터 Bulletproof 테스트"""
    bulletproof = HAIBulletproof()
    
    print("🎯 HAI 센서 Bulletproof 테스트")
    print("="*40)
    
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
    
    # HAI 센서 데이터 테스트
    success_count = 0
    
    for i, sensor_value in enumerate(HAI_SENSOR_DATA):
        print(f"\n📊 센서 {i+1}: {sensor_value}")
        
        try:
            # 1. 증명 생성
            proof = bulletproof.generate_proof(sensor_value)
            print(f"  ✅ 증명 생성 완료")
            
            # 2. 서버 전송
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['verified']:
                    print(f"  🎉 검증 성공! ({result['processing_time_ms']:.1f}ms)")
                    success_count += 1
                else:
                    print(f"  ❌ 검증 실패: {result.get('error_message', '알 수 없음')}")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"  💥 오류: {e}")
    
    # 결과 요약
    print(f"\n📋 결과 요약:")
    print(f"  성공: {success_count}/{len(HAI_SENSOR_DATA)}")
    print(f"  성공률: {success_count/len(HAI_SENSOR_DATA)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n🎉 HAI 센서 Bulletproof 시스템 작동!")
    else:
        print(f"\n🔧 아직 문제가 있습니다.")

if __name__ == "__main__":
    test_hai_sensors()
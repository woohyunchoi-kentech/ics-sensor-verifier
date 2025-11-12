"""
최종 디버깅: 서버 검증 방정식과 정확히 일치시키기
"""

from fixed_bulletproof import FixedBulletproof
from petlib.ec import EcPt
from petlib.bn import Bn
import requests

def final_verification_debug():
    """최종 검증 방정식 디버깅"""
    print("🔍 최종 검증 방정식 디버깅")
    print("="*50)
    
    bulletproof = FixedBulletproof()
    sensor_value = 1.5
    
    # 증명 생성
    proof_data = bulletproof.generate_hai_proof(sensor_value)
    
    # 데이터 추출
    commitment_hex = proof_data['commitment']
    proof = proof_data['proof']
    scaled_value = proof_data['scaled_value']
    
    print(f"센서값: {sensor_value} → 스케일링: {scaled_value}")
    
    # EC 포인트들 파싱
    V = EcPt.from_binary(bytes.fromhex(commitment_hex), bulletproof.group)
    A = EcPt.from_binary(bytes.fromhex(proof['A']), bulletproof.group)
    S = EcPt.from_binary(bytes.fromhex(proof['S']), bulletproof.group)
    T1 = EcPt.from_binary(bytes.fromhex(proof['T1']), bulletproof.group)
    T2 = EcPt.from_binary(bytes.fromhex(proof['T2']), bulletproof.group)
    
    # 스칼라들 파싱
    t = Bn.from_hex(proof['t'])
    tau_x = Bn.from_hex(proof['tau_x'])
    mu = Bn.from_hex(proof['mu'])
    
    # 챌린지 재계산 (서버와 동일한 방식)
    y = bulletproof._fiat_shamir_challenge(A, S)
    z = bulletproof._fiat_shamir_challenge(A, S, y)
    x = bulletproof._fiat_shamir_challenge(T1, T2, z)
    
    print(f"\\n📐 챌린지들:")
    print(f"  y = {y.hex()}")
    print(f"  z = {z.hex()}")
    print(f"  x = {x.hex()}")
    
    # Delta(y,z) 재계산 (서버와 정확히 동일)
    n = 32
    delta_yz = z * z * sum(Bn(2) ** i for i in range(n))
    for i in range(n):
        delta_yz += (z ** (i + 3)) * (y ** (i + 1))
    delta_yz = delta_yz % bulletproof.order
    
    print(f"\\n🧮 계산 결과들:")
    print(f"  t = {t.hex()}")
    print(f"  tau_x = {tau_x.hex()}")
    print(f"  delta(y,z) = {delta_yz.hex()}")
    
    # 검증 방정식 수동 계산
    print(f"\\n🔍 검증 방정식: g^t * h^tau_x ?= V^(z^2) * g^delta(y,z) * T1^x * T2^(x^2)")
    
    # 좌변: g^t * h^tau_x
    left_side = t * bulletproof.g + tau_x * bulletproof.h
    
    # 우변: V^(z^2) * g^delta(y,z) * T1^x * T2^(x^2)
    z_squared = z * z % bulletproof.order
    x_squared = x * x % bulletproof.order
    
    print(f"\\n우변 계산 과정:")
    print(f"  z^2 = {z_squared.hex()}")
    print(f"  x^2 = {x_squared.hex()}")
    
    # 각 항목 계산
    term1 = z_squared * V
    term2 = delta_yz * bulletproof.g
    term3 = x * T1
    term4 = x_squared * T2
    
    print(f"\\n  V^(z^2) = {term1.export().hex()}")
    print(f"  g^delta = {term2.export().hex()}")
    print(f"  T1^x = {term3.export().hex()}")
    print(f"  T2^(x^2) = {term4.export().hex()}")
    
    right_side = term1 + term2 + term3 + term4
    
    print(f"\\n결과:")
    print(f"  좌변 = {left_side.export().hex()}")
    print(f"  우변 = {right_side.export().hex()}")
    
    equations_match = left_side == right_side
    print(f"\\n✅ 방정식 일치: {'예' if equations_match else '아니오'}")
    
    if not equations_match:
        print(f"\\n💡 가능한 원인들:")
        print(f"  1. 서버의 Delta(y,z) 계산이 여전히 다를 수 있음")
        print(f"  2. 서버의 챌린지 생성 순서가 다를 수 있음") 
        print(f"  3. 서버의 모듈로 연산 시점이 다를 수 있음")
        print(f"  4. 내적 증명과의 연결 부분에서 차이")
        
        # 서버 실제 응답과 비교
        print(f"\\n🌐 서버로 실제 전송해서 비교:")
        response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                               json=proof_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"  서버 검증: {'성공' if result['verified'] else '실패'}")
            print(f"  오류: {result.get('error_message', 'None')}")
            print(f"  처리 시간: {result['processing_time_ms']:.1f}ms")
        
        # 추가 분석: t와 tau_x 역계산
        print(f"\\n🔄 t, tau_x 역계산 검증:")
        expected_t = ((z * z) * Bn(scaled_value) + delta_yz) % bulletproof.order
        print(f"  기대하는 t = {expected_t.hex()}")
        print(f"  실제 t = {t.hex()}")
        print(f"  t 일치: {'예' if expected_t == t else '아니오'}")
        
    else:
        print(f"🎉 클라이언트 계산이 완벽함! 서버에 버그가 있을 수 있습니다.")
    
    return equations_match

if __name__ == "__main__":
    final_verification_debug()
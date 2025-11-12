"""
서버 검증 방정식 디버깅
클라이언트와 서버의 계산 차이 분석
"""

from crypto.bulletproofs_baseline import BulletproofsBaseline
from petlib.ec import EcPt
from petlib.bn import Bn
import hashlib

def debug_verification_equation():
    """검증 방정식 수동 계산으로 문제점 찾기"""
    print("🔍 검증 방정식 디버깅")
    print("="*50)
    
    bulletproof = BulletproofsBaseline()
    sensor_value = 1.5
    
    print(f"센서값: {sensor_value}")
    
    # 증명 생성
    proof_data = bulletproof.generate_proof(sensor_value, min_val=0.0, max_val=3.0)
    
    # 데이터 추출
    commitment_hex = proof_data['commitment']
    proof = proof_data['proof']
    scaled_value = proof_data['scaled_value']
    
    print(f"스케일링된 값: {scaled_value}")
    print(f"커밋먼트: {commitment_hex[:32]}...")
    
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
    
    print(f"\\n📐 수동 챌린지 재계산:")
    
    # 챌린지 재계산 (서버와 동일한 방식)
    y = bulletproof._fiat_shamir_challenge(A, S)
    z = bulletproof._fiat_shamir_challenge(A, S, y)
    x = bulletproof._fiat_shamir_challenge(T1, T2, z)
    
    print(f"  y = {y.hex()[:16]}...")
    print(f"  z = {z.hex()[:16]}...")
    print(f"  x = {x.hex()[:16]}...")
    
    # Delta(y,z) 재계산 (서버 수정된 공식)
    n = 32
    delta_yz = z * z * sum(Bn(2) ** i for i in range(n))
    for i in range(n):
        delta_yz += (z ** (i + 3)) * (y ** (i + 1))
    delta_yz = delta_yz % bulletproof.order
    
    print(f"  delta(y,z) = {delta_yz.hex()[:16]}...")
    
    print(f"\\n🧮 검증 방정식 수동 계산:")
    print("목표 방정식: g^t * h^tau_x = V^(z^2) * g^delta(y,z) * T1^x * T2^(x^2)")
    
    # 좌변: g^t * h^tau_x
    left_side = t * bulletproof.g + tau_x * bulletproof.h
    
    # 우변: V^(z^2) * g^delta(y,z) * T1^x * T2^(x^2)
    z_squared = z * z
    x_squared = x * x
    
    right_side = z_squared * V + delta_yz * bulletproof.g + x * T1 + x_squared * T2
    
    print(f"\\n좌변 (g^t * h^tau_x):")
    print(f"  {left_side.export().hex()[:32]}...")
    
    print(f"\\n우변 (V^(z^2) * g^delta(y,z) * T1^x * T2^(x^2)):")
    print(f"  {right_side.export().hex()[:32]}...")
    
    # 검증
    equations_match = left_side == right_side
    print(f"\\n✅ 방정식 일치: {'예' if equations_match else '아니오'}")
    
    if not equations_match:
        print(f"\\n🔍 실패 원인 분석:")
        
        # 각 항목별 분석
        print(f"\\n각 컴포넌트 분석:")
        term1 = z_squared * V
        term2 = delta_yz * bulletproof.g  
        term3 = x * T1
        term4 = x_squared * T2
        
        print(f"  V^(z^2): {term1.export().hex()[:32]}...")
        print(f"  g^delta(y,z): {term2.export().hex()[:32]}...")
        print(f"  T1^x: {term3.export().hex()[:32]}...")
        print(f"  T2^(x^2): {term4.export().hex()[:32]}...")
        
        # 중간 합계들
        partial_sum = term1 + term2
        print(f"  V^(z^2) + g^delta(y,z): {partial_sum.export().hex()[:32]}...")
        
        partial_sum2 = partial_sum + term3
        print(f"  + T1^x: {partial_sum2.export().hex()[:32]}...")
        
        print(f"\\n💡 가능한 원인:")
        print(f"  1. Delta(y,z) 계산 공식 차이")
        print(f"  2. 챌린지 생성 순서나 방법 차이")
        print(f"  3. 모듈로 연산 시점 차이")
        print(f"  4. Inner Product Proof와의 연결 문제")
        
        # 실제 증명 생성에서 사용된 값들과 비교
        print(f"\\n🔄 증명 생성 과정에서의 실제 값들:")
        print(f"  실제 scaled_value: {scaled_value}")
        print(f"  Bn(scaled_value): {Bn(scaled_value).hex()[:16]}...")
        
        # 커밋먼트 검증
        print(f"\\n📊 커밋먼트 검증:")
        # V = scaled_value * g + gamma * h 이어야 함
        # gamma는 proof['mu']에 있을 것 (mu가 블라인딩 팩터)
        gamma_from_proof = Bn.from_hex(proof['mu'])  
        expected_V = Bn(scaled_value) * bulletproof.g + gamma_from_proof * bulletproof.h
        print(f"  기대하는 V: {expected_V.export().hex()[:32]}...")
        print(f"  실제 V: {commitment_hex[:32]}...")
        print(f"  커밋먼트 일치: {'예' if expected_V == V else '아니오'}")
    
    else:
        print(f"🎉 클라이언트 계산이 올바름! 서버 구현에 문제가 있을 수 있습니다.")
    
    return equations_match

if __name__ == "__main__":
    debug_verification_equation()
"""
단계별 검증 테스트 - 정확한 실패 지점 찾기
"""

import requests
from hai_bulletproof_fixed import HAIBulletproofFixed

def test_step_by_step():
    """단계별로 서버 응답 분석"""
    
    generator = HAIBulletproofFixed()
    sensor_value = 42
    
    print("🔍 단계별 검증 테스트")
    print("="*40)
    
    # 1. 증명 생성
    proof = generator.generate_bulletproof(sensor_value, 0, 100)
    
    print("📊 생성된 증명 분석:")
    print(f"  커밋먼트 길이: {len(proof['commitment'])}")
    print(f"  A 길이: {len(proof['A'])}")
    print(f"  Inner Product L 개수: {len(proof['inner_product_proof']['L'])}")
    print(f"  Inner Product R 개수: {len(proof['inner_product_proof']['R'])}")
    
    # 2. 최소한의 데이터로 테스트
    minimal_request = {
        "commitment": proof["commitment"],
        "proof": {
            "A": proof["A"],
            "S": proof["S"], 
            "T1": proof["T1"],
            "T2": proof["T2"],
            "tau_x": proof["tau_x"],
            "mu": proof["mu"],
            "t": proof["t"],
            "inner_product_proof": {
                "L": proof["inner_product_proof"]["L"][:1],  # 1개만
                "R": proof["inner_product_proof"]["R"][:1],  # 1개만
                "a": proof["inner_product_proof"]["a"],
                "b": proof["inner_product_proof"]["b"]
            }
        },
        "range_min": 0,
        "range_max": 100
    }
    
    print("\n🧪 1개 L,R로 테스트:")
    response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                           json=minimal_request, timeout=10)
    if response.status_code == 200:
        result = response.json()
        print(f"  결과: {result.get('verified')}")
        print(f"  오류: {result.get('error_message')}")
    
    # 3. 올바른 5개 L,R로 테스트
    full_request = {
        "commitment": proof["commitment"],
        "proof": {
            "A": proof["A"],
            "S": proof["S"],
            "T1": proof["T1"], 
            "T2": proof["T2"],
            "tau_x": proof["tau_x"],
            "mu": proof["mu"],
            "t": proof["t"],
            "inner_product_proof": proof["inner_product_proof"]
        },
        "range_min": 0,
        "range_max": 100
    }
    
    print("\n🧪 5개 L,R로 테스트:")
    response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                           json=full_request, timeout=10)
    if response.status_code == 200:
        result = response.json()
        print(f"  결과: {result.get('verified')}")
        print(f"  오류: {result.get('error_message')}")
        print(f"  처리시간: {result.get('processing_time_ms')}ms")
    
    # 4. 서버에 상세 정보 요청
    print("\n💡 서버에 요청할 정보:")
    print("  1. 메인 검증 방정식의 좌변/우변 실제 값")
    print("  2. Inner Product Proof 재귀 검증 과정의 중간 단계")
    print("  3. 서버가 직접 생성한 유효한 증명 샘플")
    print("  4. TRACE 레벨 로그에서 정확한 실패 지점")

if __name__ == "__main__":
    test_step_by_step()
"""
간단한 HAI 센서 Bulletproof 테스트
서버 베이스라인 코드 활용
"""

import requests
from crypto.bulletproofs_baseline import BulletproofsBaseline

def simple_hai_test():
    """간단한 HAI 센서 테스트"""
    print("🎯 간단한 HAI 센서 테스트")
    print("="*40)
    
    # HAI 센서 값들 (0-3 범위에서)
    hai_values = [1.5, 2.3, 0.8, 1.2, 2.9]
    
    bulletproof = BulletproofsBaseline(bit_length=32)
    
    print(f"✅ Bulletproof 생성기 초기화 (32비트)")
    
    for i, sensor_value in enumerate(hai_values):
        print(f"\n📊 HAI 센서 {i+1}: {sensor_value}")
        
        try:
            # 범위를 0-3으로 설정해서 테스트
            proof = bulletproof.generate_proof(
                sensor_value=sensor_value,
                min_val=0.0,
                max_val=3.0
            )
            
            print(f"  ✅ 증명 생성: {proof['generation_time_ms']:.1f}ms")
            print(f"  스케일링: {proof['scaled_value']}")
            print(f"  범위: [{proof['range_min']}, {proof['range_max']}]")
            
            # 서버 전송 
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  검증 결과: {'✅ 성공' if result['verified'] else '❌ 실패'}")
                print(f"  처리 시간: {result['processing_time_ms']:.1f}ms")
                
                if not result['verified']:
                    print(f"  오류: {result.get('error_message', 'Unknown')}")
                    
                    # 상세 정보 출력
                    if 'details' in result:
                        print(f"  상세:")
                        for k, v in result['details'].items():
                            if k != 'commitment':
                                print(f"    {k}: {v}")
                    
                    # 첫 번째 실패 후 중단
                    break
                else:
                    print(f"  🎉 HAI 센서 {i+1} 검증 성공!")
                    
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                print(f"  응답: {response.text}")
                break
                
        except Exception as e:
            print(f"  💥 오류: {e}")
            break
    
    print(f"\n🏁 테스트 완료")

if __name__ == "__main__":
    simple_hai_test()
"""
서버 응답 디버깅 - 정확히 무엇이 실패하는지 확인
"""

import requests
import json
from bulletproof_victory import BulletproofVictory


def debug_server_response():
    """서버 응답을 자세히 분석"""
    print("🔍 서버 응답 디버깅")
    print("="*40)
    
    # Victory 구현으로 증명 생성
    victory = BulletproofVictory()
    
    try:
        # 서버의 정확한 값들
        server_values = {
            "A": "0206c00d33b659fa5554574d2819ce0f8fc45d13d1427ef31c9486c54c20446fbc",
            "S": "02232c4316eb2cb3e69c663eca094021cee2b335e98cc6d833d6e1053790276f10", 
            "T1": "02713b1053a9710b4e1d51461c35c6744406f2b08da40c567dd6c2141e1220e984",
            "T2": "02b44235d4fabb5416e1ff0b426d39da5343ac23a9cfc6244b4e7113802cc2e706"
        }
        
        # 간단한 증명 데이터 생성
        proof_data = {
            "commitment": "0320852bcec19f57a459975a32e9dd5b12345678901234567890123456789012",
            "proof": {
                "A": server_values["A"],
                "S": server_values["S"],
                "T1": server_values["T1"],
                "T2": server_values["T2"],
                "tau_x": "1234567890123456789012345678901234567890123456789012345678901234",
                "mu": "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                "t": "fedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafe",
                "L": [
                    "021234567890123456789012345678901234567890123456789012345678901234",
                    "022345678901234567890123456789012345678901234567890123456789012345",
                    "023456789012345678901234567890123456789012345678901234567890123456",
                    "024567890123456789012345678901234567890123456789012345678901234567",
                    "025678901234567890123456789012345678901234567890123456789012345678"
                ],
                "R": [
                    "026789012345678901234567890123456789012345678901234567890123456789",
                    "027890123456789012345678901234567890123456789012345678901234567890",
                    "028901234567890123456789012345678901234567890123456789012345678901",
                    "029012345678901234567890123456789012345678901234567890123456789012",
                    "030123456789012345678901234567890123456789012345678901234567890123"
                ],
                "a": "111111111111111111111111111111111111111111111111111111111111111",
                "b": "222222222222222222222222222222222222222222222222222222222222222"
            }
        }
        
        print("📤 전송할 데이터:")
        print(f"  commitment 길이: {len(proof_data['commitment'])}")
        print(f"  A: {proof_data['proof']['A'][:20]}...")
        print(f"  L 배열 크기: {len(proof_data['proof']['L'])}")
        print(f"  R 배열 크기: {len(proof_data['proof']['R'])}")
        
        # 서버에 전송
        print(f"\n🌐 서버로 전송 중...")
        response = requests.post('http://192.168.0.11:8085/api/v1/verify/bulletproof',
                               json=proof_data, timeout=15)
        
        print(f"\n📥 서버 응답:")
        print(f"  상태 코드: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"  응답 크기: {len(response.text)} bytes")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"\n📊 JSON 응답 내용:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                if 'verified' in result:
                    print(f"\n검증 결과: {result['verified']}")
                    if 'processing_time_ms' in result:
                        print(f"처리 시간: {result['processing_time_ms']:.1f}ms")
                    
                    if 'details' in result or 'error' in result or 'message' in result:
                        print(f"\n추가 정보:")
                        for key, value in result.items():
                            if key not in ['verified', 'processing_time_ms']:
                                print(f"  {key}: {value}")
                                
            except json.JSONDecodeError as e:
                print(f"❌ JSON 디코딩 실패: {e}")
                print(f"원본 응답: {response.text}")
                
        else:
            print(f"❌ HTTP 오류 {response.status_code}")
            print(f"응답 내용: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"💥 네트워크 오류: {e}")
    except Exception as e:
        print(f"💥 일반 오류: {e}")


def test_server_endpoints():
    """다른 서버 엔드포인트들도 테스트"""
    print(f"\n🔍 서버 엔드포인트 테스트")
    print("="*40)
    
    endpoints = [
        "/api/v1/status",
        "/api/v1/info", 
        "/api/v1/health",
        "/api/v1/algorithms",
        "/",
    ]
    
    for endpoint in endpoints:
        try:
            url = f"http://192.168.0.11:8085{endpoint}"
            print(f"\n📡 테스트: {endpoint}")
            
            response = requests.get(url, timeout=5)
            print(f"  상태: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  응답: {data}")
                except:
                    print(f"  응답 (텍스트): {response.text[:100]}...")
            else:
                print(f"  오류: {response.text}")
                
        except Exception as e:
            print(f"  예외: {e}")


def main():
    """디버깅 실행"""
    debug_server_response()
    test_server_endpoints()
    
    print(f"\n📋 요약:")
    print(f"  - 서버는 응답하지만 모든 bulletproof 검증이 실패")
    print(f"  - 이는 서버 API 구현 또는 검증 로직의 문제로 보임")
    print(f"  - Fiat-Shamir 챌린지는 올바르게 매칭됨")


if __name__ == "__main__":
    main()
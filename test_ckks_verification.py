#!/usr/bin/env python3
"""
CKKS 서버 검증 요청 테스트
실제로 서버에 암호화된 데이터를 보내고 검증 결과를 받습니다.
"""

import json
import time
import requests
import pandas as pd
from crypto.ckks_baseline import CKKSBaseline

def send_to_server_for_verification(proof_data, ckks, server_url='http://192.168.0.11:8085'):
    """서버에 CKKS 증명 데이터를 보내고 검증 결과를 받음"""
    try:
        # 서버 검증 엔드포인트
        verify_url = f"{server_url}/api/v1/ckks/verify"
        
        # context 필드는 필수 - 빈 hex 또는 더미 값으로 시도
        import base64
        
        # 서버에서 지원하는 context_id 사용 (더미 context 제거)
        print(f"   Context ID 사용: {proof_data['context_id']}")
        
        # 검증 요청 데이터 - 올바른 context 필드 형식
        verification_request = {
            "sensor_id": "DM-PIT01", 
            "timestamp": proof_data['timestamp'],
            "encrypted_data": proof_data['encrypted_data'],
            "context": proof_data['context_id'],  # context_id 값을 context 필드에 사용
            "algorithm": "CKKS"
        }
        
        # POST 요청으로 서버에 검증 요청 - 상세 로깅 추가
        print(f"📤 서버에 검증 요청 전송 중...")
        print(f"   요청 URL: {verify_url}")
        print(f"   요청 시간: {time.strftime('%H:%M:%S')}")
        
        # 실제 HTTP 요청 전송
        try:
            response = requests.post(
                verify_url,
                json=verification_request,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"   응답 시간: {time.strftime('%H:%M:%S')}")
        except requests.exceptions.ConnectTimeout:
            print(f"   ❌ 연결 타임아웃 - 서버에 도달할 수 없음")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ 연결 오류 - {e}")
            raise
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 서버 응답 받음")
            print(f"   서버 응답: {result}")
            
            # 서버가 실패를 반환한 경우
            if not result.get('success', False):
                print(f"   ⚠️ 서버 검증 실패: {result.get('error_message', 'Unknown error')}")
            
            return {
                "success": result.get('success', False),
                "decrypted_value": result.get('decrypted_value'),
                "verification_time_ms": result.get('processing_time_ms'),
                "server_response": result
            }
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            print(f"   응답: {response.text}")
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "response": response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

def main():
    """메인 테스트 함수"""
    print("🧪 CKKS 서버 검증 테스트")
    print("=" * 60)
    
    # CKKS 클라이언트 초기화
    ckks = CKKSBaseline()
    server_url = 'http://192.168.0.11:8085'
    
    # 서버 공개키 로드
    print("🔑 서버 공개키 로드 중...")
    if not ckks.load_server_public_key_from_api(server_url):
        print("❌ 공개키 로드 실패")
        return
    
    # HAI 데이터에서 테스트 값 로드
    print("\n📊 HAI 센서 데이터 로드 중...")
    csv_path = 'data/hai/haiend-23.05/end-train1.csv'
    df = pd.read_csv(csv_path)
    sensor_id = 'DM-PIT01'
    sensor_data = df[sensor_id].dropna().clip(0.0, 3.0)
    test_values = sensor_data.sample(n=5).tolist()
    
    print(f"테스트 값: {[f'{v:.6f}' for v in test_values]}")
    
    # 결과 저장용
    all_results = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server_url": server_url,
        "sensor_id": sensor_id,
        "total_tests": len(test_values),
        "successful_verifications": 0,
        "test_details": []
    }
    
    # 각 값에 대해 테스트
    for i, value in enumerate(test_values, 1):
        print(f"\n🔬 테스트 {i}/{len(test_values)}")
        print(f"   원본 값: {value:.6f}")
        
        try:
            # 1. CKKS 증명 생성
            start_time = time.perf_counter()
            proof_data = ckks.generate_proof(value)
            generation_time = (time.perf_counter() - start_time) * 1000
            print(f"   ✅ 암호화 완료 ({generation_time:.1f}ms)")
            
            # 2. 서버에 검증 요청
            verification_result = send_to_server_for_verification(proof_data, ckks, server_url)
            
            # 3. 결과 기록
            test_result = {
                "test_num": i,
                "original_value": value,
                "generation_time_ms": generation_time,
                "encrypted_size_bytes": proof_data['encrypted_size_bytes'],
                "server_verification": verification_result
            }
            
            if verification_result['success']:
                all_results['successful_verifications'] += 1
                decrypted = verification_result.get('decrypted_value', 'N/A')
                if decrypted != 'N/A':
                    error = abs(decrypted - value)
                    error_pct = (error / value) * 100 if value != 0 else 0
                    print(f"   📊 복호화 값: {decrypted:.6f}")
                    print(f"   📏 오차: {error:.6f} ({error_pct:.4f}%)")
                    test_result['error'] = error
                    test_result['error_percentage'] = error_pct
            else:
                print(f"   ❌ 검증 실패: {verification_result.get('error')}")
            
            all_results['test_details'].append(test_result)
            
        except Exception as e:
            print(f"   ❌ 테스트 실패: {e}")
            test_result = {
                "test_num": i,
                "original_value": value,
                "error": str(e),
                "success": False
            }
            all_results['test_details'].append(test_result)
        
        # 서버 부하 방지를 위한 짧은 대기
        time.sleep(0.5)
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("📈 최종 결과")
    print(f"총 테스트: {all_results['total_tests']}")
    print(f"서버 검증 성공: {all_results['successful_verifications']}")
    print(f"성공률: {(all_results['successful_verifications']/all_results['total_tests']*100):.1f}%")
    
    # 결과 파일로 저장
    timestamp = int(time.time())
    output_file = f"ckks_server_verification_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 결과 저장됨: {output_file}")
    print("\n⚠️  서버 로그를 확인하여 검증 요청이 도착했는지 확인하세요!")

if __name__ == "__main__":
    main()
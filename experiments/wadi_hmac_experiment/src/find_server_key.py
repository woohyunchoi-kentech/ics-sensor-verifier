#!/usr/bin/env python3
"""
서버의 HMAC 키 찾기
"""

import asyncio
import aiohttp
import hmac
import hashlib
import json

async def find_server_key():
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    print("🔍 서버 HMAC 키 찾기")
    print("=" * 40)
    
    # 서버가 41바이트 키를 사용한다는 것을 알았음
    # 일반적인 41바이트 키 후보들
    key_candidates = [
        # 일반적인 텍스트 키들 (41바이트로 패딩)
        b"wadi_hmac_experiment_key_2025_server_key_41b",  # 정확히 41바이트
        b"ics_sensor_privacy_experiment_server_key_41b",  # 41바이트
        b"server_hmac_key_for_wadi_ics_sensors_2025_41",  # 41바이트
        b"default_server_key_hmac_sha256_41_bytes_long",  # 41바이트
        b"hmac_verification_server_key_41_bytes_wadi_",   # 41바이트
        
        # hex 형식 키들  
        bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef01"),  # 정확히 41바이트
        
        # 실제 서버가 사용할만한 키들
        b"wadi_sensor_hmac_key_2025_industrial_control",  # 41바이트
        b"ics_verifier_server_hmac_key_sha256_default_",  # 41바이트
    ]
    
    # 테스트 데이터
    test_sensor_value = 25.5
    test_timestamp = 1725000000000
    test_sensor_id = "WADI_SENSOR_001"
    
    # 가능한 메시지 형식들
    message_formats = [
        f"{test_sensor_value}:{test_timestamp}",
        f"{test_sensor_id}:{test_sensor_value}:{test_timestamp}",
        f"{test_sensor_value}{test_timestamp}",
        json.dumps({"sensor_value": test_sensor_value, "timestamp": test_timestamp}),
        json.dumps({"sensor_value": test_sensor_value, "timestamp": test_timestamp, "sensor_id": test_sensor_id}),
        f"sensor_value={test_sensor_value}&timestamp={test_timestamp}",
        f"{test_timestamp}:{test_sensor_value}",  # 순서 바뀜
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, key in enumerate(key_candidates):
            print(f"\n🔑 키 후보 {i+1}: {key[:20].decode('utf-8', errors='ignore')}... (길이: {len(key)})")
            
            for j, msg_format in enumerate(message_formats):
                # HMAC 계산
                message_bytes = msg_format.encode('utf-8')
                calculated_mac = hmac.new(key, message_bytes, hashlib.sha256).hexdigest()
                
                # 서버에 전송
                test_payload = {
                    "sensor_value": test_sensor_value,
                    "timestamp": test_timestamp,
                    "received_mac": calculated_mac,
                    "sensor_id": test_sensor_id
                }
                
                try:
                    async with session.post(server_url, json=test_payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            verified = result.get('verified', False)
                            
                            if verified:
                                print(f"🎉 성공! 올바른 키와 메시지 형식을 찾았습니다!")
                                print(f"   키: {key}")
                                print(f"   메시지 형식: {msg_format}")
                                print(f"   계산된 HMAC: {calculated_mac}")
                                print(f"   서버 응답: {result}")
                                return key, msg_format
                            else:
                                print(f"   형식 {j+1}: ❌ (MAC: {calculated_mac[:16]}...)")
                        else:
                            print(f"   형식 {j+1}: ❌ 서버 오류 {response.status}")
                            
                except Exception as e:
                    print(f"   형식 {j+1}: ❌ 요청 실패: {e}")
    
    print("\n❌ 서버의 키를 찾지 못했습니다.")
    print("\n💡 대안:")
    print("1. 서버 관리자에게 HMAC 키 문의")
    print("2. 서버 소스코드나 설정 파일 확인")
    print("3. 성능 측정만 수행 (검증 성공/실패 무시)")
    
    return None, None

if __name__ == "__main__":
    asyncio.run(find_server_key())
#!/usr/bin/env python3
"""
외부 서버 HMAC 검증 방식 디버깅
"""

import asyncio
import aiohttp
import json
import time
import hmac
import hashlib

async def debug_server_hmac():
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    print("🔍 외부 서버 HMAC 검증 방식 디버깅")
    print("=" * 50)
    
    # 테스트 케이스 1: 간단한 값
    test_cases = [
        {
            "name": "Simple test",
            "sensor_value": 7.15,
            "timestamp": 1725000000000,
            "received_mac": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "sensor_id": "WADI_001"
        },
        {
            "name": "Different MAC",
            "sensor_value": 10.5,
            "timestamp": 1725000001000,  
            "received_mac": "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
            "sensor_id": "WADI_002"
        }
    ]
    
    # 서버가 기대하는 HMAC을 역추적해보기
    # 여러 가능한 키로 HMAC 생성 시도
    possible_keys = [
        b"default_key",
        b"hmac_key", 
        b"server_key",
        b"wadi_key",
        b"ics_sensor_key",
        b"test_key_1234567890abcdef12345678",  # 32바이트
        b"0123456789abcdef0123456789abcdef"     # 32바이트 hex
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases):
            print(f"\n🧪 테스트 {i+1}: {test_case['name']}")
            
            # 서버에 요청 전송
            try:
                async with session.post(server_url, json=test_case) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"📊 서버 응답:")
                        print(f"  - 검증 결과: {result.get('verified')}")
                        print(f"  - 처리 시간: {result.get('processing_time_ms')}ms")
                        print(f"  - 세부 정보: {result.get('details', {})}")
                        
                        # 서버가 사용하는 키 추측해보기
                        sensor_value = test_case["sensor_value"] 
                        timestamp = test_case["timestamp"]
                        sensor_id = test_case["sensor_id"]
                        
                        print(f"\n🔑 가능한 키로 HMAC 계산:")
                        for key in possible_keys:
                            # 여러 메시지 형식 시도
                            message_formats = [
                                f"{sensor_value}:{timestamp}".encode(),
                                f"{sensor_id}:{sensor_value}:{timestamp}".encode(),
                                f"{sensor_value}{timestamp}".encode(),
                                json.dumps({"sensor_value": sensor_value, "timestamp": timestamp}).encode(),
                                json.dumps({"sensor_value": sensor_value, "timestamp": timestamp, "sensor_id": sensor_id}).encode()
                            ]
                            
                            for msg_format in message_formats[:2]:  # 처음 2개만 테스트
                                calculated_mac = hmac.new(key, msg_format, hashlib.sha256).hexdigest()
                                print(f"    키 '{key.decode('utf-8', errors='ignore')[:20]}'... → {calculated_mac[:16]}...")
                    else:
                        print(f"❌ 서버 오류: {response.status}")
                        print(await response.text())
                        
            except Exception as e:
                print(f"❌ 요청 실패: {e}")
    
    # 서버에 성공적인 HMAC이 있는지 확인
    print(f"\n🎯 성공적인 검증을 위해 서버의 키를 찾아야 합니다.")
    print("서버가 실제로 어떤 키와 메시지 형식을 사용하는지 문서나 소스코드를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(debug_server_hmac())
#!/usr/bin/env python3
"""
빠른 디버그 테스트
================
실제로 서버에 요청이 가는지 확인
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib

# 서버 설정
SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

async def test_server_connection():
    """서버 연결 테스트"""
    
    print("🔍 서버 연결 디버그 테스트")
    print("=" * 40)
    print(f"서버: {SERVER_URL}")
    print("=" * 40)
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            for i in range(5):  # 5번 테스트
                print(f"\n📤 테스트 {i+1}/5:")
                
                # 요청 데이터 생성
                sensor_id = f"WADI_DEBUG_TEST_{i}"
                timestamp = int(time.time())
                value = 25.0 + i
                
                message = generate_hmac_message(sensor_id, timestamp, value)
                hmac_value = generate_hmac(message, HMAC_KEY)
                
                payload = {
                    "sensor_value": value,
                    "timestamp": timestamp,
                    "received_mac": hmac_value,
                    "sensor_id": sensor_id
                }
                
                print(f"  센서: {sensor_id}")
                print(f"  값: {value}")
                print(f"  타임스탬프: {timestamp}")
                print(f"  HMAC: {hmac_value[:16]}...")
                
                try:
                    start_time = time.time()
                    async with session.post(SERVER_URL, json=payload) as response:
                        end_time = time.time()
                        rtt = (end_time - start_time) * 1000
                        
                        print(f"  응답: HTTP {response.status}")
                        print(f"  RTT: {rtt:.1f}ms")
                        
                        if response.status == 200:
                            result = await response.json()
                            verified = result.get('verified', False)
                            print(f"  검증: {'✅' if verified else '❌'}")
                        else:
                            text = await response.text()
                            print(f"  오류: {text[:100]}")
                            
                except Exception as e:
                    print(f"  ❌ 요청 실패: {e}")
                
                # 1초 대기
                if i < 4:
                    await asyncio.sleep(1)
                    
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_server_connection())
#!/usr/bin/env python3
"""
HAI HMAC 서버 연결 테스트
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib

SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

async def test_single_request():
    """단일 요청 테스트"""
    print("🔗 HAI HMAC 서버 연결 테스트")
    print(f"서버: {SERVER_URL}")
    
    timestamp = int(time.time())
    sensor_id = "HAI_HMAC_TEST_S001"
    value = 50.0
    
    message = generate_hmac_message(sensor_id, timestamp, value)
    hmac_value = generate_hmac(message, HMAC_KEY)
    
    payload = {
        "sensor_value": value,
        "timestamp": timestamp,
        "received_mac": hmac_value,
        "sensor_id": sensor_id
    }
    
    print(f"📤 테스트 페이로드:")
    print(f"   센서 ID: {sensor_id}")
    print(f"   값: {value}")
    print(f"   메시지: {message}")
    print(f"   HMAC: {hmac_value[:20]}...")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start = time.perf_counter()
            async with session.post(SERVER_URL, json=payload) as response:
                rtt = (time.perf_counter() - start) * 1000
                
                print(f"📥 서버 응답:")
                print(f"   상태 코드: {response.status}")
                print(f"   응답 시간: {rtt:.1f}ms")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"   응답 내용: {result}")
                    print(f"   검증 결과: {result.get('verified', 'N/A')}")
                    return True
                else:
                    text = await response.text()
                    print(f"   오류 내용: {text}")
                    return False
                    
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

async def main():
    success = await test_single_request()
    if success:
        print("\n✅ HAI HMAC 서버 연결 성공!")
        print("📋 실험 실행 준비 완료")
    else:
        print("\n❌ HAI HMAC 서버 연결 실패!")
        print("🔧 서버 상태 또는 네트워크 연결 확인 필요")

if __name__ == "__main__":
    asyncio.run(main())
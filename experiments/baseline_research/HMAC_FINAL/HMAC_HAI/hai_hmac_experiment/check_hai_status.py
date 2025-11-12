#!/usr/bin/env python3
"""
HAI 실험 상태 확인
"""

import asyncio
import aiohttp
import hmac
import hashlib
import time

SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

async def test_hai_request():
    """HAI 요청 1개 테스트"""
    print("🔄 HAI 실험 상태 확인 중...")
    
    timestamp = int(time.time())
    sensor_id = "HAI_STATUS_CHECK"
    value = 75.0
    
    message = generate_hmac_message(sensor_id, timestamp, value)
    hmac_value = generate_hmac(message, HMAC_KEY)
    
    payload = {
        "sensor_value": value,
        "timestamp": timestamp,
        "received_mac": hmac_value,
        "sensor_id": sensor_id
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start = time.perf_counter()
            async with session.post(SERVER_URL, json=payload) as response:
                rtt = (time.perf_counter() - start) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 서버 정상 응답: {rtt:.1f}ms")
                    print(f"   검증 결과: {result.get('verified')}")
                    return True
                else:
                    print(f"❌ 서버 오류: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_hai_request())
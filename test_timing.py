#!/usr/bin/env python3
"""
타이밍 테스트
"""

import asyncio
import time
import aiohttp
from datetime import datetime


async def send_test_request(sensor_id: str, value: float):
    """테스트 요청 전송"""
    payload = {
        "algorithm": "ed25519",
        "sensor_id": sensor_id,
        "sensor_value": value,
        "signature": "test_signature",
        "public_key": "test_public_key", 
        "timestamp": int(time.time())
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://192.168.0.11:8085/api/v1/verify/ed25519",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                print(f"📤 {datetime.now().strftime('%H:%M:%S.%f')[:-3]} - {sensor_id}: {value}")
                return response.status == 200
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
        return False


async def test_regular_timing():
    """정확한 타이밍 테스트"""
    print("🕐 정확한 1Hz 타이밍 테스트 (10초간)")
    
    frequency = 1  # 1Hz
    interval = 1.0 / frequency
    target_requests = 10
    next_send_time = time.time()
    
    for i in range(target_requests):
        # 정확한 타이밍을 위해 다음 전송 시간까지 대기
        current_time = time.time()
        if current_time < next_send_time:
            await asyncio.sleep(next_send_time - current_time)
        
        # Fire-and-forget 전송
        asyncio.create_task(send_test_request("TEST_SENSOR", i * 0.1))
        
        # 다음 전송 시간 설정
        next_send_time = next_send_time + interval
    
    print("✅ 테스트 완료")


if __name__ == "__main__":
    asyncio.run(test_regular_timing())

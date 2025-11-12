#!/usr/bin/env python3
"""
직접적인 타이밍 테스트 - 서버에 정확한 간격으로 요청 전송
"""

import asyncio
import time
import aiohttp
from datetime import datetime


async def send_precise_requests():
    """정확한 0.5초 간격으로 10개 요청 전송"""
    print("🕐 직접적인 0.5초 간격(2Hz) 테스트 시작")
    
    frequency = 2  # 2Hz (0.5초 간격)
    interval = 1.0 / frequency
    target_requests = 10
    
    start_time = time.perf_counter()
    
    for i in range(target_requests):
        # 정확한 전송 시점 계산
        target_time = start_time + (i * interval)
        current_time = time.perf_counter()
        
        # 다음 전송 시간까지 대기
        sleep_time = target_time - current_time
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        
        # 현재 시간 기록
        send_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # 서버에 요청 전송 (Fire-and-forget)
        asyncio.create_task(send_single_request(f"TEST_SENSOR", i, send_time))
        
        print(f"📤 {send_time} - 요청 #{i+1} 전송")
    
    print("✅ 모든 요청 전송 완료")
    # 마지막 요청이 처리될 시간을 기다림
    await asyncio.sleep(2)


async def send_single_request(sensor_id: str, request_id: int, send_time: str):
    """단일 요청 전송"""
    payload = {
        "algorithm": "ed25519",
        "sensor_id": sensor_id,
        "sensor_value": float(request_id * 0.1),
        "signature": f"test_signature_{request_id}",
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
                status = "✅" if response.status == 200 else "❌"
                print(f"   {status} {send_time} - {sensor_id} 응답: {response.status}")
    except Exception as e:
        print(f"   ❌ {send_time} - {sensor_id} 오류: {e}")


if __name__ == "__main__":
    asyncio.run(send_precise_requests())
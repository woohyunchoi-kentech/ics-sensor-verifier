#!/usr/bin/env python3
"""
직접 테스트 - 최소한의 코드로 바로 확인
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

async def main():
    print("🚀 직접 테스트 시작 - 10개 요청을 1초 간격으로")
    
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        for i in range(10):
            print(f"📤 요청 {i+1}/10...")
            
            # 요청 데이터
            sensor_id = f"WADI_DIRECT_TEST_{i}"
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
            
            try:
                start = time.time()
                async with session.post(SERVER_URL, json=payload) as response:
                    rtt = (time.time() - start) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        verified = result.get('verified', False)
                        print(f"   ✅ 성공 - RTT: {rtt:.1f}ms, 검증: {'✅' if verified else '❌'}")
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        
            except Exception as e:
                print(f"   ❌ 오류: {e}")
            
            # 1초 대기
            if i < 9:
                print("   ⏱️  1초 대기...")
                await asyncio.sleep(1)
    
    print("🏁 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
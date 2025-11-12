#!/usr/bin/env python3
"""
즉시 실행 테스트 - 대기 시간 없이 바로 전송
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

async def send_request(session, sensor_id, value):
    timestamp = int(time.time())
    message = generate_hmac_message(sensor_id, timestamp, value)
    hmac_value = generate_hmac(message, HMAC_KEY)
    
    payload = {
        "sensor_value": value,
        "timestamp": timestamp,
        "received_mac": hmac_value,
        "sensor_id": sensor_id
    }
    
    try:
        start = time.perf_counter()
        async with session.post(SERVER_URL, json=payload) as response:
            rtt = (time.perf_counter() - start) * 1000
            
            if response.status == 200:
                result = await response.json()
                return {"success": True, "verified": result.get('verified', False), "rtt": rtt}
            else:
                return {"success": False, "verified": False, "error": f"HTTP {response.status}"}
    except Exception as e:
        return {"success": False, "verified": False, "error": str(e)}

async def main():
    print("🔥 즉시 실행 테스트 - 대기 없이 100개 요청 연속 전송")
    
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        print("📤 전송 시작...")
        start_time = time.time()
        
        # 100개 요청을 즉시 병렬 전송
        tasks = []
        for i in range(100):
            sensor_id = f"WADI_IMMEDIATE_{i:03d}"
            value = 25.0 + (i * 0.1)
            task = asyncio.create_task(send_request(session, sensor_id, value))
            tasks.append(task)
        
        print(f"⚡ {len(tasks)}개 요청 병렬 전송 중...")
        
        # 모든 요청 완료 대기
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        successful = sum(1 for r in results if r["success"])
        verified = sum(1 for r in results if r["verified"])
        
        print(f"\\n📊 즉시 실행 결과:")
        print(f"   총 요청: {len(results)}개")
        print(f"   성공: {successful}개 ({successful/len(results)*100:.1f}%)")
        print(f"   검증: {verified}개 ({verified/len(results)*100:.1f}%)")
        print(f"   소요 시간: {duration:.2f}초")
        print(f"   RPS: {len(results)/duration:.1f}")
        
        if successful > 0:
            avg_rtt = sum(r["rtt"] for r in results if r["success"]) / successful
            print(f"   평균 RTT: {avg_rtt:.1f}ms")
        
        # 실패한 요청 정보
        failed = [r for r in results if not r["success"]]
        if failed:
            print(f"\\n❌ 실패한 요청 {len(failed)}개:")
            for i, fail in enumerate(failed[:5]):  # 처음 5개만 표시
                print(f"   {i+1}. {fail.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
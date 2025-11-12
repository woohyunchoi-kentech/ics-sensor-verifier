#!/usr/bin/env python3
"""
HAI HMAC 빠른 테스트 - 1개 조건만
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
                return {"success": False, "verified": False, "rtt": rtt}
    except Exception as e:
        return {"success": False, "verified": False, "rtt": 0, "error": str(e)}

async def main():
    """HAI HMAC 빠른 테스트 - 10센서 10Hz 10개 요청"""
    
    print("🌊 HAI HMAC 빠른 테스트")
    print("📊 조건: 10센서 × 10Hz × 10개 요청")
    
    sensor_count = 10
    frequency = 10
    max_requests = 10
    
    interval = 1.0 / frequency
    print(f"📤 전송 간격: {interval:.3f}초")
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        results = []
        request_count = 0
        transmission_id = 0
        
        start_time = time.time()
        print(f"📤 전송 시작...")
        
        while request_count < max_requests:
            # 전송 시간 계산
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            # 타이밍 조절
            wait_time = target_time - current_time
            if wait_time > 0.001:
                await asyncio.sleep(min(wait_time, 0.1))
                continue
            
            # HAI 센서들 전송
            tasks = []
            sensors = [f"HAI_TEST_S{i:03d}" for i in range(sensor_count)]
            
            for sensor in sensors:
                if request_count >= max_requests:
                    break
                value = 50.0 + (request_count * 0.1)
                task = asyncio.create_task(send_request(session, sensor, value))
                tasks.append(task)
                request_count += 1
            
            # 병렬 전송
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, dict):
                        results.append(result)
                    else:
                        results.append({"success": False, "verified": False, "rtt": 0, "error": str(result)})
            
            transmission_id += 1
            print(f"⏱️  전송 {transmission_id}: {request_count}/{max_requests}개 완료")
        
        # 결과 분석
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r.get("success", False))
        verified = sum(1 for r in results if r.get("verified", False))
        
        print(f"\n✅ HAI 빠른 테스트 결과:")
        print(f"   총 요청: {len(results)}개")
        print(f"   성공: {successful}개 ({successful/len(results)*100:.1f}%)")
        print(f"   검증: {verified}개 ({verified/len(results)*100:.1f}%)")
        print(f"   소요 시간: {total_duration:.1f}초")
        
        if successful > 0:
            avg_rtt = sum(r["rtt"] for r in results if r["success"]) / successful
            print(f"   평균 RTT: {avg_rtt:.1f}ms")
        
        # 실패한 요청이 있으면 출력
        failed = [r for r in results if not r["success"]]
        if failed:
            print(f"\n❌ 실패한 요청 {len(failed)}개:")
            for i, fail in enumerate(failed[:3]):
                print(f"   {i+1}. {fail.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
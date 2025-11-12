#!/usr/bin/env python3
"""
서버 전송 타이밍 테스트
=====================
실제 서버로 요청을 보내서 타이밍 확인
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib
from datetime import datetime

# 서버 설정
SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    """HMAC 메시지 생성"""
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    """HMAC 생성"""
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

async def send_test_request(session: aiohttp.ClientSession, sensor_id: str, value: float) -> dict:
    """테스트 요청 전송"""
    
    timestamp = int(time.time())
    message = generate_hmac_message(sensor_id, timestamp, value)
    hmac_value = generate_hmac(message, HMAC_KEY)
    
    payload = {
        "sensor_id": sensor_id,
        "timestamp": timestamp,
        "sensor_value": value,
        "hmac": hmac_value
    }
    
    try:
        start_time = time.time()
        async with session.post(SERVER_URL, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
            response_time = time.time()
            
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "send_time": start_time,
                    "response_time": response_time,
                    "rtt": (response_time - start_time) * 1000,
                    "verified": result.get("verified", False)
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "send_time": start_time,
                    "response_time": response_time
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "send_time": time.time(),
            "response_time": time.time()
        }

async def test_server_timing():
    """서버 전송 타이밍 테스트"""
    
    print("🌐 서버 전송 타이밍 테스트")
    print("=" * 50)
    print(f"서버: {SERVER_URL}")
    print("조건: 1Hz, 10초 (10번 전송)")
    print("=" * 50)
    
    frequency = 1  # 1Hz
    duration = 10  # 10초
    interval = 1.0 / frequency  # 1초 간격
    total_transmissions = frequency * duration  # 10번
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        results = []
        
        for transmission_id in range(total_transmissions):
            # 정확한 전송 시간 계산
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            # 대기
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            # 실제 전송
            sensor_id = f"WADI_TEST_SENSOR_"
            value = 0.5 + (transmission_id * 0.01)  # 테스트 값
            
            result = await send_test_request(session, sensor_id, value)
            results.append(result)
            
            # 진행 상황 출력
            actual_time = result["send_time"]
            elapsed = actual_time - start_time
            expected_elapsed = transmission_id * interval
            
            status = "✅" if result["success"] else "❌"
            verified = "✅" if result.get("verified", False) else "❌"
            rtt = result.get("rtt", 0)
            
            print(f"전송 {transmission_id + 1:2d}: {elapsed:.3f}초 (예상: {expected_elapsed:.3f}초) {status} 검증:{verified} RTT:{rtt:.1f}ms")
    
    print(f"\\n📊 결과 분석:")
    
    # 성공률
    successful = sum(1 for r in results if r["success"])
    verified = sum(1 for r in results if r.get("verified", False))
    
    print(f"성공률: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"검증률: {verified}/{len(results)} ({verified/len(results)*100:.1f}%)")
    
    # 타이밍 분석
    send_times = [r["send_time"] for r in results if r["success"]]
    if len(send_times) >= 2:
        intervals = []
        for i in range(1, len(send_times)):
            interval_actual = send_times[i] - send_times[i-1]
            intervals.append(interval_actual)
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            max_deviation = max(abs(inv - interval) for inv in intervals)
            
            print(f"평균 전송 간격: {avg_interval:.3f}초 (예상: {interval:.3f}초)")
            print(f"최대 편차: {max_deviation:.3f}초")
            print(f"타이밍 정확도: {'✅' if max_deviation < 0.1 else '❌'}")
    
    # RTT 분석
    rtts = [r["rtt"] for r in results if r["success"] and "rtt" in r]
    if rtts:
        avg_rtt = sum(rtts) / len(rtts)
        print(f"평균 RTT: {avg_rtt:.1f}ms")

if __name__ == "__main__":
    asyncio.run(test_server_timing())
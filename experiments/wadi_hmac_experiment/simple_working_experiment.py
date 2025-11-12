#!/usr/bin/env python3
"""
간단한 작동하는 WADI HMAC 실험
==============================
복잡한 로직 없이 확실히 작동하는 실험
"""

import asyncio
import time
import json
import hmac
import hashlib
import aiohttp
from datetime import datetime
from pathlib import Path

# 서버 설정
SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

async def send_request(session, sensor_id, value):
    """단일 요청 전송"""
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
        start_time = time.perf_counter()
        async with session.post(SERVER_URL, json=payload) as response:
            end_time = time.perf_counter()
            rtt = (end_time - start_time) * 1000
            
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "verified": result.get('verified', False),
                    "rtt_ms": rtt,
                    "timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "verified": False,
                    "rtt_ms": rtt,
                    "error": f"HTTP {response.status}",
                    "timestamp": time.time()
                }
    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "rtt_ms": 0,
            "error": str(e),
            "timestamp": time.time()
        }

async def run_simple_experiment(sensor_count, frequency, total_requests):
    """간단한 실험 실행"""
    
    print(f"\\n🚀 실험: {sensor_count}센서, {frequency}Hz, {total_requests}개 요청")
    
    # 센서 목록 생성
    sensors = [f"WADI_SENSOR_{i:03d}" for i in range(sensor_count)]
    
    # HTTP 세션 생성
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        results = []
        start_time = time.time()
        interval = 1.0 / frequency
        
        request_count = 0
        transmission_count = 0
        
        print(f"📊 전송 간격: {interval:.3f}초")
        print(f"📤 전송 시작...")
        
        while request_count < total_requests:
            # 전송 시간 계산
            target_time = start_time + (transmission_count * interval)
            current_time = time.time()
            
            # 대기
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            # 이 전송에서 모든 센서 전송
            tasks = []
            for sensor in sensors:
                if request_count >= total_requests:
                    break
                    
                value = 25.0 + (request_count * 0.01)
                task = asyncio.create_task(send_request(session, sensor, value))
                tasks.append(task)
                request_count += 1
            
            # 병렬 전송
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            transmission_count += 1
            
            # 진행 상황 (10% 간격)
            if request_count % max(1, total_requests // 10) == 0:
                progress = (request_count / total_requests) * 100
                elapsed = time.time() - start_time
                print(f"⏱️  {elapsed:.1f}초: {request_count:,}/{total_requests:,} ({progress:.0f}%)")
    
    # 결과 분석
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    verified = sum(1 for r in results if r["verified"])
    
    if successful > 0:
        avg_rtt = sum(r["rtt_ms"] for r in results if r["success"]) / successful
    else:
        avg_rtt = 0
    
    duration = time.time() - start_time
    actual_rps = total / duration if duration > 0 else 0
    
    print(f"\\n📊 결과:")
    print(f"   총 요청: {total:,}개")
    print(f"   성공: {successful:,}개 ({successful/max(1,total)*100:.1f}%)")
    print(f"   검증: {verified:,}개 ({verified/max(1,total)*100:.1f}%)")
    print(f"   소요 시간: {duration:.1f}초")
    print(f"   실제 RPS: {actual_rps:.1f}")
    print(f"   평균 RTT: {avg_rtt:.1f}ms")
    
    return {
        "sensor_count": sensor_count,
        "frequency": frequency,
        "total_requests": total,
        "successful_requests": successful,
        "verified_requests": verified,
        "duration_seconds": duration,
        "avg_rtt_ms": avg_rtt,
        "actual_rps": actual_rps
    }

async def main():
    """메인 실험"""
    
    print("🌊 간단한 WADI HMAC 실험")
    print("=" * 50)
    
    # 테스트 조건들 (빠른 버전)
    test_conditions = [
        (1, 1, 100),    # 1센서, 1Hz, 100개 → 100초
        (1, 10, 100),   # 1센서, 10Hz, 100개 → 10초
        (10, 1, 100),   # 10센서, 1Hz, 100개 → 10초
        (10, 10, 100),  # 10센서, 10Hz, 100개 → 1초
        (1, 1, 1000),   # 1센서, 1Hz, 1000개 → 1000초 (원래 계획)
    ]
    
    results = []
    
    for sensor_count, frequency, total_requests in test_conditions:
        try:
            result = await run_simple_experiment(sensor_count, frequency, total_requests)
            results.append(result)
            
            print(f"✅ 조건 완료")
            await asyncio.sleep(2)  # 조건 간 휴식
            
        except KeyboardInterrupt:
            print("\\n⏹️ 실험 중단됨")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")
            continue
    
    # 최종 요약
    print(f"\\n{'='*50}")
    print("🏁 실험 완료")
    print(f"{'='*50}")
    
    for i, result in enumerate(results):
        condition = test_conditions[i]
        print(f"{i+1}. {condition[0]}센서 × {condition[1]}Hz × {condition[2]}개: "
              f"성공률 {result['successful_requests']/max(1,result['total_requests'])*100:.1f}%, "
              f"검증률 {result['verified_requests']/max(1,result['total_requests'])*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
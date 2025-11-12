#!/usr/bin/env python3
"""
최종 타이밍 실험 - 확실히 작동하는 로직
=======================================
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib
import csv
from datetime import datetime
from pathlib import Path

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

async def run_timed_condition(sensor_count, frequency, max_requests):
    """타이밍 조건 실행"""
    
    print(f"\\n🚀 실험: {sensor_count}센서 × {frequency}Hz × {max_requests}개")
    
    interval = 1.0 / frequency
    print(f"📊 전송 간격: {interval:.3f}초")
    
    timeout = aiohttp.ClientTimeout(total=5)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        results = []
        request_count = 0
        transmission_id = 0
        
        start_time = time.time()
        print(f"📤 전송 시작 ({start_time:.1f})")
        
        while request_count < max_requests:
            # 이번 전송 시간
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            # 시간이 됐으면 전송, 아니면 짧게 대기
            wait_time = target_time - current_time
            if wait_time > 0:
                if wait_time > 0.001:  # 1ms 이상이면 대기
                    await asyncio.sleep(min(wait_time, 0.1))  # 최대 0.1초만 대기
                    continue  # 다시 체크
            
            # 전송 실행
            tasks = []
            sensors = [f"WADI_S{i:03d}" for i in range(sensor_count)]
            
            for sensor in sensors:
                if request_count >= max_requests:
                    break
                value = 25.0 + (request_count * 0.001)
                task = asyncio.create_task(send_request(session, sensor, value))
                tasks.append(task)
                request_count += 1
            
            # 병렬 전송
            if tasks:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
            
            transmission_id += 1
            
            # 진행 상황 (매 20%)
            if request_count % max(1, max_requests // 5) == 0:
                elapsed = time.time() - start_time
                progress = (request_count / max_requests) * 100
                print(f"⏱️  {elapsed:.1f}초: {request_count}/{max_requests} ({progress:.0f}%)")
        
        # 완료
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r["success"])
        verified = sum(1 for r in results if r["verified"])
        
        result = {
            "sensor_count": sensor_count,
            "frequency": frequency,
            "total_requests": len(results),
            "successful_requests": successful,
            "verified_requests": verified,
            "duration_seconds": total_duration,
            "success_rate": (successful / max(1, len(results))) * 100,
            "verification_rate": (verified / max(1, len(results))) * 100
        }
        
        if successful > 0:
            result["avg_rtt_ms"] = sum(r["rtt"] for r in results if r["success"]) / successful
        else:
            result["avg_rtt_ms"] = 0
        
        print(f"✅ 완료: {successful}/{len(results)} 성공 ({result['success_rate']:.1f}%), "
              f"{verified} 검증 ({result['verification_rate']:.1f}%), "
              f"{total_duration:.1f}초")
        
        return result

async def main():
    print("🌊 최종 타이밍 WADI HMAC 실험")
    print("=" * 50)
    
    # 빠른 테스트 조건들
    conditions = [
        (1, 1, 20),      # 1센서, 1Hz, 20개 → 20초
        (1, 10, 20),     # 1센서, 10Hz, 20개 → 2초
        (10, 1, 20),     # 10센서, 1Hz, 20개 → 2초  
        (10, 10, 100),   # 10센서, 10Hz, 100개 → 1초
        (50, 10, 500),   # 50센서, 10Hz, 500개 → 1초
        (100, 10, 1000), # 100센서, 10Hz, 1000개 → 1초
    ]
    
    results = []
    
    print(f"🚀 {len(conditions)}개 조건 실험")
    
    for i, (sensor_count, frequency, max_requests) in enumerate(conditions, 1):
        print(f"\\n{'='*40}")
        print(f"📍 조건 {i}/{len(conditions)}")
        print(f"{'='*40}")
        
        try:
            result = await run_timed_condition(sensor_count, frequency, max_requests)
            results.append(result)
            
            # 조건 간 잠깐 휴식
            if i < len(conditions):
                print("⏸️  2초 휴식...")
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print("\\n⏹️ 중단됨")
            break
        except Exception as e:
            print(f"❌ 오류: {e}")
            continue
    
    # 결과 저장
    if results:
        results_dir = Path("../results/final_timed_experiment")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = results_dir / f"timed_results_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\\n💾 결과 저장: {csv_path}")
        
        # 요약
        print(f"\\n📊 실험 요약:")
        total_requests = sum(r["total_requests"] for r in results)
        total_verified = sum(r["verified_requests"] for r in results)
        
        print(f"   완료 조건: {len(results)}/{len(conditions)}개")
        print(f"   총 요청: {total_requests:,}개")
        print(f"   전체 검증률: {total_verified/max(1,total_requests)*100:.1f}%")
        
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['sensor_count']}센서×{result['frequency']}Hz: "
                  f"{result['verification_rate']:.1f}% 검증률")

if __name__ == "__main__":
    asyncio.run(main())
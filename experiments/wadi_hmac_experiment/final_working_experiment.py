#!/usr/bin/env python3
"""
최종 작동하는 WADI HMAC 실험
===========================
검증된 로직으로 16개 조건 실험
"""

import asyncio
import time
import json
import hmac
import hashlib
import aiohttp
import csv
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
                    "rtt_ms": rtt
                }
            else:
                return {
                    "success": False,
                    "verified": False,
                    "rtt_ms": rtt,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "rtt_ms": 0,
            "error": str(e)
        }

async def run_condition(sensor_count, frequency, max_requests):
    """단일 조건 실행"""
    
    print(f"\\n🚀 실험: {sensor_count}센서 × {frequency}Hz × {max_requests}개 요청")
    
    # 센서 목록
    sensors = [f"WADI_SENSOR_{i:03d}" for i in range(sensor_count)]
    
    # 타이밍 계산
    interval = 1.0 / frequency
    print(f"📊 전송 간격: {interval:.3f}초")
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        results = []
        start_time = time.time()
        request_count = 0
        transmission_count = 0
        
        print(f"📤 전송 시작...")
        
        while request_count < max_requests:
            # 전송 시간 맞추기
            target_time = start_time + (transmission_count * interval)
            current_time = time.time()
            
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            # 이 시점에서 모든 센서 데이터 전송
            tasks = []
            for sensor in sensors:
                if request_count >= max_requests:
                    break
                    
                value = 25.0 + (request_count * 0.001)  # 값 변화
                task = asyncio.create_task(send_request(session, sensor, value))
                tasks.append(task)
                request_count += 1
            
            # 병렬 전송 및 결과 수집
            if tasks:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
            
            transmission_count += 1
            
            # 진행 상황 (20% 간격)
            if request_count % max(1, max_requests // 5) == 0:
                progress = (request_count / max_requests) * 100
                elapsed = time.time() - start_time
                print(f"⏱️  {elapsed:.1f}초: {request_count:,}/{max_requests:,} ({progress:.0f}%)")
    
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
    
    result = {
        "sensor_count": sensor_count,
        "frequency": frequency,
        "total_requests": total,
        "successful_requests": successful,
        "verified_requests": verified,
        "success_rate": (successful / max(1, total)) * 100,
        "verification_rate": (verified / max(1, total)) * 100,
        "duration_seconds": duration,
        "avg_rtt_ms": avg_rtt,
        "actual_rps": actual_rps
    }
    
    print(f"📊 결과:")
    print(f"   성공: {successful:,}/{total:,} ({result['success_rate']:.1f}%)")
    print(f"   검증: {verified:,}/{total:,} ({result['verification_rate']:.1f}%)")
    print(f"   시간: {duration:.1f}초")
    print(f"   RTT: {avg_rtt:.1f}ms")
    print(f"   RPS: {actual_rps:.1f}")
    
    return result

async def main():
    """메인 실험"""
    
    print("🌊 최종 WADI HMAC 실험")
    print("=" * 50)
    
    # 실험 조건 (합리적인 크기로)
    conditions = [
        # Phase 1: 기본 조건
        (1, 1, 100),     # 1센서, 1Hz, 100개 → 100초
        (1, 2, 200),     # 1센서, 2Hz, 200개 → 100초  
        (1, 10, 100),    # 1센서, 10Hz, 100개 → 10초
        (1, 100, 100),   # 1센서, 100Hz, 100개 → 1초
        
        # Phase 2: 다중 센서
        (10, 1, 100),    # 10센서, 1Hz, 100개 → 10초
        (10, 2, 200),    # 10센서, 2Hz, 200개 → 10초
        (10, 10, 1000),  # 10센서, 10Hz, 1000개 → 10초
        (10, 100, 1000), # 10센서, 100Hz, 1000개 → 1초
        
        # Phase 3: 대규모
        (50, 1, 500),    # 50센서, 1Hz, 500개 → 10초
        (50, 2, 1000),   # 50센서, 2Hz, 1000개 → 10초
        (50, 10, 5000),  # 50센서, 10Hz, 5000개 → 10초
        (50, 100, 5000), # 50센서, 100Hz, 5000개 → 1초
        
        # Phase 4: 최대 규모
        (100, 1, 1000),  # 100센서, 1Hz, 1000개 → 10초
        (100, 2, 2000),  # 100센서, 2Hz, 2000개 → 10초
        (100, 10, 10000),# 100센서, 10Hz, 10000개 → 10초
        (100, 100, 10000)# 100센서, 100Hz, 10000개 → 1초
    ]
    
    results = []
    
    print(f"🚀 총 {len(conditions)}개 조건 실험 시작")
    
    for i, (sensor_count, frequency, max_requests) in enumerate(conditions, 1):
        print(f"\\n{'='*60}")
        print(f"📍 조건 {i}/{len(conditions)}")
        print(f"{'='*60}")
        
        try:
            result = await run_condition(sensor_count, frequency, max_requests)
            results.append(result)
            
            # 중간 저장
            if i % 4 == 0:  # 4개마다 저장
                save_results(results, f"progress_{i:02d}")
            
            print(f"✅ 조건 {i} 완료")
            
            # 조건 간 휴식
            if i < len(conditions):
                await asyncio.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\\n⏹️ 실험 중단됨 (완료: {i-1}/{len(conditions)})")
            break
        except Exception as e:
            print(f"❌ 조건 {i} 실패: {e}")
            continue
    
    # 최종 결과 저장
    save_results(results, "final")
    print_summary(results)
    
    print(f"\\n🎉 실험 완료!")

def save_results(results, suffix):
    """결과 저장"""
    if not results:
        return
    
    # 결과 디렉토리 생성
    results_dir = Path("../results/final_wadi_hmac")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV 저장
    csv_path = results_dir / f"wadi_hmac_{suffix}_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print(f"💾 결과 저장: {csv_path}")

def print_summary(results):
    """결과 요약"""
    if not results:
        return
    
    print(f"\\n{'='*60}")
    print("🏁 실험 완료 요약")
    print(f"{'='*60}")
    
    total_requests = sum(r["total_requests"] for r in results)
    total_successful = sum(r["successful_requests"] for r in results)
    total_verified = sum(r["verified_requests"] for r in results)
    
    print(f"📊 전체 통계:")
    print(f"   완료 조건: {len(results)}/16개")
    print(f"   총 요청: {total_requests:,}개")
    print(f"   전체 성공률: {total_successful/max(1,total_requests)*100:.1f}%")
    print(f"   전체 검증률: {total_verified/max(1,total_requests)*100:.1f}%")
    
    if results:
        avg_rtt = sum(r["avg_rtt_ms"] for r in results if r["successful_requests"] > 0) / max(1, sum(1 for r in results if r["successful_requests"] > 0))
        print(f"   평균 RTT: {avg_rtt:.1f}ms")
    
    print(f"\\n📈 조건별 결과:")
    for i, result in enumerate(results, 1):
        print(f"   {i:2d}. {result['sensor_count']}센서 × {result['frequency']}Hz: "
              f"성공률 {result['success_rate']:.1f}%, "
              f"검증률 {result['verification_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
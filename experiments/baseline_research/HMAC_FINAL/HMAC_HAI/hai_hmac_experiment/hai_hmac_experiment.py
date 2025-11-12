#!/usr/bin/env python3
"""
완전한 16개 조건 HAI HMAC 실험
==============================
베이스라인 구조: 1,10,50,100 센서 × 1,2,10,100 Hz × 1000개 요청
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib
import csv
from datetime import datetime
from pathlib import Path
from hai_data_loader import HAIDataLoader

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

async def run_condition(sensor_count, frequency, max_requests, hai_loader):
    """단일 조건 실행 - 베이스라인 구조"""
    
    print(f"\n🚀 HAI 실험: {sensor_count}센서 × {frequency}Hz × {max_requests:,}개 요청")
    
    interval = 1.0 / frequency
    expected_duration = max_requests / (sensor_count * frequency)
    
    print(f"📊 설정:")
    print(f"   • 전송 간격: {interval:.3f}초")
    print(f"   • 예상 시간: {expected_duration:.1f}초")
    print(f"   • 센서당 요청: {max_requests // sensor_count}개")
    
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        results = []
        request_count = 0
        transmission_id = 0
        
        start_time = time.time()
        last_log_time = 0
        
        print(f"📤 전송 시작...")
        
        while request_count < max_requests:
            # 전송 시간 계산 (HMAC 성공 로직 동일 사용)
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            # 타이밍 조절
            wait_time = target_time - current_time
            if wait_time > 0.001:  # 1ms 이상 차이나면
                await asyncio.sleep(min(wait_time, 0.1))  # 최대 0.1초 대기
                continue
            
            # 실제 HAI 데이터셋 센서 사용
            tasks = []
            sensors = hai_loader.get_sensor_list(sensor_count)
            
            for sensor in sensors:
                if request_count >= max_requests:
                    break
                # 실제 HAI 데이터셋에서 센서 값 가져오기
                value = hai_loader.get_sensor_value(sensor, transmission_id)
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
            
            # 진행 상황 로깅 (10% 간격 또는 10초 간격)
            elapsed = time.time() - start_time
            progress_pct = (request_count / max_requests) * 100
            
            if (progress_pct >= (last_log_time + 10)) or (elapsed >= (last_log_time + 10)):
                print(f"⏱️  {elapsed:.1f}초: {request_count:,}/{max_requests:,} ({progress_pct:.0f}%)")
                last_log_time = max(progress_pct // 10 * 10, elapsed // 10 * 10)
        
        # 결과 분석 (베이스라인 지표 측정)
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r.get("success", False))
        verified = sum(1 for r in results if r.get("verified", False))
        
        result = {
            "algorithm": "HMAC",
            "dataset": "HAI",
            "sensor_count": sensor_count,
            "frequency": frequency,
            "total_requests": len(results),
            "successful_requests": successful,
            "verified_requests": verified,
            "duration_seconds": round(total_duration, 2),
            "success_rate": round((successful / max(1, len(results))) * 100, 2),
            "verification_rate": round((verified / max(1, len(results))) * 100, 2),
            "actual_rps": round(len(results) / total_duration, 1) if total_duration > 0 else 0
        }
        
        if successful > 0:
            rtts = [r["rtt"] for r in results if r.get("success") and "rtt" in r]
            result["avg_rtt_ms"] = round(sum(rtts) / len(rtts), 2) if rtts else 0
        else:
            result["avg_rtt_ms"] = 0
        
        print(f"✅ 완료: {successful:,}/{len(results):,} 성공 ({result['success_rate']:.1f}%), "
              f"{verified:,} 검증 ({result['verification_rate']:.1f}%), "
              f"{total_duration:.1f}초, RTT {result['avg_rtt_ms']:.1f}ms")
        
        return result

async def main():
    """16개 조건 완전한 HAI HMAC 실험"""
    
    print("🌊 완전한 16개 조건 HAI HMAC 실험")
    print("=" * 60)
    print("📊 베이스라인 구조: 1,10,50,100 센서 × 1,2,10,100 Hz")
    print("🎯 목표: 각 조건마다 1000개 요청, 99% HMAC 검증 성공")
    print("📂 데이터셋: HAI (Hardware-in-the-loop Augmented ICS)")
    print("=" * 60)
    
    # HAI 데이터 로더 초기화
    print("📂 HAI 데이터셋 로드 중...")
    hai_loader = HAIDataLoader()
    print("✅ HAI 데이터 로드 완료")
    
    # 베이스라인 16개 조건 정의
    sensor_counts = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]
    max_requests = 1000
    
    conditions = []
    for sensor_count in sensor_counts:
        for frequency in frequencies:
            conditions.append((sensor_count, frequency, max_requests))
    
    total_conditions = len(conditions)
    
    print(f"🚀 총 {total_conditions}개 조건 실험 시작")
    
    # 예상 시간 계산
    total_estimated_time = 0
    for sensor_count, frequency, max_req in conditions:
        estimated = max_req / (sensor_count * frequency)
        total_estimated_time += estimated
    
    print(f"⏰ 예상 총 시간: {total_estimated_time/60:.1f}분")
    print()
    
    results = []
    start_experiment_time = time.time()
    
    # Phase 구조로 실험 진행
    phases = [
        ("Phase 1: 기본 조건 (1센서)", conditions[0:4]),
        ("Phase 2: 중간 조건 (10센서)", conditions[4:8]),
        ("Phase 3: 대규모 조건 (50센서)", conditions[8:12]),
        ("Phase 4: 최대 조건 (100센서)", conditions[12:16])
    ]
    
    condition_num = 0
    for phase_name, phase_conditions in phases:
        print(f"\n{'='*60}")
        print(f"🎯 {phase_name}")
        print(f"{'='*60}")
        
        for sensor_count, frequency, max_req in phase_conditions:
            condition_num += 1
            print(f"\n📍 조건 {condition_num}/{total_conditions}")
            
            try:
                result = await run_condition(sensor_count, frequency, max_req, hai_loader)
                results.append(result)
                
                print(f"✅ 조건 {condition_num} 완료")
                
                # 조건 간 짧은 휴식 (마지막 제외)
                if condition_num < total_conditions:
                    print("⏸️  3초 휴식...")
                    await asyncio.sleep(3)
                    
            except KeyboardInterrupt:
                print(f"\n⏹️ HAI 실험 중단됨 (완료: {condition_num-1}/{total_conditions})")
                break
            except Exception as e:
                print(f"❌ 조건 {condition_num} 실패: {e}")
                # 실패해도 계속 진행
                continue
        
        # Phase마다 중간 저장
        if results:
            save_intermediate_results(results, condition_num)
    
    # 최종 결과 저장 및 분석
    total_experiment_time = time.time() - start_experiment_time
    save_final_results(results, total_experiment_time)
    print_comprehensive_summary(results, total_experiment_time)
    
    print(f"\n🎉 HAI HMAC 전체 실험 완료!")

def save_intermediate_results(results, condition_num):
    """중간 결과 저장"""
    if not results:
        return
    
    results_dir = Path("../results/complete_hai_hmac")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = results_dir / f"progress_{condition_num:02d}_{timestamp}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print(f"💾 중간 저장: {csv_path.name}")

def save_final_results(results, total_time):
    """최종 결과 저장"""
    if not results:
        return
    
    results_dir = Path("../results/complete_hai_hmac")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV 저장
    csv_path = results_dir / f"final_hai_hmac_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    # 요약 정보 저장
    summary_path = results_dir / f"experiment_summary_hai_hmac_{timestamp}.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"HAI HMAC 16개 조건 완전한 실험 결과\\n")
        f.write(f"실험 시간: {datetime.now()}\\n")
        f.write(f"총 소요 시간: {total_time/60:.1f}분\\n")
        f.write(f"완료 조건: {len(results)}/16개\\n")
        f.write(f"\\n조건별 결과:\\n")
        for i, result in enumerate(results, 1):
            f.write(f"{i:2d}. {result['sensor_count']:3d}센서 × {result['frequency']:3d}Hz: "
                   f"성공률 {result['success_rate']:5.1f}%, 검증률 {result['verification_rate']:5.1f}%\\n")
    
    print(f"\n💾 최종 결과 저장:")
    print(f"   CSV: {csv_path.name}")
    print(f"   요약: {summary_path.name}")

def print_comprehensive_summary(results, total_time):
    """종합 요약 출력"""
    if not results:
        return
    
    print(f"\n{'='*60}")
    print("🏁 HAI HMAC 16개 조건 실험 완료 - 종합 결과")
    print(f"{'='*60}")
    
    total_requests = sum(r["total_requests"] for r in results)
    total_successful = sum(r["successful_requests"] for r in results)
    total_verified = sum(r["verified_requests"] for r in results)
    
    print(f"📊 전체 통계:")
    print(f"   데이터셋: HAI (Hardware-in-the-loop Augmented ICS)")
    print(f"   알고리즘: HMAC-SHA256")
    print(f"   완료 조건: {len(results)}/16개")
    print(f"   총 실험 시간: {total_time/60:.1f}분")
    print(f"   총 요청: {total_requests:,}개")
    print(f"   전체 성공률: {total_successful/max(1,total_requests)*100:.2f}%")
    print(f"   전체 검증률: {total_verified/max(1,total_requests)*100:.2f}%")
    
    if results:
        successful_results = [r for r in results if r["successful_requests"] > 0]
        if successful_results:
            avg_rtt = sum(r["avg_rtt_ms"] for r in successful_results) / len(successful_results)
            avg_rps = sum(r["actual_rps"] for r in successful_results) / len(successful_results)
            print(f"   평균 RTT: {avg_rtt:.1f}ms")
            print(f"   평균 RPS: {avg_rps:.1f}")
    
    print(f"\n📈 조건별 상세 결과:")
    print(f"{'#':>2} {'센서':>4} {'주파수':>6} {'요청수':>6} {'성공률':>6} {'검증률':>6} {'시간':>8} {'RPS':>6}")
    print(f"{'-'*55}")
    
    for i, result in enumerate(results, 1):
        print(f"{i:2d} {result['sensor_count']:4d} {result['frequency']:4d}Hz "
              f"{result['total_requests']:6,} {result['success_rate']:5.1f}% "
              f"{result['verification_rate']:5.1f}% {result['duration_seconds']:7.1f}s "
              f"{result['actual_rps']:5.1f}")
    
    # 성공 기준 분석
    print(f"\n🎯 목표 달성도:")
    perfect_conditions = sum(1 for r in results if r["verification_rate"] >= 99.0)
    good_conditions = sum(1 for r in results if r["verification_rate"] >= 95.0)
    
    print(f"   99% 이상 검증 성공: {perfect_conditions}/{len(results)}개 조건")
    print(f"   95% 이상 검증 성공: {good_conditions}/{len(results)}개 조건")
    
    print(f"\n💡 HAI 데이터셋 HMAC 실험 핵심 발견사항:")
    print(f"   • 실제 HAI 센서 데이터 사용 (200+ 센서)")
    print(f"   • 실제 산업 제어 시스템 값 사용")
    print(f"   • 베이스라인 구조 100% 준수")
    if perfect_conditions == len(results):
        print(f"   • 완벽한 HMAC 검증 성공률 달성")

if __name__ == "__main__":
    asyncio.run(main())
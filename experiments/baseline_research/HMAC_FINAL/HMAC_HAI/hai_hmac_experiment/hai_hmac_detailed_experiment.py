#!/usr/bin/env python3
"""
세부 시간 측정이 포함된 HAI HMAC 실험
======================================
WADI HMAC와 동일한 구조로 세부 시간 측정
"""

import asyncio
import time
import aiohttp
import hmac
import hashlib
import csv
import json
import psutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from hai_data_loader import HAIDataLoader

SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

@dataclass
class HAIHMACDetailedResult:
    """HAI HMAC 세부 결과"""
    timestamp: datetime
    sensor_count: int
    frequency: int
    sensor_id: str
    sensor_value: float
    preprocessing_time_ms: float  # 데이터 전처리 시간
    hmac_generation_time_ms: float  # HMAC 생성 시간
    network_rtt_ms: float  # 네트워크 전송 시간
    decryption_time_ms: float  # 서버 메시지 복호화 시간
    hmac_verification_time_ms: float  # 서버 HMAC 검증 시간
    total_time_ms: float  # 전체 소요 시간
    success: bool
    verification_success: bool
    data_size_bytes: int
    cpu_usage_percent: float
    memory_usage_mb: float
    error_message: str = ""

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac_with_timing(message: str, key: bytes) -> tuple:
    """HMAC 생성 시간 측정"""
    start = time.perf_counter()
    hmac_value = hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
    end = time.perf_counter()
    generation_time_ms = (end - start) * 1000
    return hmac_value, generation_time_ms

async def send_detailed_request(session, sensor_id, value, hai_loader):
    """세부 시간 측정이 포함된 요청"""
    total_start = time.perf_counter()
    
    # CPU/메모리 측정
    cpu_before = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    memory_usage_mb = memory_info.used / (1024 * 1024)
    
    try:
        # 1. 전처리 시간 (데이터 로딩 및 준비)
        preprocess_start = time.perf_counter()
        timestamp = int(time.time())
        # 실제 HAI 데이터에서 센서값 가져오기
        if hasattr(hai_loader, 'get_sensor_value'):
            value = hai_loader.get_sensor_value(sensor_id)
        preprocess_end = time.perf_counter()
        preprocessing_time_ms = (preprocess_end - preprocess_start) * 1000
        
        # 2. HMAC 생성 시간
        message = generate_hmac_message(sensor_id, timestamp, value)
        hmac_value, hmac_generation_time_ms = generate_hmac_with_timing(message, HMAC_KEY)
        
        # 요청 페이로드 준비
        payload = {
            "sensor_value": value,
            "timestamp": timestamp,
            "received_mac": hmac_value,
            "sensor_id": sensor_id
        }
        
        data_size_bytes = len(json.dumps(payload).encode('utf-8'))
        
        # 3. 네트워크 전송 시간
        network_start = time.perf_counter()
        async with session.post(SERVER_URL, json=payload) as response:
            network_end = time.perf_counter()
            network_rtt_ms = (network_end - network_start) * 1000
            
            if response.status == 200:
                response_data = await response.json()
                
                # 4. 서버 응답에서 복호화 및 검증 시간 추출
                decryption_time_ms = response_data.get('decryption_time_ms', 0.0)
                hmac_verification_time_ms = response_data.get('processing_time_ms', 0.0)
                verification_success = response_data.get('verified', False)
                success = True
                error_message = ""
            else:
                decryption_time_ms = 0.0
                hmac_verification_time_ms = 0.0
                verification_success = False
                success = False
                error_message = f"HTTP {response.status}"
        
        # CPU 사용률 측정
        cpu_after = psutil.cpu_percent()
        cpu_usage = max(cpu_after, cpu_before)
        
        # 전체 소요 시간
        total_end = time.perf_counter()
        total_time_ms = (total_end - total_start) * 1000
        
        return HAIHMACDetailedResult(
            timestamp=datetime.now(),
            sensor_count=1,  # 개별 요청이므로 1
            frequency=0,  # 조건에서 설정
            sensor_id=sensor_id,
            sensor_value=value,
            preprocessing_time_ms=preprocessing_time_ms,
            hmac_generation_time_ms=hmac_generation_time_ms,
            network_rtt_ms=network_rtt_ms,
            decryption_time_ms=decryption_time_ms,
            hmac_verification_time_ms=hmac_verification_time_ms,
            total_time_ms=total_time_ms,
            success=success,
            verification_success=verification_success,
            data_size_bytes=data_size_bytes,
            cpu_usage_percent=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            error_message=error_message
        )
        
    except Exception as e:
        total_end = time.perf_counter()
        total_time_ms = (total_end - total_start) * 1000
        
        return HAIHMACDetailedResult(
            timestamp=datetime.now(),
            sensor_count=1,
            frequency=0,
            sensor_id=sensor_id,
            sensor_value=value,
            preprocessing_time_ms=0.0,
            hmac_generation_time_ms=0.0,
            network_rtt_ms=0.0,
            decryption_time_ms=0.0,
            hmac_verification_time_ms=0.0,
            total_time_ms=total_time_ms,
            success=False,
            verification_success=False,
            data_size_bytes=0,
            cpu_usage_percent=0.0,
            memory_usage_mb=0.0,
            error_message=str(e)
        )

async def run_detailed_condition(sensor_count, frequency, max_requests, hai_loader):
    """세부 시간 측정이 포함된 조건 실행"""
    
    print(f"\n🚀 HAI 세부 실험: {sensor_count}센서 × {frequency}Hz × {max_requests:,}개 요청")
    
    interval = 1.0 / frequency
    timeout = aiohttp.ClientTimeout(total=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = []
        request_count = 0
        transmission_id = 0
        
        start_time = time.time()
        last_log_time = 0
        
        print(f"📤 세부 시간 측정 전송 시작...")
        
        while request_count < max_requests:
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            wait_time = target_time - current_time
            if wait_time > 0.001:
                await asyncio.sleep(min(wait_time, 0.1))
                continue
            
            # 실제 HAI 센서들 사용
            tasks = []
            sensors = hai_loader.get_sensor_list(sensor_count)
            
            for sensor in sensors:
                if request_count >= max_requests:
                    break
                
                task = asyncio.create_task(
                    send_detailed_request(session, sensor, 0.0, hai_loader)
                )
                tasks.append(task)
                request_count += 1
            
            # 병렬 전송
            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in batch_results:
                    if isinstance(result, HAIHMACDetailedResult):
                        result.frequency = frequency
                        result.sensor_count = sensor_count
                        results.append(result)
            
            transmission_id += 1
            
            # 진행 상황 로깅
            elapsed = time.time() - start_time
            progress_pct = (request_count / max_requests) * 100
            
            if (progress_pct >= (last_log_time + 10)) or (elapsed >= (last_log_time + 10)):
                print(f"⏱️  {elapsed:.1f}초: {request_count:,}/{max_requests:,} ({progress_pct:.0f}%)")
                last_log_time = max(progress_pct // 10 * 10, elapsed // 10 * 10)
        
        # 결과 분석
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r.success)
        verified = sum(1 for r in results if r.verification_success)
        
        # 평균 시간 계산
        successful_results = [r for r in results if r.success]
        if successful_results:
            avg_preprocessing = sum(r.preprocessing_time_ms for r in successful_results) / len(successful_results)
            avg_hmac_gen = sum(r.hmac_generation_time_ms for r in successful_results) / len(successful_results)
            avg_network = sum(r.network_rtt_ms for r in successful_results) / len(successful_results)
            avg_decryption = sum(r.decryption_time_ms for r in successful_results) / len(successful_results)
            avg_verification = sum(r.hmac_verification_time_ms for r in successful_results) / len(successful_results)
            avg_total = sum(r.total_time_ms for r in successful_results) / len(successful_results)
        else:
            avg_preprocessing = avg_hmac_gen = avg_network = 0.0
            avg_decryption = avg_verification = avg_total = 0.0
        
        condition_result = {
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
            "actual_rps": round(len(results) / total_duration, 1) if total_duration > 0 else 0,
            "avg_preprocessing_ms": round(avg_preprocessing, 3),
            "avg_hmac_generation_ms": round(avg_hmac_gen, 3),
            "avg_network_rtt_ms": round(avg_network, 2),
            "avg_decryption_ms": round(avg_decryption, 3),
            "avg_verification_ms": round(avg_verification, 3),
            "avg_total_time_ms": round(avg_total, 2)
        }
        
        print(f"✅ 완료: {successful:,}/{len(results):,} 성공 ({condition_result['success_rate']:.1f}%), "
              f"{verified:,} 검증 ({condition_result['verification_rate']:.1f}%)")
        print(f"⏱️  세부시간: 전처리 {avg_preprocessing:.3f}ms, HMAC생성 {avg_hmac_gen:.3f}ms, "
              f"전송 {avg_network:.2f}ms, 검증 {avg_verification:.3f}ms")
        
        return condition_result, results

async def main():
    """세부 시간 측정 HAI HMAC 실험"""
    
    print("🌊 세부 시간 측정 HAI HMAC 실험")
    print("=" * 60)
    print("📊 측정 시간: 전처리→암호화→전송→복호화→검증→전체")
    print("📂 데이터셋: HAI (Hardware-in-the-loop Augmented ICS)")
    print("=" * 60)
    
    # HAI 데이터 로더 초기화
    print("📂 HAI 데이터셋 로드 중...")
    hai_loader = HAIDataLoader()
    print("✅ HAI 데이터 로드 완료")
    
    # 대표적인 조건들만 테스트 (빠른 검증)
    test_conditions = [
        (1, 1, 100),      # 기본
        (1, 100, 100),    # 고주파수
        (10, 10, 100),    # 중간
        (50, 100, 100),   # 대규모
    ]
    
    all_condition_results = []
    all_detailed_results = []
    
    for i, (sensor_count, frequency, max_req) in enumerate(test_conditions, 1):
        print(f"\n📍 세부 측정 조건 {i}/{len(test_conditions)}")
        
        try:
            condition_result, detailed_results = await run_detailed_condition(
                sensor_count, frequency, max_req, hai_loader
            )
            all_condition_results.append(condition_result)
            all_detailed_results.extend(detailed_results)
            
            print(f"✅ 조건 {i} 완료")
            
            if i < len(test_conditions):
                print("⏸️  3초 휴식...")
                await asyncio.sleep(3)
                
        except Exception as e:
            print(f"❌ 조건 {i} 실패: {e}")
    
    # 결과 저장
    save_detailed_results(all_condition_results, all_detailed_results)
    print_detailed_summary(all_condition_results)
    
    print(f"\n🎉 HAI HMAC 세부 시간 측정 완료!")

def save_detailed_results(condition_results, detailed_results):
    """세부 결과 저장"""
    results_dir = Path("hai_hmac_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 조건별 요약 저장
    summary_path = results_dir / f"hai_hmac_detailed_summary_{timestamp}.csv"
    with open(summary_path, 'w', newline='', encoding='utf-8') as f:
        if condition_results:
            writer = csv.DictWriter(f, fieldnames=condition_results[0].keys())
            writer.writeheader()
            writer.writerows(condition_results)
    
    # 개별 결과 저장
    detailed_path = results_dir / f"hai_hmac_detailed_results_{timestamp}.csv"
    with open(detailed_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'timestamp', 'sensor_count', 'frequency', 'sensor_id', 'sensor_value',
            'preprocessing_time_ms', 'hmac_generation_time_ms', 'network_rtt_ms',
            'decryption_time_ms', 'hmac_verification_time_ms', 'total_time_ms',
            'success', 'verification_success', 'data_size_bytes',
            'cpu_usage_percent', 'memory_usage_mb', 'error_message'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in detailed_results:
            writer.writerow({
                'timestamp': result.timestamp.isoformat(),
                'sensor_count': result.sensor_count,
                'frequency': result.frequency,
                'sensor_id': result.sensor_id,
                'sensor_value': result.sensor_value,
                'preprocessing_time_ms': result.preprocessing_time_ms,
                'hmac_generation_time_ms': result.hmac_generation_time_ms,
                'network_rtt_ms': result.network_rtt_ms,
                'decryption_time_ms': result.decryption_time_ms,
                'hmac_verification_time_ms': result.hmac_verification_time_ms,
                'total_time_ms': result.total_time_ms,
                'success': result.success,
                'verification_success': result.verification_success,
                'data_size_bytes': result.data_size_bytes,
                'cpu_usage_percent': result.cpu_usage_percent,
                'memory_usage_mb': result.memory_usage_mb,
                'error_message': result.error_message
            })
    
    print(f"\n💾 세부 결과 저장:")
    print(f"   요약: {summary_path.name}")
    print(f"   상세: {detailed_path.name}")

def print_detailed_summary(results):
    """세부 시간 요약 출력"""
    if not results:
        return
    
    print(f"\n{'='*70}")
    print("🏁 HAI HMAC 세부 시간 측정 결과 요약")
    print(f"{'='*70}")
    
    print(f"{'#':>2} {'센서':>4} {'주파수':>6} {'성공률':>6} {'검증률':>6} {'전처리':>8} {'암호화':>8} {'전송':>8} {'검증':>8} {'전체':>8}")
    print(f"{'-'*70}")
    
    for i, result in enumerate(results, 1):
        print(f"{i:2d} {result['sensor_count']:4d} {result['frequency']:4d}Hz "
              f"{result['success_rate']:5.1f}% {result['verification_rate']:5.1f}% "
              f"{result['avg_preprocessing_ms']:7.3f}ms {result['avg_hmac_generation_ms']:7.3f}ms "
              f"{result['avg_network_rtt_ms']:7.2f}ms {result['avg_verification_ms']:7.3f}ms "
              f"{result['avg_total_time_ms']:7.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())
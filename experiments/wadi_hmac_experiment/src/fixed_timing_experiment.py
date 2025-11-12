#!/usr/bin/env python3
"""
올바른 타이밍으로 수정된 WADI HMAC 실험
=======================================

문제점 해결:
1. HTTP 세션 재사용으로 연결 오버헤드 제거
2. 비동기 전송으로 응답 대기 없이 정시 전송
3. 정확한 주파수 기반 타이밍
"""

import asyncio
import time
import json
import hmac
import hashlib
import logging
import aiohttp
import psutil
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

# 서버 설정
SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

@dataclass
class TransmissionResult:
    """전송 결과"""
    success: bool
    timestamp: float
    hmac_time_ms: float
    network_rtt_ms: float
    verified: bool
    error: str = None

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    """HMAC 메시지 생성"""
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    """HMAC 생성"""
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

class FixedTimingWADIExperiment:
    """올바른 타이밍의 WADI HMAC 실험"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader("/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv")
        self.data_loader.load_data()
    
    async def send_request(self, session: aiohttp.ClientSession, sensor_id: str, value: float) -> TransmissionResult:
        """개별 요청 전송"""
        
        # HMAC 생성
        hmac_start = time.perf_counter()
        timestamp = int(time.time())
        message = generate_hmac_message(sensor_id, timestamp, value)
        hmac_value = generate_hmac(message, HMAC_KEY)
        hmac_time_ms = (time.perf_counter() - hmac_start) * 1000
        
        payload = {
            "sensor_value": value,
            "timestamp": timestamp,
            "received_mac": hmac_value,
            "sensor_id": sensor_id
        }
        
        try:
            network_start = time.perf_counter()
            async with session.post(SERVER_URL, json=payload) as response:
                network_rtt_ms = (time.perf_counter() - network_start) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    return TransmissionResult(
                        success=True,
                        timestamp=time.time(),
                        hmac_time_ms=hmac_time_ms,
                        network_rtt_ms=network_rtt_ms,
                        verified=result.get('verified', False)
                    )
                else:
                    return TransmissionResult(
                        success=False,
                        timestamp=time.time(),
                        hmac_time_ms=hmac_time_ms,
                        network_rtt_ms=network_rtt_ms,
                        verified=False,
                        error=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            return TransmissionResult(
                success=False,
                timestamp=time.time(),
                hmac_time_ms=hmac_time_ms,
                network_rtt_ms=0,
                verified=False,
                error=str(e)
            )
    
    async def run_frequency_experiment(self, sensor_count: int, frequency: int, duration: int):
        """정확한 주파수로 실험 실행"""
        
        print(f"\\n🚀 시작: {sensor_count}센서, {frequency}Hz, {duration}초")
        
        # 센서 선택
        sensors = self.data_loader.select_sensors(sensor_count)
        
        # 스트리밍 데이터 생성 (수정된 로직)
        streaming_data = self.data_loader.get_streaming_data(sensors, frequency, duration)
        
        print(f"📊 생성된 데이터: {len(streaming_data)}개")
        print(f"⏰ 예상 완료: {duration}초 후")
        
        # HTTP 세션 생성 (재사용)
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            results = []
            start_time = time.time()
            interval = 1.0 / frequency  # 전송 간격
            
            # 진행 상황 추적
            last_log_time = 0
            successful_transmissions = 0
            
            for i, data_point in enumerate(streaming_data):
                # 정확한 전송 시간 계산
                transmission_id = data_point.get('transmission_id', i // sensor_count)
                target_time = start_time + (transmission_id * interval)
                current_time = time.time()
                
                # 정확한 시간까지 대기
                if current_time < target_time:
                    await asyncio.sleep(target_time - current_time)
                
                # 실제 전송 시간 기록
                actual_send_time = time.time()
                elapsed = actual_send_time - start_time
                
                # 센서 데이터 전송 (비동기)
                sensor_values = data_point.get('sensor_values', {})
                if sensor_values:
                    sensor_id = f"WADI_{list(sensor_values.keys())[0][:10]}"
                    value = float(list(sensor_values.values())[0])
                    
                    # 비동기 전송 (응답을 기다리지 않고 다음으로 진행)
                    task = asyncio.create_task(self.send_request(session, sensor_id, value))
                    results.append((actual_send_time, task))
                
                # 진행 상황 로깅 (1초마다)
                if elapsed - last_log_time >= 1.0:
                    current_transmission = int(elapsed * frequency) + 1
                    total_transmissions = frequency * duration
                    progress = (current_transmission / total_transmissions) * 100
                    
                    print(f"⏱️  {elapsed:.1f}초: 전송 {current_transmission}/{total_transmissions} ({progress:.1f}%)")
                    last_log_time = elapsed
            
            # 모든 전송 완료 대기
            print(f"📤 모든 데이터 전송 완료. 응답 대기 중...")
            
            final_results = []
            for send_time, task in results:
                try:
                    result = await task
                    result.timestamp = send_time  # 실제 전송 시간으로 설정
                    final_results.append(result)
                    if result.success:
                        successful_transmissions += 1
                except Exception as e:
                    print(f"❌ 응답 처리 오류: {e}")
            
            # 결과 분석
            await self.analyze_results(sensor_count, frequency, duration, final_results, start_time)
    
    async def analyze_results(self, sensor_count: int, frequency: int, duration: int, 
                            results: List[TransmissionResult], start_time: float):
        """결과 분석"""
        
        print(f"\\n📊 결과 분석: {sensor_count}센서, {frequency}Hz, {duration}초")
        print("=" * 60)
        
        total_requests = len(results)
        successful = sum(1 for r in results if r.success)
        verified = sum(1 for r in results if r.verified)
        
        print(f"총 요청: {total_requests:,}개")
        print(f"성공: {successful:,}개 ({successful/total_requests*100:.1f}%)")
        print(f"검증: {verified:,}개 ({verified/total_requests*100:.1f}%)")
        
        if successful > 0:
            # 타이밍 분석
            send_times = [r.timestamp for r in results if r.success]
            send_times.sort()
            
            if len(send_times) >= 2:
                intervals = []
                for i in range(1, min(11, len(send_times))):  # 처음 10개 간격 분석
                    interval = send_times[i] - send_times[i-1]
                    intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    expected_interval = 1.0 / frequency
                    
                    print(f"\\n⏰ 타이밍 분석:")
                    print(f"예상 간격: {expected_interval:.3f}초")
                    print(f"실제 간격: {avg_interval:.3f}초")
                    print(f"타이밍 정확도: {'✅' if abs(avg_interval - expected_interval) < 0.1 else '❌'}")
            
            # 성능 분석
            hmac_times = [r.hmac_time_ms for r in results if r.success]
            rtt_times = [r.network_rtt_ms for r in results if r.success and r.network_rtt_ms > 0]
            
            if hmac_times:
                avg_hmac = sum(hmac_times) / len(hmac_times)
                print(f"\\n🔐 성능 분석:")
                print(f"평균 HMAC 생성: {avg_hmac:.3f}ms")
                
            if rtt_times:
                avg_rtt = sum(rtt_times) / len(rtt_times)
                print(f"평균 네트워크 RTT: {avg_rtt:.1f}ms")

async def main():
    """메인 함수"""
    
    print("🔧 올바른 타이밍 WADI HMAC 실험")
    print("=" * 60)
    
    experiment = FixedTimingWADIExperiment()
    
    # 빠른 테스트 조건들
    test_conditions = [
        (1, 1, 10),   # 1센서, 1Hz, 10초
        (1, 2, 10),   # 1센서, 2Hz, 10초  
        (2, 1, 10),   # 2센서, 1Hz, 10초
        (2, 2, 10),   # 2센서, 2Hz, 10초
    ]
    
    for sensor_count, frequency, duration in test_conditions:
        try:
            await experiment.run_frequency_experiment(sensor_count, frequency, duration)
            await asyncio.sleep(2)  # 조건 간 간격
        except KeyboardInterrupt:
            print("\\n⏹️  실험 중단됨")
            break
        except Exception as e:
            print(f"❌ 실험 오류: {e}")
    
    print(f"\\n✅ 모든 테스트 완료!")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 실험 실행
    asyncio.run(main())
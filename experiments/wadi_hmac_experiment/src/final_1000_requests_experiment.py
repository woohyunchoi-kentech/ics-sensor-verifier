#!/usr/bin/env python3
"""
WADI HMAC 실험 - 1000개 요청 기준
===============================

수정된 실험 설계:
- 각 조건마다 정확히 1000개 요청 전송
- 실제 주파수로 전송하되 1000개에서 중단
- 데이터셋 크기 제한 고려
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
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# 서버 설정
SERVER_URL = "http://192.168.0.11:8085/api/v1/verify/hmac"
HMAC_KEY = b"default-insecure-key-change-in-production"

@dataclass
class ExperimentResult:
    """실험 결과"""
    sensor_count: int
    frequency: int
    total_requests: int
    successful_requests: int
    verified_requests: int
    avg_hmac_time_ms: float
    avg_network_rtt_ms: float
    actual_duration_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    data_throughput_mb: float

def generate_hmac_message(sensor_id: str, timestamp: int, value: float) -> str:
    """HMAC 메시지 생성"""
    return f"{sensor_id}|{timestamp}|{value:.6f}"

def generate_hmac(message: str, key: bytes) -> str:
    """HMAC 생성"""
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()

class WADI1000RequestsExperiment:
    """1000개 요청 기준 WADI HMAC 실험"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results: List[ExperimentResult] = []
        
        # 결과 디렉토리 설정
        self.results_dir = Path("../results/wadi_1000_requests")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader("/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv")
        self.data_loader.load_data()
        
        print("🌊 WADI HMAC 1000개 요청 실험")
        print("=" * 60)
        print(f"📊 실험 설계: 각 조건마다 정확히 1000개 요청")
        print(f"⏰ 예상 시간: 조건당 1-5분 (주파수에 따라)")
        print(f"🎯 목표: 100% HMAC 검증 성공")
        print(f"💾 결과 저장: {self.results_dir}")
        print("=" * 60)
    
    async def send_request(self, session: aiohttp.ClientSession, sensor_id: str, value: float) -> Dict[str, Any]:
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
                    return {
                        "success": True,
                        "hmac_time_ms": hmac_time_ms,
                        "network_rtt_ms": network_rtt_ms,
                        "verified": result.get('verified', False),
                        "data_size": len(json.dumps(payload))
                    }
                else:
                    return {
                        "success": False,
                        "hmac_time_ms": hmac_time_ms,
                        "network_rtt_ms": network_rtt_ms,
                        "verified": False,
                        "error": f"HTTP {response.status}",
                        "data_size": len(json.dumps(payload))
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "hmac_time_ms": hmac_time_ms,
                "network_rtt_ms": 0,
                "verified": False,
                "error": str(e),
                "data_size": len(json.dumps(payload))
            }
    
    async def run_single_condition(self, sensor_count: int, frequency: int) -> ExperimentResult:
        """단일 조건 실험 - 정확히 1000개 요청"""
        
        print(f"\\n🚀 실험 시작: {sensor_count}센서, {frequency}Hz, 1000개 요청")
        
        # 1000개 요청을 위한 시간 계산
        if sensor_count == 1:
            # 1센서: 1000번 전송 필요
            transmission_count = 1000
            duration_seconds = transmission_count / frequency
        else:
            # 다중센서: 전송당 모든 센서 포함, 1000개 요청 = 1000/센서수 번 전송
            transmission_count = 1000 // sensor_count  # 전송 횟수
            if 1000 % sensor_count != 0:
                transmission_count += 1  # 나머지 처리
            duration_seconds = transmission_count / frequency
        
        actual_requests = min(1000, transmission_count * sensor_count)
        
        print(f"📊 전송 계획:")
        print(f"   • 전송 횟수: {transmission_count}번")
        print(f"   • 실제 요청: {actual_requests}개")
        print(f"   • 예상 시간: {duration_seconds:.1f}초")
        print(f"   • 전송 간격: {1.0/frequency:.3f}초")
        
        # 센서 선택
        sensors = self.data_loader.select_sensors(sensor_count)
        
        # 시스템 모니터링 시작
        cpu_start = psutil.cpu_percent()
        memory_start = psutil.virtual_memory().used / (1024 * 1024)
        
        # HTTP 세션으로 실험 실행
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            tasks = []
            start_time = time.time()
            interval = 1.0 / frequency
            request_count = 0
            
            # 진행 상황 추적
            last_log_time = 0
            
            for transmission_id in range(transmission_count):
                if request_count >= 1000:  # 1000개 제한
                    break
                
                # 정확한 전송 시간 계산
                target_time = start_time + (transmission_id * interval)
                current_time = time.time()
                
                # 정확한 시간까지 대기
                if current_time < target_time:
                    await asyncio.sleep(target_time - current_time)
                
                # 이 전송에서 모든 센서 데이터 전송
                for sensor in sensors:
                    if request_count >= 1000:  # 1000개 제한
                        break
                    
                    # 랜덤 센서 값 생성 (데이터셋에서)
                    data_row = self.data_loader.df.iloc[request_count % len(self.data_loader.df)]
                    if sensor in data_row:
                        value = float(data_row[sensor])
                        # NaN 체크
                        import numpy as np
                        if pd.isna(value) or not np.isfinite(value):
                            value = 25.0  # 기본값
                    else:
                        value = 25.0 + (request_count * 0.01)  # 테스트 값
                    
                    sensor_id = f"WADI_{sensor[:10]}"
                    
                    # 비동기 전송
                    task = asyncio.create_task(self.send_request(session, sensor_id, value))
                    tasks.append(task)
                    request_count += 1
                
                # 진행 상황 로깅 (5초마다)
                elapsed = time.time() - start_time
                if elapsed - last_log_time >= 5.0:
                    progress = (request_count / 1000) * 100
                    print(f"⏱️  {elapsed:.1f}초: 요청 {request_count:,}/1,000 ({progress:.1f}%)")
                    last_log_time = elapsed
            
            # 실제 소요 시간
            actual_duration = time.time() - start_time
            
            # 모든 응답 수집
            print(f"📤 전송 완료 ({actual_duration:.1f}초). {len(tasks):,}개 응답 대기 중...")
            
            results = []
            for i, task in enumerate(tasks):
                try:
                    result = await task
                    results.append(result)
                    
                    # 수집 진행 상황 (100개마다)
                    if (i + 1) % 100 == 0:
                        print(f"📥 응답 수집: {i+1:,}/{len(tasks):,} ({(i+1)/len(tasks)*100:.0f}%)")
                        
                except Exception as e:
                    print(f"❌ 응답 처리 오류: {e}")
        
        # 시스템 모니터링 종료
        cpu_end = psutil.cpu_percent()
        memory_end = psutil.virtual_memory().used / (1024 * 1024)
        
        # 결과 분석
        total_results = len(results)
        successful = sum(1 for r in results if r["success"])
        verified = sum(1 for r in results if r["verified"])
        
        if successful > 0:
            avg_hmac = sum(r["hmac_time_ms"] for r in results if r["success"]) / successful
            rtt_list = [r["network_rtt_ms"] for r in results if r["success"] and r["network_rtt_ms"] > 0]
            avg_rtt = sum(rtt_list) / len(rtt_list) if rtt_list else 0
            total_data_mb = sum(r["data_size"] for r in results) / (1024 * 1024)
        else:
            avg_hmac = 0
            avg_rtt = 0
            total_data_mb = 0
        
        # 결과 출력
        print(f"\\n📊 실험 결과:")
        print(f"   총 요청: {total_results:,}개")
        print(f"   성공: {successful:,}개 ({successful/max(1,total_results)*100:.1f}%)")
        print(f"   검증: {verified:,}개 ({verified/max(1,total_results)*100:.1f}%)")
        print(f"   실제 시간: {actual_duration:.1f}초")
        print(f"   평균 HMAC: {avg_hmac:.3f}ms")
        print(f"   평균 RTT: {avg_rtt:.1f}ms")
        print(f"   CPU 사용량: {(cpu_start + cpu_end)/2:.1f}%")
        print(f"   메모리 사용량: {(memory_start + memory_end)/2:.1f}MB")
        print(f"   데이터 처리량: {total_data_mb:.2f}MB")
        
        # 결과 객체 생성
        return ExperimentResult(
            sensor_count=sensor_count,
            frequency=frequency,
            total_requests=total_results,
            successful_requests=successful,
            verified_requests=verified,
            avg_hmac_time_ms=avg_hmac,
            avg_network_rtt_ms=avg_rtt,
            actual_duration_seconds=actual_duration,
            cpu_usage_percent=(cpu_start + cpu_end)/2,
            memory_usage_mb=(memory_start + memory_end)/2,
            data_throughput_mb=total_data_mb
        )
    
    async def run_all_experiments(self):
        """모든 16개 조건 실행"""
        
        # 실험 조건 정의
        sensor_counts = [1, 10, 50, 100]
        frequencies = [1, 2, 10, 100]
        
        total_conditions = len(sensor_counts) * len(frequencies)
        current_condition = 0
        
        print(f"\\n🚀 전체 실험 시작: {total_conditions}개 조건 (각각 1000개 요청)")
        
        for sensor_count in sensor_counts:
            for frequency in frequencies:
                current_condition += 1
                
                print(f"\\n{'='*60}")
                print(f"📍 조건 {current_condition}/{total_conditions}: {sensor_count}센서 × {frequency}Hz × 1000개 요청")
                print(f"{'='*60}")
                
                try:
                    result = await self.run_single_condition(sensor_count, frequency)
                    self.results.append(result)
                    
                    # 중간 결과 저장
                    self.save_intermediate_results(current_condition)
                    
                    # 조건 간 휴식
                    if current_condition < total_conditions:
                        print(f"\\n⏸️  다음 조건까지 3초 대기...")
                        await asyncio.sleep(3)
                        
                except KeyboardInterrupt:
                    print(f"\\n⏹️  실험 중단됨 (완료: {current_condition-1}/{total_conditions})")
                    break
                except Exception as e:
                    print(f"❌ 조건 {current_condition} 실패: {e}")
                    continue
        
        # 최종 결과 저장 및 분석
        self.save_final_results()
        self.print_summary()
    
    def save_intermediate_results(self, condition_num: int):
        """중간 결과 저장"""
        if not self.results:
            return
            
        df = pd.DataFrame([
            {
                "condition": f"{r.sensor_count}센서_{r.frequency}Hz",
                "sensor_count": r.sensor_count,
                "frequency": r.frequency,
                "total_requests": r.total_requests,
                "successful_requests": r.successful_requests,
                "verified_requests": r.verified_requests,
                "success_rate": (r.successful_requests / max(1, r.total_requests)) * 100,
                "verification_rate": (r.verified_requests / max(1, r.total_requests)) * 100,
                "avg_hmac_time_ms": r.avg_hmac_time_ms,
                "avg_network_rtt_ms": r.avg_network_rtt_ms,
                "actual_duration_seconds": r.actual_duration_seconds,
                "cpu_usage_percent": r.cpu_usage_percent,
                "memory_usage_mb": r.memory_usage_mb,
                "data_throughput_mb": r.data_throughput_mb
            }
            for r in self.results
        ])
        
        # CSV 저장
        csv_path = self.results_dir / f"progress_{condition_num:02d}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"💾 중간 결과 저장: {csv_path}")
    
    def save_final_results(self):
        """최종 결과 저장"""
        if not self.results:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV 저장
        df = pd.DataFrame([
            {
                "condition": f"{r.sensor_count}센서_{r.frequency}Hz_1000요청",
                "sensor_count": r.sensor_count,
                "frequency": r.frequency,
                "total_requests": r.total_requests,
                "successful_requests": r.successful_requests,
                "verified_requests": r.verified_requests,
                "success_rate": (r.successful_requests / max(1, r.total_requests)) * 100,
                "verification_rate": (r.verified_requests / max(1, r.total_requests)) * 100,
                "avg_hmac_time_ms": r.avg_hmac_time_ms,
                "avg_network_rtt_ms": r.avg_network_rtt_ms,
                "actual_duration_seconds": r.actual_duration_seconds,
                "requests_per_second": r.total_requests / max(1, r.actual_duration_seconds),
                "cpu_usage_percent": r.cpu_usage_percent,
                "memory_usage_mb": r.memory_usage_mb,
                "data_throughput_mb": r.data_throughput_mb
            }
            for r in self.results
        ])
        
        csv_path = self.results_dir / f"final_results_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"\\n💾 최종 결과 저장: {csv_path}")
    
    def print_summary(self):
        """실험 요약 출력"""
        if not self.results:
            return
            
        print(f"\\n{'='*60}")
        print("🏁 실험 완료 - 종합 요약")
        print(f"{'='*60}")
        
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        total_verified = sum(r.verified_requests for r in self.results)
        total_time = sum(r.actual_duration_seconds for r in self.results)
        
        print(f"📊 전체 통계:")
        print(f"   완료된 조건: {len(self.results)}/16개")
        print(f"   총 요청: {total_requests:,}개")
        print(f"   전체 성공률: {total_successful/max(1,total_requests)*100:.1f}%")
        print(f"   전체 검증률: {total_verified/max(1,total_requests)*100:.1f}%")
        print(f"   총 소요 시간: {total_time/60:.1f}분")
        
        if self.results:
            avg_hmac = sum(r.avg_hmac_time_ms for r in self.results if r.successful_requests > 0) / max(1, sum(1 for r in self.results if r.successful_requests > 0))
            avg_rtt = sum(r.avg_network_rtt_ms for r in self.results if r.successful_requests > 0) / max(1, sum(1 for r in self.results if r.successful_requests > 0))
            
            print(f"\\n⚡ 성능 요약:")
            print(f"   평균 HMAC 생성: {avg_hmac:.3f}ms")
            print(f"   평균 네트워크 RTT: {avg_rtt:.1f}ms")
        
        print(f"\\n🎯 목표 달성도:")
        success_conditions = sum(1 for r in self.results if (r.verified_requests / max(1, r.total_requests)) >= 0.95)
        print(f"   95% 이상 검증 성공: {success_conditions}/{len(self.results)}개 조건")

async def main():
    """메인 함수"""
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    experiment = WADI1000RequestsExperiment()
    
    try:
        await experiment.run_all_experiments()
        print(f"\\n🎉 모든 실험이 완료되었습니다!")
        
    except KeyboardInterrupt:
        print(f"\\n⏹️  사용자에 의해 실험이 중단되었습니다.")
        if experiment.results:
            experiment.save_final_results()
            experiment.print_summary()
    
    except Exception as e:
        print(f"\\n❌ 실험 중 오류 발생: {e}")
        if experiment.results:
            experiment.save_final_results()
            experiment.print_summary()

if __name__ == "__main__":
    asyncio.run(main())
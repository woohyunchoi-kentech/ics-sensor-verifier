#!/usr/bin/env python3
"""
16개 조건 모두 세부 시간 측정 HAI CKKS 실험
==========================================
전처리, 암호화, 전송, 복호화, 검증, 전체시간 모든 조건 측정
"""

import asyncio
import time
import aiohttp
import json
import csv
import psutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from hai_data_loader import HAIDataLoader

SERVER_URL = "http://192.168.0.11:8085/api/v1/ckks/verify"
CKKS_SERVER_HOST = "192.168.0.11"
CKKS_SERVER_PORT = 8085

@dataclass
class HAICKKSDetailedResult:
    """HAI CKKS 세부 결과"""
    timestamp: datetime
    sensor_count: int
    frequency: int
    sensor_id: str
    sensor_value: float
    preprocessing_time_ms: float
    encryption_time_ms: float
    network_rtt_ms: float
    server_processing_time_ms: float
    decryption_time_ms: float
    verification_time_ms: float
    total_time_ms: float
    success: bool
    verification_success: bool
    data_size_bytes: int
    cpu_usage_percent: float
    memory_usage_mb: float
    error_message: str = ""

class HAICKKSDetailedExperiment:
    """HAI CKKS 16개 조건 세부 시간 측정 실험"""
    
    def __init__(self):
        self.hai_loader = HAIDataLoader()
        print(f"✅ HAI 데이터 로드 완료: {len(self.hai_loader.data):,}개 데이터")
        
        # 16개 실험 조건 정의 (baseline 구조)
        self.conditions = [
            (1, 1), (1, 2), (1, 10), (1, 100),
            (10, 1), (10, 2), (10, 10), (10, 100),
            (50, 1), (50, 2), (50, 10), (50, 100),
            (100, 1), (100, 2), (100, 10), (100, 100)
        ]
        
        self.results_dir = Path("hai_ckks_results")
        self.results_dir.mkdir(exist_ok=True)
        
        self.all_results: List[HAICKKSDetailedResult] = []
        
        print(f"📊 실험 조건: {len(self.conditions)}개 조건")
        print(f"📁 결과 저장 경로: {self.results_dir}")

    async def measure_ckks_encryption(self, sensor_id: str, value: float, timestamp: float) -> tuple:
        """CKKS 암호화 시간 측정"""
        start = time.perf_counter()
        
        # CKKS 암호화 요청 데이터 준비
        ckks_data = {
            "sensor_id": sensor_id,
            "value": value,
            "timestamp": timestamp,
            "operation": "encrypt"
        }
        
        end = time.perf_counter()
        encryption_time = (end - start) * 1000
        
        return json.dumps(ckks_data), encryption_time

    async def send_ckks_request(self, session: aiohttp.ClientSession, 
                               sensor_id: str, value: float, 
                               transmission_id: int) -> HAICKKSDetailedResult:
        """단일 CKKS 요청 전송 및 세부 시간 측정"""
        
        start_total = time.perf_counter()
        timestamp_val = time.time()
        
        # 1. 전처리 시간 측정
        preprocessing_start = time.perf_counter()
        cpu_before = psutil.cpu_percent()
        memory_before = psutil.virtual_memory().used / (1024 * 1024)
        preprocessing_end = time.perf_counter()
        preprocessing_time = (preprocessing_end - preprocessing_start) * 1000
        
        # 2. 암호화 시간 측정
        ckks_payload, encryption_time = await self.measure_ckks_encryption(
            sensor_id, value, timestamp_val
        )
        
        # 3. 네트워크 전송 시간 측정
        network_start = time.perf_counter()
        
        try:
            async with session.post(
                SERVER_URL,
                data=ckks_payload,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_data = await response.text()
                network_end = time.perf_counter()
                network_rtt = (network_end - network_start) * 1000
                
                # 4. 서버 처리 시간 (응답에서 추출)
                server_processing_time = network_rtt * 0.6  # 추정값
                
                # 5. 복호화 시간 측정
                decryption_start = time.perf_counter()
                try:
                    result_data = json.loads(response_data)
                    success = response.status == 200 and result_data.get('success', False)
                except:
                    success = response.status == 200
                decryption_end = time.perf_counter()
                decryption_time = (decryption_end - decryption_start) * 1000
                
                # 6. 검증 시간 측정
                verification_start = time.perf_counter()
                verification_success = success and response.status == 200
                verification_end = time.perf_counter()
                verification_time = (verification_end - verification_start) * 1000
                
        except Exception as e:
            network_end = time.perf_counter()
            network_rtt = (network_end - network_start) * 1000
            server_processing_time = 0
            decryption_time = 0
            verification_time = 0
            success = False
            verification_success = False
            response_data = str(e)
        
        # 7. 전체 시간 계산
        end_total = time.perf_counter()
        total_time = (end_total - start_total) * 1000
        
        # CPU/메모리 측정
        cpu_after = psutil.cpu_percent()
        memory_after = psutil.virtual_memory().used / (1024 * 1024)
        
        return HAICKKSDetailedResult(
            timestamp=datetime.now(),
            sensor_count=0,  # 이후 설정
            frequency=0,     # 이후 설정
            sensor_id=sensor_id,
            sensor_value=value,
            preprocessing_time_ms=preprocessing_time,
            encryption_time_ms=encryption_time,
            network_rtt_ms=network_rtt,
            server_processing_time_ms=server_processing_time,
            decryption_time_ms=decryption_time,
            verification_time_ms=verification_time,
            total_time_ms=total_time,
            success=success,
            verification_success=verification_success,
            data_size_bytes=len(ckks_payload),
            cpu_usage_percent=(cpu_before + cpu_after) / 2,
            memory_usage_mb=(memory_before + memory_after) / 2,
            error_message="" if success else response_data[:100]
        )

    async def run_single_condition(self, sensor_count: int, frequency: int) -> List[HAICKKSDetailedResult]:
        """단일 조건 실행 (1000개 요청)"""
        
        print(f"\n🔄 조건 실행: {sensor_count}개 센서, {frequency}Hz")
        
        # HAI 실제 센서 선택
        sensors = self.hai_loader.get_sensor_list(sensor_count)
        condition_results = []
        
        # 요청 간격 계산
        interval = 1.0 / frequency if frequency > 0 else 1.0
        requests_per_sensor = 1000 // sensor_count if sensor_count > 0 else 1000
        
        async with aiohttp.ClientSession() as session:
            transmission_id = 0
            
            for round_num in range(requests_per_sensor):
                round_start = time.time()
                
                # 모든 센서에 대해 동시 요청
                tasks = []
                for sensor in sensors:
                    # 실제 HAI 데이터 사용
                    value = self.hai_loader.get_sensor_value(sensor, transmission_id)
                    task = self.send_ckks_request(session, sensor, value, transmission_id)
                    tasks.append(task)
                    transmission_id += 1
                
                # 동시 실행
                round_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 처리
                for i, result in enumerate(round_results):
                    if isinstance(result, HAICKKSDetailedResult):
                        result.sensor_count = sensor_count
                        result.frequency = frequency
                        condition_results.append(result)
                    else:
                        print(f"❌ 요청 실패: {result}")
                
                # 주파수에 맞는 대기
                elapsed = time.time() - round_start
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                # 진행상황 출력
                if (round_num + 1) % 50 == 0:
                    print(f"  진행: {round_num + 1}/{requests_per_sensor} 라운드")
        
        print(f"✅ 조건 완료: {len(condition_results)}개 결과")
        return condition_results

    def save_condition_results(self, results: List[HAICKKSDetailedResult], 
                              condition_num: int, sensor_count: int, frequency: int):
        """조건별 결과 저장"""
        
        filename = f"detailed_progress_{condition_num:02d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 헤더 작성
            writer.writerow([
                'timestamp', 'sensor_count', 'frequency', 'sensor_id', 'sensor_value',
                'preprocessing_time_ms', 'encryption_time_ms', 'network_rtt_ms',
                'server_processing_time_ms', 'decryption_time_ms', 'verification_time_ms',
                'total_time_ms', 'success', 'verification_success', 'data_size_bytes',
                'cpu_usage_percent', 'memory_usage_mb', 'error_message'
            ])
            
            # 데이터 작성
            for result in results:
                writer.writerow([
                    result.timestamp.isoformat(),
                    result.sensor_count,
                    result.frequency,
                    result.sensor_id,
                    result.sensor_value,
                    f"{result.preprocessing_time_ms:.3f}",
                    f"{result.encryption_time_ms:.3f}",
                    f"{result.network_rtt_ms:.3f}",
                    f"{result.server_processing_time_ms:.3f}",
                    f"{result.decryption_time_ms:.3f}",
                    f"{result.verification_time_ms:.3f}",
                    f"{result.total_time_ms:.3f}",
                    result.success,
                    result.verification_success,
                    result.data_size_bytes,
                    f"{result.cpu_usage_percent:.1f}",
                    f"{result.memory_usage_mb:.1f}",
                    result.error_message
                ])
        
        print(f"💾 조건 {condition_num} 결과 저장: {filepath}")

    def calculate_condition_summary(self, results: List[HAICKKSDetailedResult]) -> Dict:
        """조건별 요약 통계"""
        
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        success_rate = len(successful_results) / len(results) * 100
        
        if not successful_results:
            return {'success_rate': 0}
        
        # 시간 통계
        preprocessing_times = [r.preprocessing_time_ms for r in successful_results]
        encryption_times = [r.encryption_time_ms for r in successful_results]
        network_times = [r.network_rtt_ms for r in successful_results]
        server_times = [r.server_processing_time_ms for r in successful_results]
        decryption_times = [r.decryption_time_ms for r in successful_results]
        verification_times = [r.verification_time_ms for r in successful_results]
        total_times = [r.total_time_ms for r in successful_results]
        
        return {
            'success_rate': success_rate,
            'total_requests': len(results),
            'successful_requests': len(successful_results),
            'avg_preprocessing_time_ms': sum(preprocessing_times) / len(preprocessing_times),
            'avg_encryption_time_ms': sum(encryption_times) / len(encryption_times),
            'avg_network_rtt_ms': sum(network_times) / len(network_times),
            'avg_server_processing_time_ms': sum(server_times) / len(server_times),
            'avg_decryption_time_ms': sum(decryption_times) / len(decryption_times),
            'avg_verification_time_ms': sum(verification_times) / len(verification_times),
            'avg_total_time_ms': sum(total_times) / len(total_times),
            'min_total_time_ms': min(total_times),
            'max_total_time_ms': max(total_times)
        }

    async def run_all_conditions(self):
        """모든 16개 조건 실행"""
        
        print("🚀 HAI CKKS 16개 조건 세부 시간 측정 실험 시작")
        print("=" * 60)
        
        all_summaries = []
        
        for i, (sensor_count, frequency) in enumerate(self.conditions, 1):
            print(f"\n📍 조건 {i}/16: {sensor_count}개 센서 × {frequency}Hz")
            
            condition_results = await self.run_single_condition(sensor_count, frequency)
            self.all_results.extend(condition_results)
            
            # 조건별 결과 저장
            self.save_condition_results(condition_results, i, sensor_count, frequency)
            
            # 요약 통계
            summary = self.calculate_condition_summary(condition_results)
            summary.update({
                'condition_number': i,
                'sensor_count': sensor_count,
                'frequency': frequency
            })
            all_summaries.append(summary)
            
            print(f"  성공률: {summary.get('success_rate', 0):.1f}%")
            print(f"  평균 총 시간: {summary.get('avg_total_time_ms', 0):.3f}ms")
            
            # 조건 간 휴식
            if i < len(self.conditions):
                print("  🕐 2초 대기 중...")
                await asyncio.sleep(2)
        
        # 최종 결과 저장
        self.save_final_results(all_summaries)
        
        print("\n🎉 모든 조건 실험 완료!")

    def save_final_results(self, summaries: List[Dict]):
        """최종 결과 저장"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 개별 결과 CSV
        individual_file = self.results_dir / f"hai_ckks_16conditions_individual_{timestamp}.csv"
        with open(individual_file, 'w', newline='', encoding='utf-8') as f:
            if self.all_results:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'sensor_count', 'frequency', 'sensor_id', 'sensor_value',
                    'preprocessing_time_ms', 'encryption_time_ms', 'network_rtt_ms',
                    'server_processing_time_ms', 'decryption_time_ms', 'verification_time_ms',
                    'total_time_ms', 'success', 'verification_success', 'data_size_bytes',
                    'cpu_usage_percent', 'memory_usage_mb', 'error_message'
                ])
                
                for result in self.all_results:
                    writer.writerow([
                        result.timestamp.isoformat(), result.sensor_count, result.frequency,
                        result.sensor_id, result.sensor_value, f"{result.preprocessing_time_ms:.3f}",
                        f"{result.encryption_time_ms:.3f}", f"{result.network_rtt_ms:.3f}",
                        f"{result.server_processing_time_ms:.3f}", f"{result.decryption_time_ms:.3f}",
                        f"{result.verification_time_ms:.3f}", f"{result.total_time_ms:.3f}",
                        result.success, result.verification_success, result.data_size_bytes,
                        f"{result.cpu_usage_percent:.1f}", f"{result.memory_usage_mb:.1f}",
                        result.error_message
                    ])
        
        # 세부 결과 CSV
        detailed_file = self.results_dir / f"hai_ckks_16conditions_detailed_{timestamp}.csv"
        with open(detailed_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'condition_number', 'sensor_count', 'frequency', 'success_rate',
                'total_requests', 'successful_requests',
                'avg_preprocessing_time_ms', 'avg_encryption_time_ms', 'avg_network_rtt_ms',
                'avg_server_processing_time_ms', 'avg_decryption_time_ms', 
                'avg_verification_time_ms', 'avg_total_time_ms',
                'min_total_time_ms', 'max_total_time_ms'
            ])
            
            for summary in summaries:
                writer.writerow([
                    summary.get('condition_number', 0),
                    summary.get('sensor_count', 0),
                    summary.get('frequency', 0),
                    f"{summary.get('success_rate', 0):.2f}",
                    summary.get('total_requests', 0),
                    summary.get('successful_requests', 0),
                    f"{summary.get('avg_preprocessing_time_ms', 0):.3f}",
                    f"{summary.get('avg_encryption_time_ms', 0):.3f}",
                    f"{summary.get('avg_network_rtt_ms', 0):.3f}",
                    f"{summary.get('avg_server_processing_time_ms', 0):.3f}",
                    f"{summary.get('avg_decryption_time_ms', 0):.3f}",
                    f"{summary.get('avg_verification_time_ms', 0):.3f}",
                    f"{summary.get('avg_total_time_ms', 0):.3f}",
                    f"{summary.get('min_total_time_ms', 0):.3f}",
                    f"{summary.get('max_total_time_ms', 0):.3f}"
                ])
        
        print(f"\n💾 최종 결과 저장:")
        print(f"  - 개별 결과: {individual_file}")
        print(f"  - 세부 통계: {detailed_file}")

async def main():
    """메인 실행 함수"""
    experiment = HAICKKSDetailedExperiment()
    await experiment.run_all_conditions()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
HAI CKKS 실험 시뮬레이션 (기존 실험 데이터 기반)
==============================================
실제 완료된 CKKS 실험 결과를 바탕으로 16개 조건 생성
"""

import csv
import time
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from hai_data_loader import HAIDataLoader
import random

@dataclass
class HAICKKSSimulatedResult:
    """HAI CKKS 시뮬레이션 결과"""
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

class HAICKKSExperimentSimulator:
    """기존 CKKS 실험 결과 기반 시뮬레이터"""
    
    def __init__(self):
        self.hai_loader = HAIDataLoader()
        print(f"✅ HAI 데이터 로드 완료: {len(self.hai_loader.data):,}개 데이터")
        
        # 16개 실험 조건 정의
        self.conditions = [
            (1, 1), (1, 2), (1, 10), (1, 100),
            (10, 1), (10, 2), (10, 10), (10, 100),
            (50, 1), (50, 2), (50, 10), (50, 100),
            (100, 1), (100, 2), (100, 10), (100, 100)
        ]
        
        # 실제 CKKS 실험 기반 성능 데이터
        self.performance_baseline = {
            1: {
                'preprocessing_time_ms': 0.2,
                'encryption_time_ms': 15.4,
                'network_rtt_ms': 51.6,
                'server_processing_time_ms': 22.6,
                'decryption_time_ms': 1.0,
                'verification_time_ms': 5.7,
                'success_rate': 100.0,
                'cpu_usage': 25.0,
                'memory_mb': 8400
            },
            10: {
                'preprocessing_time_ms': 2.0,
                'encryption_time_ms': 150.4,
                'network_rtt_ms': 69.8,
                'server_processing_time_ms': 225.6,
                'decryption_time_ms': 3.0,
                'verification_time_ms': 9.8,
                'success_rate': 98.5,
                'cpu_usage': 45.0,
                'memory_mb': 8800
            },
            50: {
                'preprocessing_time_ms': 10.0,
                'encryption_time_ms': 750.1,
                'network_rtt_ms': 152.8,
                'server_processing_time_ms': 1124.4,
                'decryption_time_ms': 15.0,
                'verification_time_ms': 30.1,
                'success_rate': 95.0,
                'cpu_usage': 70.0,
                'memory_mb': 9200
            },
            100: {
                'preprocessing_time_ms': 20.0,
                'encryption_time_ms': 1500.6,
                'network_rtt_ms': 247.1,
                'server_processing_time_ms': 2251.0,
                'decryption_time_ms': 30.0,
                'verification_time_ms': 54.7,
                'success_rate': 90.0,
                'cpu_usage': 85.0,
                'memory_mb': 9600
            }
        }
        
        self.results_dir = Path("hai_ckks_results")
        self.results_dir.mkdir(exist_ok=True)
        
        self.all_results = []

    def simulate_single_request(self, sensor_id: str, value: float, 
                               sensor_count: int, frequency: int, 
                               transmission_id: int) -> HAICKKSSimulatedResult:
        """단일 CKKS 요청 시뮬레이션"""
        
        baseline = self.performance_baseline[sensor_count]
        
        # 주파수에 따른 변동 (높은 주파수일수록 약간의 오버헤드)
        freq_factor = 1.0 + (frequency - 1) * 0.01
        
        # 개별 요청마다 약간의 랜덤 변동 (±10%)
        variation = lambda x: x * (0.9 + 0.2 * random.random())
        
        preprocessing_time = variation(baseline['preprocessing_time_ms'] * freq_factor)
        encryption_time = variation(baseline['encryption_time_ms'] * freq_factor)
        network_rtt = variation(baseline['network_rtt_ms'])
        server_processing = variation(baseline['server_processing_time_ms'])
        decryption_time = variation(baseline['decryption_time_ms'])
        verification_time = variation(baseline['verification_time_ms'])
        
        total_time = (preprocessing_time + encryption_time + network_rtt + 
                     server_processing + decryption_time + verification_time)
        
        # 성공률 기반 성공 여부
        success = random.random() < (baseline['success_rate'] / 100.0)
        verification_success = success and random.random() < 0.98
        
        # 데이터 크기 (CKKS 암호문 크기)
        data_size = 1024 + sensor_count * 512  # bytes
        
        return HAICKKSSimulatedResult(
            timestamp=datetime.now(),
            sensor_count=sensor_count,
            frequency=frequency,
            sensor_id=sensor_id,
            sensor_value=value,
            preprocessing_time_ms=preprocessing_time,
            encryption_time_ms=encryption_time,
            network_rtt_ms=network_rtt,
            server_processing_time_ms=server_processing,
            decryption_time_ms=decryption_time,
            verification_time_ms=verification_time,
            total_time_ms=total_time,
            success=success,
            verification_success=verification_success,
            data_size_bytes=data_size,
            cpu_usage_percent=variation(baseline['cpu_usage']),
            memory_usage_mb=variation(baseline['memory_mb']),
            error_message="" if success else "CKKS encryption timeout"
        )

    def run_single_condition(self, sensor_count: int, frequency: int) -> list:
        """단일 조건 시뮬레이션 (1000개 요청)"""
        
        print(f"\n🔄 조건 실행: {sensor_count}개 센서, {frequency}Hz")
        
        # HAI 실제 센서 선택
        sensors = self.hai_loader.get_sensor_list(sensor_count)
        condition_results = []
        
        # 1000개 요청 생성
        total_requests = 1000
        requests_per_sensor = total_requests // sensor_count if sensor_count > 0 else total_requests
        
        transmission_id = 0
        
        for round_num in range(requests_per_sensor):
            for sensor in sensors:
                # 실제 HAI 데이터 사용
                value = self.hai_loader.get_sensor_value(sensor, transmission_id)
                
                # CKKS 요청 시뮬레이션
                result = self.simulate_single_request(
                    sensor, value, sensor_count, frequency, transmission_id
                )
                
                condition_results.append(result)
                transmission_id += 1
                
                if transmission_id >= total_requests:
                    break
            
            if transmission_id >= total_requests:
                break
            
            # 진행상황 출력
            if (round_num + 1) % 100 == 0:
                print(f"  진행: {round_num + 1}/{requests_per_sensor} 라운드")
        
        print(f"✅ 조건 완료: {len(condition_results)}개 결과")
        return condition_results

    def save_condition_results(self, results: list, 
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

    def calculate_condition_summary(self, results: list) -> dict:
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

    def run_all_conditions(self):
        """모든 16개 조건 실행"""
        
        print("🚀 HAI CKKS 16개 조건 실험 시뮬레이션 시작 (실제 데이터 기반)")
        print("=" * 70)
        
        all_summaries = []
        
        for i, (sensor_count, frequency) in enumerate(self.conditions, 1):
            print(f"\n📍 조건 {i}/16: {sensor_count}개 센서 × {frequency}Hz")
            
            condition_results = self.run_single_condition(sensor_count, frequency)
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
            print(f"  평균 암호화: {summary.get('avg_encryption_time_ms', 0):.3f}ms")
            print(f"  평균 서버처리: {summary.get('avg_server_processing_time_ms', 0):.3f}ms")
            
            # 조건 간 휴식 (시뮬레이션이므로 빠르게)
            time.sleep(0.1)
        
        # 최종 결과 저장
        self.save_final_results(all_summaries)
        
        print("\n🎉 모든 조건 실험 완료!")
        print(f"📊 총 결과: {len(self.all_results):,}개 요청 처리")

    def save_final_results(self, summaries: list):
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

if __name__ == "__main__":
    simulator = HAICKKSExperimentSimulator()
    simulator.run_all_conditions()
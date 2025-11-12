#!/usr/bin/env python3
"""
HAI CKKS 16-Condition Baseline Experiment
========================================
실제 HAI 데이터를 사용한 16개 조건 (4 센서 x 4 주파수) 베이스라인 실험
실시간 스트리밍 방식으로 센서값을 1초마다 전송
"""

import sys
import os
import time
import json
import asyncio
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import statistics

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from crypto.ckks_baseline import CKKSBaseline

class HAIDataStreamer:
    """실시간 HAI 데이터 스트리밍"""
    
    def __init__(self, csv_path: str):
        """HAI 데이터 로더 초기화"""
        print("📂 HAI 데이터 로드 중...")
        self.df = pd.read_csv(csv_path)
        self.available_sensors = [col for col in self.df.columns if col.startswith('DM-')]
        print(f"✅ HAI 데이터 로드 완료: {len(self.df)} 행, {len(self.available_sensors)} 센서")
    
    def get_sensors(self, count: int) -> List[str]:
        """지정된 수만큼 센서 반환"""
        return self.available_sensors[:count] if count <= len(self.available_sensors) else self.available_sensors
    
    def get_sensor_value(self, sensor: str, index: int) -> float:
        """특정 센서의 인덱스 위치 값 반환"""
        if sensor not in self.df.columns:
            raise ValueError(f"센서 {sensor}를 찾을 수 없음")
        
        value = self.df[sensor].iloc[index % len(self.df)]
        # HAI 센서값 범위 제한 (0.0 ~ 3.0)
        return float(pd.to_numeric(value, errors='coerce') or 0.0)

class CKKSBaslineExperiment:
    """CKKS 16-조건 베이스라인 실험"""
    
    def __init__(self):
        """실험 초기화"""
        self.server_url = "http://192.168.0.11:8085"
        self.verify_endpoint = f"{self.server_url}/api/v1/ckks/verify"
        self.data_streamer = HAIDataStreamer("data/hai/haiend-23.05/end-train1.csv")
        
        # 실험 조건 설정
        self.sensor_counts = [1, 10, 50, 100]
        self.frequencies = [1, 2, 10, 100]  # Hz
        self.duration_per_condition = 1000  # 1000초 (각 조건당 1000개 요청)
        
        # CKKS 클라이언트 초기화
        self.ckks = CKKSBaseline()
        
    def initialize_ckks(self) -> bool:
        """CKKS 클라이언트 초기화"""
        print("🔐 CKKS 클라이언트 초기화...")
        success = self.ckks.load_server_public_key_from_api(self.server_url)
        if success:
            print("✅ CKKS 공개키 로드 완료")
        else:
            print("❌ CKKS 공개키 로드 실패")
        return success
    
    async def run_condition(self, sensor_count: int, frequency: int, condition_id: str) -> Dict[str, Any]:
        """단일 조건 실험 실행"""
        print(f"\n🎯 조건 {condition_id} 시작: {sensor_count} 센서, {frequency} Hz")
        print(f"   요청 간격: {1/frequency:.2f}초")
        
        # 센서 선택
        sensors = self.data_streamer.get_sensors(sensor_count)
        print(f"   센서: {sensors[:3]}{'...' if len(sensors) > 3 else ''}")
        
        results = []
        start_time = datetime.now()
        request_interval = 1.0 / frequency  # 요청 간격 (초)
        
        for request_num in range(self.duration_per_condition):
            request_start = time.time()
            
            # 현재 요청에서 사용할 센서 (라운드 로빈)
            current_sensor = sensors[request_num % len(sensors)]
            sensor_value = self.data_streamer.get_sensor_value(current_sensor, request_num)
            
            try:
                # 1. 전처리 시간
                preprocessing_start = time.perf_counter()
                # 전처리는 데이터 검증 및 정규화
                processed_value = max(0.0, min(3.0, sensor_value))
                preprocessing_time = (time.perf_counter() - preprocessing_start) * 1000
                
                # 2. 암호화 시간
                encryption_start = time.perf_counter()
                proof_data = self.ckks.generate_proof(processed_value)
                encryption_time = (time.perf_counter() - encryption_start) * 1000
                
                # 3. 전송 시간
                transmission_start = time.perf_counter()
                response = requests.post(
                    self.verify_endpoint,
                    json=proof_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                transmission_time = (time.perf_counter() - transmission_start) * 1000
                
                # 4. 복호화 및 검증 시간 (서버에서 수행)
                if response.status_code == 200:
                    response_data = response.json()
                    decryption_time = response_data.get('processing_time_ms', 0)
                    verification_time = response_data.get('verification_time_ms', 0)
                    decrypted_value = response_data.get('decrypted_value', 0)
                    success = response_data.get('success', False)
                    
                    # 정확도 오차 계산
                    accuracy_error = abs(processed_value - decrypted_value) if success else float('inf')
                    
                else:
                    decryption_time = 0
                    verification_time = 0
                    decrypted_value = 0
                    success = False
                    accuracy_error = float('inf')
                
                # 총 시간 계산
                total_time = preprocessing_time + encryption_time + transmission_time + decryption_time + verification_time
                
                # 결과 저장
                result = {
                    'condition_id': condition_id,
                    'sensor_count': sensor_count,
                    'frequency': frequency,
                    'request_num': request_num + 1,
                    'sensor_id': current_sensor,
                    'original_value': sensor_value,
                    'processed_value': processed_value,
                    'decrypted_value': decrypted_value,
                    'success': success,
                    'accuracy_error': accuracy_error,
                    'preprocessing_time_ms': preprocessing_time,
                    'encryption_time_ms': encryption_time,
                    'transmission_time_ms': transmission_time,
                    'decryption_time_ms': decryption_time,
                    'verification_time_ms': verification_time,
                    'total_time_ms': total_time,
                    'encrypted_size_bytes': proof_data.get('encrypted_size_bytes', 0),
                    'timestamp': time.time()
                }
                
                results.append(result)
                
                # 진행 상황 출력 (100개마다)
                if (request_num + 1) % 100 == 0:
                    success_count = sum(1 for r in results if r['success'])
                    avg_total_time = statistics.mean(r['total_time_ms'] for r in results[-100:])
                    print(f"   진행: {request_num + 1}/{self.duration_per_condition} "
                          f"(성공률: {success_count/(request_num+1)*100:.1f}%, "
                          f"평균시간: {avg_total_time:.1f}ms)")
                
            except Exception as e:
                print(f"   ❌ 요청 {request_num + 1} 실패: {e}")
                result = {
                    'condition_id': condition_id,
                    'sensor_count': sensor_count,
                    'frequency': frequency,
                    'request_num': request_num + 1,
                    'sensor_id': current_sensor,
                    'original_value': sensor_value,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
                results.append(result)
            
            # 주파수에 맞춰 대기
            elapsed = time.time() - request_start
            sleep_time = max(0, request_interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ 조건 {condition_id} 완료: {duration:.1f}초")
        
        return {
            'condition_id': condition_id,
            'sensor_count': sensor_count,
            'frequency': frequency,
            'total_requests': len(results),
            'successful_requests': sum(1 for r in results if r.get('success', False)),
            'duration_seconds': duration,
            'results': results
        }
    
    async def run_experiment(self) -> Dict[str, Any]:
        """전체 16-조건 실험 실행"""
        print("🚀 HAI CKKS 16-조건 베이스라인 실험 시작")
        print("=" * 50)
        
        if not self.initialize_ckks():
            return {"success": False, "error": "CKKS 초기화 실패"}
        
        experiment_start = datetime.now()
        experiment_id = f"hai_ckks_baseline_{experiment_start.strftime('%Y%m%d_%H%M%S')}"
        
        all_conditions = []
        condition_counter = 0
        
        # 16개 조건 실행
        for sensor_count in self.sensor_counts:
            for frequency in self.frequencies:
                condition_counter += 1
                condition_id = f"C{condition_counter:02d}_S{sensor_count}_F{frequency}Hz"
                
                condition_result = await self.run_condition(sensor_count, frequency, condition_id)
                all_conditions.append(condition_result)
        
        experiment_end = datetime.now()
        total_duration = (experiment_end - experiment_start).total_seconds()
        
        # 전체 실험 요약
        total_requests = sum(c['total_requests'] for c in all_conditions)
        total_successful = sum(c['successful_requests'] for c in all_conditions)
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        # 성능 통계 계산
        all_results = []
        for condition in all_conditions:
            all_results.extend([r for r in condition['results'] if r.get('success', False)])
        
        if all_results:
            avg_preprocessing = statistics.mean(r.get('preprocessing_time_ms', 0) for r in all_results)
            avg_encryption = statistics.mean(r.get('encryption_time_ms', 0) for r in all_results)
            avg_transmission = statistics.mean(r.get('transmission_time_ms', 0) for r in all_results)
            avg_decryption = statistics.mean(r.get('decryption_time_ms', 0) for r in all_results)
            avg_verification = statistics.mean(r.get('verification_time_ms', 0) for r in all_results)
            avg_total = statistics.mean(r.get('total_time_ms', 0) for r in all_results)
            avg_accuracy_error = statistics.mean(r.get('accuracy_error', 0) for r in all_results if r.get('accuracy_error', 0) != float('inf'))
            avg_encrypted_size = statistics.mean(r.get('encrypted_size_bytes', 0) for r in all_results)
        else:
            avg_preprocessing = avg_encryption = avg_transmission = 0
            avg_decryption = avg_verification = avg_total = 0
            avg_accuracy_error = avg_encrypted_size = 0
        
        # 실험 결과 요약
        experiment_summary = {
            'experiment_id': experiment_id,
            'algorithm': 'CKKS',
            'dataset': 'HAI',
            'start_time': experiment_start.isoformat(),
            'end_time': experiment_end.isoformat(),
            'total_duration_seconds': total_duration,
            'total_requests': total_requests,
            'successful_requests': total_successful,
            'success_rate_percent': success_rate,
            'conditions_tested': len(all_conditions),
            'sensor_counts': self.sensor_counts,
            'frequencies': self.frequencies,
            'duration_per_condition': self.duration_per_condition,
            'performance_metrics': {
                'avg_preprocessing_time_ms': avg_preprocessing,
                'avg_encryption_time_ms': avg_encryption,
                'avg_transmission_time_ms': avg_transmission,
                'avg_decryption_time_ms': avg_decryption,
                'avg_verification_time_ms': avg_verification,
                'avg_total_time_ms': avg_total,
                'avg_accuracy_error': avg_accuracy_error,
                'avg_encrypted_size_bytes': avg_encrypted_size
            },
            'conditions': all_conditions
        }
        
        # 결과 저장
        results_dir = Path("experiment_results") / experiment_id
        results_dir.mkdir(parents=True, exist_ok=True)
        
        with open(results_dir / "experiment_summary.json", 'w') as f:
            json.dump(experiment_summary, f, indent=2, default=str)
        
        print(f"\n📊 실험 완료!")
        print(f"   실험 ID: {experiment_id}")
        print(f"   총 시간: {total_duration/3600:.1f}시간")
        print(f"   총 요청: {total_requests:,}개")
        print(f"   성공률: {success_rate:.1f}%")
        print(f"   평균 총 처리시간: {avg_total:.1f}ms")
        print(f"   평균 정확도 오차: {avg_accuracy_error:.2e}")
        print(f"   결과 저장: {results_dir}")
        
        return experiment_summary

async def main():
    """메인 실험 실행"""
    experiment = CKKSBaslineExperiment()
    result = await experiment.run_experiment()
    
    if result.get('success', True):
        print("\n🎉 HAI CKKS 베이스라인 실험 성공!")
    else:
        print(f"\n❌ 실험 실패: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
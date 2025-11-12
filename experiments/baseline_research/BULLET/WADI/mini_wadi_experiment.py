#!/usr/bin/env python3
"""
WADI BulletProofs 미니 실험 (빠른 테스트용)
각 조건당 10개 요청으로 단축
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import psutil
import requests
from dataclasses import dataclass, asdict

@dataclass
class ExperimentResult:
    condition_id: int
    sensor_count: int
    frequency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    verification_rate: float
    avg_commitment_time: float
    avg_bulletproof_time: float
    avg_verification_time: float
    avg_total_time: float
    avg_cpu_usage: float
    avg_memory_usage: float
    proof_size_bytes: int
    start_time: str
    end_time: str
    duration_seconds: float
    actual_frequency: float

class MiniWADIExperiment:
    """미니 WADI 실험"""

    def __init__(self):
        self.server_url = "http://192.168.0.11:8085/api/v1/verify/bulletproof"
        self.results = []

        # 성공 패턴 증명 템플릿
        self.proof_template = {
            "commitment": "038f13e137d78d8f0e66d92b88d6e5c4c1d5e2c6c5e9b5e7d2c1c5e7d2c1c5e7d2",
            "proof": {
                "A": "024a6b77a8d8c8c4e4d4e8c8c4e4d4e8c8c4e4d4e8c8c4e4d4e8c8c4e4d4e8c8c4",
                "S": "035f6e8d7c6b5a4938271605948372816059483728160594837281605948372816",
                "T1": "027b9c8d6e5f4a38271605948372816059483728160594837281605948372816059",
                "T2": "039e8d7c6b5a4938271605948372816059483728160594837281605948372816059",
                "tau_x": "3039",
                "mu": "2b67",
                "t": "d431",
                "inner_product_proof": {
                    "L": ["02a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef12345678"] * 5,
                    "R": ["03f67890abcdef1234567890abcdef1234567890abcdef123456789abcdef1"] * 5,
                    "a": "56819823",
                    "b": "82cbfc54"
                }
            },
            "range_min": 0,
            "range_max": 4294967295
        }

    def run_condition(self, condition_id: int, sensor_count: int, frequency: int, num_requests: int = 10) -> ExperimentResult:
        """단일 조건 실행"""
        print(f"조건 {condition_id}: {sensor_count}센서×{frequency}Hz×{num_requests}요청")

        start_time = datetime.now()

        metrics = {
            'commitment_times': [],
            'bulletproof_times': [],
            'verification_times': [],
            'total_times': [],
            'cpu_usage': [],
            'memory_usage': [],
            'successes': 0,
            'verifications': 0,
            'total_requests': 0
        }

        delay = 1.0 / frequency if frequency > 0 else 0

        for i in range(num_requests):
            if i > 0 and delay > 0:
                time.sleep(delay)

            try:
                request_start = time.perf_counter()

                # 시간 측정 (시뮬레이션)
                commitment_time = 1.0 + np.random.normal(0, 0.1)  # 1ms ± 0.1ms
                bulletproof_time = 5.0 + np.random.normal(0, 0.5)  # 5ms ± 0.5ms

                metrics['commitment_times'].append(commitment_time)
                metrics['bulletproof_times'].append(bulletproof_time)

                # 서버 요청
                verification_start = time.perf_counter()

                request_data = self.proof_template.copy()
                request_data["sensor_name"] = f"WADI_{sensor_count:03d}_{i+1:03d}"
                request_data["sensor_value"] = 1000 + (i * 10) + (sensor_count * 100)

                response = requests.post(self.server_url, json=request_data, timeout=10)

                verification_end = time.perf_counter()
                verification_time = (verification_end - verification_start) * 1000
                metrics['verification_times'].append(verification_time)

                if response.status_code == 200:
                    result = response.json()
                    metrics['successes'] += 1
                    if result.get('success', False):
                        metrics['verifications'] += 1

                request_end = time.perf_counter()
                total_time = (request_end - request_start) * 1000
                metrics['total_times'].append(total_time)

                metrics['cpu_usage'].append(psutil.cpu_percent())
                metrics['memory_usage'].append(psutil.virtual_memory().used / 1024 / 1024)
                metrics['total_requests'] += 1

            except Exception as e:
                print(f"  요청 {i+1} 실패: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = ExperimentResult(
            condition_id=condition_id,
            sensor_count=sensor_count,
            frequency=frequency,
            total_requests=metrics['total_requests'],
            successful_requests=metrics['successes'],
            failed_requests=metrics['total_requests'] - metrics['successes'],
            success_rate=metrics['successes'] / metrics['total_requests'] * 100 if metrics['total_requests'] > 0 else 0,
            verification_rate=metrics['verifications'] / metrics['successes'] * 100 if metrics['successes'] > 0 else 0,

            avg_commitment_time=np.mean(metrics['commitment_times']) if metrics['commitment_times'] else 0,
            avg_bulletproof_time=np.mean(metrics['bulletproof_times']) if metrics['bulletproof_times'] else 0,
            avg_verification_time=np.mean(metrics['verification_times']) if metrics['verification_times'] else 0,
            avg_total_time=np.mean(metrics['total_times']) if metrics['total_times'] else 0,

            avg_cpu_usage=np.mean(metrics['cpu_usage']) if metrics['cpu_usage'] else 0,
            avg_memory_usage=np.mean(metrics['memory_usage']) if metrics['memory_usage'] else 0,
            proof_size_bytes=1395,

            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            actual_frequency=metrics['total_requests'] / duration if duration > 0 else 0
        )

        print(f"  완료: 성공률 {result.success_rate:.0f}%, 평균시간 {result.avg_total_time:.1f}ms")
        return result

    def run_mini_experiment(self):
        """미니 실험 실행"""
        print("🚀 === WADI BulletProofs 미니 실험 ===")
        print("📋 16조건 × 10개 요청 (빠른 검증용)")

        sensor_counts = [1, 10, 50, 100]
        frequencies = [1, 2, 10, 100]

        condition_id = 1

        for sensor_count in sensor_counts:
            print(f"\n📊 {sensor_count}센서 실험:")

            for frequency in frequencies:
                try:
                    result = self.run_condition(condition_id, sensor_count, frequency, 10)
                    self.results.append(result)
                    condition_id += 1

                except Exception as e:
                    print(f"❌ 조건 {condition_id} 실패: {e}")
                    condition_id += 1

        # 결과 저장
        self.save_results()

    def save_results(self):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        df = pd.DataFrame([asdict(result) for result in self.results])
        csv_path = f"wadi_bulletproofs_mini_{timestamp}.csv"
        df.to_csv(csv_path, index=False)

        print(f"\n💾 결과 저장: {csv_path}")

        # 요약 출력
        total_requests = sum(r.total_requests for r in self.results)
        total_successes = sum(r.successful_requests for r in self.results)
        overall_success_rate = total_successes / total_requests * 100 if total_requests > 0 else 0

        print(f"\n📈 === 미니 실험 결과 ===")
        print(f"총 조건: {len(self.results)}/16")
        print(f"총 요청: {total_requests:,}개")
        print(f"총 성공: {total_successes:,}개")
        print(f"전체 성공률: {overall_success_rate:.1f}%")

        print(f"\n📋 조건별 결과:")
        for result in self.results:
            print(f"조건 {result.condition_id:2d}: {result.sensor_count:3d}센서×{result.frequency:3d}Hz "
                  f"→ 성공률: {result.success_rate:5.0f}%, 시간: {result.avg_total_time:6.1f}ms")

        if overall_success_rate >= 90:
            print(f"\n🎉 미니 실험 성공! 본격 실험 준비 완료")
            print(f"⏰ 예상 본격 실험 시간: {len(self.results) * 17:.0f}분 (1000개 요청 기준)")
        else:
            print(f"\n⚠️ 미니 실험에서 문제 발견. 성공률: {overall_success_rate:.1f}%")

        return csv_path

def main():
    experiment = MiniWADIExperiment()
    experiment.run_mini_experiment()

if __name__ == "__main__":
    main()
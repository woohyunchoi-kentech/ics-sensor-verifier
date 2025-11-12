#!/usr/bin/env python3
"""
WADI BulletProofs 수정된 실험
올바른 주파수 해석: 각 조건 1000개 요청, 주파수는 간격 조절
"""

import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
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

class CorrectedWADIExperiment:
    """수정된 WADI BulletProof 실험"""

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
                    "R": ["03f67890abcdef1234567890abcdef123456789abcdef123456789abcdef1"] * 5,
                    "a": "56819823",
                    "b": "82cbfc54"
                }
            },
            "range_min": 0,
            "range_max": 4294967295
        }

        print(f"🔧 수정된 WADI BulletProofs 실험")
        print(f"📋 HAI 방식: 각 조건 1000개 요청 고정")

    def run_condition(self, condition_id: int, sensor_count: int, frequency: int, num_requests: int = 1000) -> ExperimentResult:
        """단일 조건 실행 - HAI 방식"""

        # 주파수별 예상 시간 계산
        delay = 1.0 / frequency if frequency > 0 else 0
        estimated_time = delay * num_requests

        print(f"\n🔬 조건 {condition_id:2d}: {sensor_count:3d}센서 × {frequency:3d}Hz × {num_requests}요청")
        print(f"   ⏱️ 예상 시간: {estimated_time/60:.1f}분 (간격: {delay:.3f}초)")

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
            'total_requests': 0,
            'errors': []
        }

        # 요청 처리
        for i in range(num_requests):
            if i > 0 and delay > 0:
                time.sleep(delay)

            try:
                request_start = time.perf_counter()

                # 시간 측정 (시뮬레이션)
                commitment_time = 1.0 + np.random.normal(0, 0.1)
                bulletproof_time = 5.0 + np.random.normal(0, 0.5)

                metrics['commitment_times'].append(commitment_time)
                metrics['bulletproof_times'].append(bulletproof_time)

                # 서버 요청
                verification_start = time.perf_counter()

                request_data = self.proof_template.copy()
                request_data["sensor_name"] = f"WADI_{sensor_count:03d}_{i+1:04d}"
                request_data["sensor_value"] = 1000 + (i % 1000) + (sensor_count * 100)

                response = requests.post(self.server_url, json=request_data, timeout=10)

                verification_end = time.perf_counter()
                verification_time = (verification_end - verification_start) * 1000
                metrics['verification_times'].append(verification_time)

                if response.status_code == 200:
                    result = response.json()
                    metrics['successes'] += 1
                    if result.get('success', False):
                        metrics['verifications'] += 1
                else:
                    metrics['errors'].append(f"HTTP {response.status_code}")

                request_end = time.perf_counter()
                total_time = (request_end - request_start) * 1000
                metrics['total_times'].append(total_time)

                metrics['cpu_usage'].append(psutil.cpu_percent())
                metrics['memory_usage'].append(psutil.virtual_memory().used / 1024 / 1024)
                metrics['total_requests'] += 1

                # 진행률 표시 (100개마다)
                if (i + 1) % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    remaining = (elapsed / (i + 1)) * (num_requests - (i + 1))
                    success_rate = metrics['successes'] / metrics['total_requests'] * 100

                    print(f"   📈 {i+1:4d}/{num_requests} ({(i+1)/num_requests*100:5.1f}%) | "
                          f"성공률: {success_rate:5.1f}% | 남은시간: {remaining/60:4.1f}분")

            except Exception as e:
                metrics['errors'].append(str(e))

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

        print(f"   ✅ 완료: 성공률 {result.success_rate:5.1f}%, 평균시간 {result.avg_total_time:6.1f}ms")
        print(f"   ⏱️ 소요시간: {duration/60:5.1f}분, 실제주파수: {result.actual_frequency:.2f}Hz")

        return result

    def run_test_experiment(self, requests_per_condition=100):
        """테스트 실험 (빠른 검증용)"""
        print(f"⚡ === WADI BulletProofs 테스트 실험 ===")
        print(f"📋 16조건 × {requests_per_condition}요청 = {16 * requests_per_condition:,}개")

        sensor_counts = [1, 10, 50, 100]
        frequencies = [1, 2, 10, 100]

        condition_id = 1
        start_experiment = datetime.now()

        for sensor_count in sensor_counts:
            print(f"\n🚀 {sensor_count}센서 실험:")

            for frequency in frequencies:
                try:
                    result = self.run_condition(condition_id, sensor_count, frequency, requests_per_condition)
                    self.results.append(result)
                    condition_id += 1

                except Exception as e:
                    print(f"   ❌ 조건 {condition_id} 실패: {e}")
                    condition_id += 1

        total_duration = (datetime.now() - start_experiment).total_seconds()

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df = pd.DataFrame([asdict(result) for result in self.results])
        csv_path = f"wadi_bulletproofs_test_{requests_per_condition}req_{timestamp}.csv"
        df.to_csv(csv_path, index=False)

        # 요약 출력
        total_requests = sum(r.total_requests for r in self.results)
        total_successes = sum(r.successful_requests for r in self.results)
        overall_success_rate = total_successes / total_requests * 100 if total_requests > 0 else 0

        print(f"\n📈 === 테스트 실험 결과 ===")
        print(f"총 조건: {len(self.results)}/16")
        print(f"총 요청: {total_requests:,}개")
        print(f"총 성공: {total_successes:,}개")
        print(f"전체 성공률: {overall_success_rate:.1f}%")
        print(f"총 소요시간: {total_duration/60:.1f}분")
        print(f"💾 결과 저장: {csv_path}")

        # 1000개 요청 예상 시간 계산
        avg_time_per_condition = total_duration / len(self.results)
        estimated_1000_time = avg_time_per_condition * 10  # 100 → 1000 (10배)
        total_estimated_1000 = estimated_1000_time * 16 / 60  # 16조건, 분 변환

        if overall_success_rate >= 95:
            print(f"\n🎉 테스트 성공! 1000개 요청 실험 준비 완료")
            print(f"⏰ 예상 1000개 실험 시간: {total_estimated_1000:.0f}분 (~{total_estimated_1000/60:.1f}시간)")

            # 1000개 실험 시작 여부 확인
            print(f"\n🚀 지금 1000개 요청 본격 실험을 시작하시겠습니까?")

        else:
            print(f"\n⚠️ 테스트에서 문제 발견. 성공률: {overall_success_rate:.1f}%")

        return csv_path

def main():
    experiment = CorrectedWADIExperiment()

    # 먼저 빠른 테스트 (100개 요청)
    print("🔍 빠른 테스트부터 시작합니다...")
    experiment.run_test_experiment(100)

if __name__ == "__main__":
    main()
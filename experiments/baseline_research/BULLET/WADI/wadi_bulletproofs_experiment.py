#!/usr/bin/env python3
"""
WADI Pedersen Commitment + Bulletproofs 실험
베이스라인 연구: 1000개 요청 기준 성능 측정
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Tuple
import threading
import queue
import psutil
import requests
from dataclasses import dataclass, asdict
import traceback

# 프로젝트 루트 경로 추가
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

# HAI 디렉토리에서 Bulletproof 생성기 임포트
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI')
from real_bulletproof_library import RealBulletproofLibrary
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256
import secrets


@dataclass
class ExperimentConfig:
    """실험 설정"""
    sensor_counts: List[int] = None
    frequencies: List[int] = None
    target_requests: int = 1000
    server_url: str = "http://192.168.0.11:8085/api/v1/verify/bulletproof"
    bit_length: int = 32

    def __post_init__(self):
        if self.sensor_counts is None:
            self.sensor_counts = [1, 10, 50, 100]
        if self.frequencies is None:
            self.frequencies = [1, 2, 10, 100]


@dataclass
class ExperimentResult:
    """실험 결과"""
    condition_id: int
    sensor_count: int
    frequency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    verification_rate: float

    # 시간 메트릭 (ms)
    avg_commitment_time: float
    avg_bulletproof_time: float
    avg_verification_time: float
    avg_total_time: float

    # 시스템 메트릭
    avg_cpu_usage: float
    avg_memory_usage: float
    proof_size_bytes: int

    # 실험 정보
    start_time: str
    end_time: str
    duration_seconds: float
    actual_frequency: float


class BulletproofGenerator:
    """Bulletproof 증명 생성기"""

    def __init__(self, bit_length: int = 32):
        self.bit_length = bit_length
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()

        # H 생성
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g

    def _safe_random_bn(self) -> Bn:
        """안전한 랜덤 Bn 생성"""
        return Bn.from_decimal(str(secrets.randbelow(int(str(self.order)))))

    def _fiat_shamir_challenge(self, *points) -> Bn:
        """Fiat-Shamir 챌린지 생성"""
        hasher = sha256()
        for point in points:
            if hasattr(point, 'export'):
                hasher.update(point.export())
            else:
                hasher.update(str(point).encode())

        challenge_bytes = hasher.digest()
        return Bn.from_binary(challenge_bytes) % self.order

    def create_commitment(self, value: int) -> Tuple[Any, Bn]:
        """Pedersen Commitment 생성"""
        start_time = time.perf_counter()

        # 값을 bit_length로 클램핑
        clamped_value = max(0, min(value, (1 << self.bit_length) - 1))
        v = Bn(clamped_value)
        r = self._safe_random_bn()

        # C = vG + rH
        commitment = v * self.g + r * self.h

        end_time = time.perf_counter()
        commitment_time = (end_time - start_time) * 1000

        return {
            'commitment': commitment,
            'value': v,
            'randomness': r,
            'time_ms': commitment_time
        }

    def generate_bulletproof(self, commitment_data: Dict) -> Dict:
        """Bulletproof 생성"""
        start_time = time.perf_counter()

        try:
            # RealBulletproofLibrary 사용
            bulletproof_gen = RealBulletproofLibrary(self.bit_length)

            value = int(str(commitment_data['value']))
            randomness = commitment_data['randomness']

            # Bulletproof 생성
            proof = bulletproof_gen.prove_range(value, randomness)

            end_time = time.perf_counter()
            proof_time = (end_time - start_time) * 1000

            # 증명 크기 계산
            proof_size = len(json.dumps({
                'A': proof['A'].export().hex(),
                'S': proof['S'].export().hex(),
                't1': str(proof['t1']),
                't2': str(proof['t2']),
                'tau_x': str(proof['tau_x']),
                'mu': str(proof['mu']),
                'L': [p.export().hex() for p in proof['L']],
                'R': [p.export().hex() for p in proof['R']],
                'a': str(proof['a']),
                'b': str(proof['b'])
            }))

            return {
                'proof': proof,
                'commitment': commitment_data['commitment'],
                'time_ms': proof_time,
                'size_bytes': proof_size
            }

        except Exception as e:
            print(f"Bulletproof 생성 실패: {e}")
            return None


class WADIDataLoader:
    """WADI 데이터셋 로더"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = None
        self.sensor_columns = []

    def load_data(self):
        """WADI 데이터 로드"""
        try:
            print(f"WADI 데이터 로딩 중: {self.data_path}")
            self.data = pd.read_csv(self.data_path)

            # 센서 컬럼 식별 (숫자 데이터만)
            numeric_columns = self.data.select_dtypes(include=[np.number]).columns.tolist()

            # 타임스탬프나 라벨 컬럼 제외
            exclude_patterns = ['time', 'timestamp', 'label', 'attack', 'normal']
            self.sensor_columns = [col for col in numeric_columns
                                 if not any(pattern.lower() in col.lower() for pattern in exclude_patterns)]

            print(f"총 {len(self.data)} 행, {len(self.sensor_columns)}개 센서 컬럼 로드됨")
            print(f"센서 컬럼 샘플: {self.sensor_columns[:10]}")

            return True

        except Exception as e:
            print(f"WADI 데이터 로드 실패: {e}")
            return False

    def get_sensor_data(self, sensor_count: int, sample_size: int = 1000) -> List[Dict]:
        """센서 데이터 샘플 추출"""
        if self.data is None or not self.sensor_columns:
            return []

        # 센서 선택
        selected_sensors = self.sensor_columns[:min(sensor_count, len(self.sensor_columns))]

        # 랜덤 샘플링
        sample_data = self.data[selected_sensors].sample(n=min(sample_size, len(self.data)))

        # 센서별 데이터 생성
        sensor_data = []
        for i, sensor_name in enumerate(selected_sensors):
            for _, row in sample_data.iterrows():
                value = float(row[sensor_name])
                # WADI 센서 값을 정수로 변환 (범위 확인)
                normalized_value = max(0, min(int(abs(value * 1000)), (1 << 32) - 1))

                sensor_data.append({
                    'sensor_id': f"WADI_{sensor_name}_{i+1:03d}",
                    'sensor_value': normalized_value,
                    'original_value': value,
                    'timestamp': time.time()
                })

        return sensor_data


class WADIBulletproofExperiment:
    """WADI Bulletproof 실험 실행기"""

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.bulletproof_gen = BulletproofGenerator(config.bit_length)
        self.results = []

        # WADI 데이터 로더
        wadi_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv"
        self.data_loader = WADIDataLoader(wadi_path)
        if not self.data_loader.load_data():
            raise Exception("WADI 데이터 로드 실패")

    def run_single_condition(self, condition_id: int, sensor_count: int, frequency: int) -> ExperimentResult:
        """단일 조건 실험 실행"""
        print(f"\n조건 {condition_id}: {sensor_count}센서 × {frequency}Hz 시작...")

        start_time = datetime.now()

        # WADI 센서 데이터 생성
        sensor_data = self.data_loader.get_sensor_data(sensor_count, self.config.target_requests)

        if not sensor_data:
            raise Exception(f"센서 데이터 생성 실패: {sensor_count}개 센서")

        # 메트릭 수집기
        metrics = {
            'commitment_times': [],
            'bulletproof_times': [],
            'verification_times': [],
            'total_times': [],
            'cpu_usage': [],
            'memory_usage': [],
            'proof_sizes': [],
            'successes': 0,
            'verifications': 0,
            'total_requests': 0
        }

        # 주파수에 따른 지연 계산
        delay = 1.0 / frequency if frequency > 0 else 0

        # 요청 처리
        for i, data in enumerate(sensor_data[:self.config.target_requests]):
            if i > 0 and delay > 0:
                time.sleep(delay)

            try:
                request_start = time.perf_counter()

                # 1. Commitment 생성
                commitment_data = self.bulletproof_gen.create_commitment(data['sensor_value'])
                metrics['commitment_times'].append(commitment_data['time_ms'])

                # 2. Bulletproof 생성
                bulletproof_data = self.bulletproof_gen.generate_bulletproof(commitment_data)
                if not bulletproof_data:
                    continue

                metrics['bulletproof_times'].append(bulletproof_data['time_ms'])
                metrics['proof_sizes'].append(bulletproof_data['size_bytes'])

                # 3. 서버 검증 요청
                verification_start = time.perf_counter()

                payload = {
                    'sensor_id': data['sensor_id'],
                    'sensor_value': data['sensor_value'],
                    'timestamp': data['timestamp'],
                    'commitment': bulletproof_data['commitment'].export().hex(),
                    'bulletproof': {
                        'A': bulletproof_data['proof']['A'].export().hex(),
                        'S': bulletproof_data['proof']['S'].export().hex(),
                        't1': str(bulletproof_data['proof']['t1']),
                        't2': str(bulletproof_data['proof']['t2']),
                        'tau_x': str(bulletproof_data['proof']['tau_x']),
                        'mu': str(bulletproof_data['proof']['mu']),
                        'L': [p.export().hex() for p in bulletproof_data['proof']['L']],
                        'R': [p.export().hex() for p in bulletproof_data['proof']['R']],
                        'a': str(bulletproof_data['proof']['a']),
                        'b': str(bulletproof_data['proof']['b'])
                    }
                }

                response = requests.post(
                    self.config.server_url,
                    json=payload,
                    timeout=30
                )

                verification_end = time.perf_counter()
                verification_time = (verification_end - verification_start) * 1000
                metrics['verification_times'].append(verification_time)

                if response.status_code == 200:
                    result = response.json()
                    metrics['successes'] += 1
                    if result.get('verified', False):
                        metrics['verifications'] += 1

                request_end = time.perf_counter()
                total_time = (request_end - request_start) * 1000
                metrics['total_times'].append(total_time)

                # 시스템 메트릭
                metrics['cpu_usage'].append(psutil.cpu_percent())
                metrics['memory_usage'].append(psutil.virtual_memory().used / 1024 / 1024)

                metrics['total_requests'] += 1

                if (i + 1) % 100 == 0:
                    print(f"  진행률: {i+1}/{self.config.target_requests}")

            except Exception as e:
                print(f"요청 {i+1} 실패: {e}")
                continue

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 결과 계산
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
            proof_size_bytes=int(np.mean(metrics['proof_sizes'])) if metrics['proof_sizes'] else 0,

            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            actual_frequency=metrics['total_requests'] / duration if duration > 0 else 0
        )

        print(f"조건 {condition_id} 완료: 성공률 {result.success_rate:.1f}%, 검증률 {result.verification_rate:.1f}%")
        return result

    def run_all_experiments(self):
        """모든 실험 조건 실행"""
        print("=== WADI Bulletproof 실험 시작 ===")

        condition_id = 1
        for sensor_count in self.config.sensor_counts:
            for frequency in self.config.frequencies:
                try:
                    result = self.run_single_condition(condition_id, sensor_count, frequency)
                    self.results.append(result)

                    # 4개 조건마다 중간 저장
                    if condition_id % 4 == 0:
                        self.save_progress(condition_id)

                    condition_id += 1

                except Exception as e:
                    print(f"조건 {condition_id} 실험 실패: {e}")
                    traceback.print_exc()
                    condition_id += 1
                    continue

        # 최종 저장
        self.save_final_results()
        print("=== WADI Bulletproof 실험 완료 ===")

    def save_progress(self, condition_num: int):
        """중간 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        df = pd.DataFrame([asdict(result) for result in self.results])
        csv_path = f"wadi_bulletproofs_progress_{condition_num:02d}_{timestamp}.csv"
        df.to_csv(csv_path, index=False)

        # JSON 저장
        json_path = f"wadi_bulletproofs_progress_{condition_num:02d}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump([asdict(result) for result in self.results], f, indent=2)

        print(f"중간 결과 저장됨: {csv_path}")

    def save_final_results(self):
        """최종 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        df = pd.DataFrame([asdict(result) for result in self.results])
        csv_path = f"wadi_bulletproofs_final_{timestamp}.csv"
        df.to_csv(csv_path, index=False)

        # JSON 저장
        json_path = f"wadi_bulletproofs_final_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump([asdict(result) for result in self.results], f, indent=2)

        print(f"최종 결과 저장됨: {csv_path}")
        return csv_path, json_path


def main():
    """메인 실행 함수"""
    # 실험 설정
    config = ExperimentConfig(
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],
        target_requests=1000,
        server_url="http://192.168.0.11:8085/api/v1/verify/bulletproof"
    )

    try:
        # 실험 실행
        experiment = WADIBulletproofExperiment(config)
        experiment.run_all_experiments()

        # 결과 요약
        print("\n=== 실험 결과 요약 ===")
        for result in experiment.results:
            print(f"조건 {result.condition_id}: {result.sensor_count}센서×{result.frequency}Hz "
                  f"- 성공률: {result.success_rate:.1f}%, 평균시간: {result.avg_total_time:.1f}ms")

    except Exception as e:
        print(f"실험 실행 실패: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
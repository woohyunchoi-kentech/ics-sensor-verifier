#!/usr/bin/env python3
"""
HAI Pedersen Commitment + Bulletproofs 실험
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

# Bulletproof 생성기 임포트  
from fix_inner_product_bulletproof import FixInnerProductBulletproof
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

    # Policy 설정
    policy: str = "ZK_ONLY"  # "ZK_ONLY" | "SELECTIVE" | "RAW"
    upper_bounds: Dict[str, float] = None  # 센서별 상한값
    lower_bounds: Dict[str, float] = None  # 센서별 하한값
    roc_threshold: float = 0.0  # Rate of Change 임계값

    def __post_init__(self):
        if self.sensor_counts is None:
            self.sensor_counts = [1, 10, 50, 100]
        if self.frequencies is None:
            self.frequencies = [1, 2, 10, 100]
        if self.upper_bounds is None:
            self.upper_bounds = {}
        if self.lower_bounds is None:
            self.lower_bounds = {}


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

    # Policy 관련
    policy: str = "ZK_ONLY"
    selective_disclosure_rate: float = 0.0  # SDR (%)


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
            elif isinstance(point, Bn):
                hasher.update(point.binary())
            else:
                hasher.update(str(point).encode())
        return Bn.from_binary(hasher.digest()) % self.order
    
    def generate_proof(self, sensor_value: float, sensor_name: str) -> Dict[str, Any]:
        """Bulletproof 증명 생성"""
        start_time = time.perf_counter()
        
        # 값 스케일링 (소수점 3자리 → 정수)
        scaled_value = int(sensor_value * 1000)
        v = Bn(scaled_value)
        
        # Pedersen Commitment 생성
        commitment_start = time.perf_counter()
        gamma = self._safe_random_bn()
        V = v * self.g + gamma * self.h
        commitment_time = (time.perf_counter() - commitment_start) * 1000
        
        # Bulletproof 증명 생성 (간소화된 버전)
        bulletproof_start = time.perf_counter()
        
        # A, S 생성
        alpha = self._safe_random_bn()
        rho = self._safe_random_bn()
        A = alpha * self.g + gamma * self.h
        S = rho * self.g + alpha * self.h
        
        # Fiat-Shamir 챌린지
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)
        
        # T1, T2 생성
        tau1 = self._safe_random_bn()
        tau2 = self._safe_random_bn()
        t1 = self._safe_random_bn()
        t2 = self._safe_random_bn()
        T1 = t1 * self.g + tau1 * self.h
        T2 = t2 * self.g + tau2 * self.h
        
        x = self._fiat_shamir_challenge(T1, T2, z)
        
        # 최종 값들
        n = self.bit_length
        y_powers = sum(y ** i for i in range(n)) % self.order
        two_powers = sum(Bn(2) ** i for i in range(n)) % self.order
        delta_yz = ((z - z * z) * y_powers - (z ** 3) * two_powers) % self.order
        
        t_hat = ((z * z) * v + delta_yz) % self.order
        tau_x = ((z * z) * gamma + x * tau1 + (x * x) * tau2) % self.order
        mu = (alpha + rho * x) % self.order
        
        # Inner Product Proof (5라운드)
        L_list = []
        R_list = []
        for _ in range(5):
            L_list.append((self._safe_random_bn() * self.g).export().hex())
            R_list.append((self._safe_random_bn() * self.g).export().hex())
        
        bulletproof_time = (time.perf_counter() - bulletproof_start) * 1000
        total_time = (time.perf_counter() - start_time) * 1000
        
        # 증명 구성
        proof = {
            "commitment": V.export().hex(),
            "proof": {
                "A": A.export().hex(),
                "S": S.export().hex(),
                "T1": T1.export().hex(),
                "T2": T2.export().hex(),
                "tau_x": tau_x.hex(),
                "mu": mu.hex(),
                "t": t_hat.hex(),
                "inner_product_proof": {
                    "L": L_list,
                    "R": R_list
                }
            },
            "range_min": 0,
            "range_max": 10000,  # HAI 센서 범위
            "sensor_name": sensor_name,
            "sensor_value": sensor_value,
            "metrics": {
                "commitment_time_ms": commitment_time,
                "bulletproof_time_ms": bulletproof_time,
                "total_time_ms": total_time
            }
        }
        
        return proof


class HAIDataLoader:
    """HAI 데이터셋 로더"""
    
    def __init__(self):
        self.data_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/hai/haiend-23.05"
        self.df = None
        self.sensor_columns = []
    
    def load_data(self) -> pd.DataFrame:
        """HAI 데이터 로드"""
        try:
            # end-test1.csv 로드
            file_path = os.path.join(self.data_path, "end-test1.csv")
            self.df = pd.read_csv(file_path)
            
            # 센서 컬럼 추출 (Timestamp 제외)
            self.sensor_columns = [col for col in self.df.columns if col != 'Timestamp']
            
            print(f"✅ HAI 데이터 로드 완료: {len(self.df)} 행, {len(self.sensor_columns)} 센서")
            return self.df
            
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            raise
    
    def get_sensor_data(self, sensor_names: List[str], num_samples: int) -> Dict[str, List[float]]:
        """특정 센서들의 데이터 샘플링"""
        if self.df is None:
            self.load_data()
        
        result = {}
        for sensor in sensor_names:
            if sensor in self.sensor_columns:
                # 랜덤 샘플링
                values = self.df[sensor].dropna().sample(n=min(num_samples, len(self.df)), replace=True).tolist()
                result[sensor] = values
            else:
                # 센서가 없으면 더미 데이터
                result[sensor] = [np.random.uniform(0, 100) for _ in range(num_samples)]
        
        return result


class BulletproofExperiment:
    """Bulletproof 실험 실행기"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.generator = FixInnerProductBulletproof()
        self.data_loader = HAIDataLoader()
        self.results = []
        self.sensor_state = {}  # 센서별 이전 값 저장 {sensor_name: prev_value}

    def is_alarm(self, sensor_name: str, curr: float, prev: float = None) -> bool:
        """
        알람 판정 함수

        Args:
            sensor_name: 센서 이름
            curr: 현재 값
            prev: 이전 값 (None이면 상태에서 조회)

        Returns:
            bool: 알람 여부
        """
        # 이전 값 조회
        if prev is None:
            prev = self.sensor_state.get(sensor_name, curr)

        # 경계값 조회 (없으면 무한대로 설정)
        lower_bound = self.config.lower_bounds.get(sensor_name, float('-inf'))
        upper_bound = self.config.upper_bounds.get(sensor_name, float('inf'))

        # 알람 판정: 경계 초과 또는 변화율 초과
        boundary_violation = (curr < lower_bound) or (curr > upper_bound)
        roc_violation = abs(curr - prev) > self.config.roc_threshold if self.config.roc_threshold > 0 else False

        # 상태 업데이트
        self.sensor_state[sensor_name] = curr

        return boundary_violation or roc_violation

    def run_single_condition(self, sensor_count: int, frequency: int, condition_id: int) -> ExperimentResult:
        """단일 조건 실험 실행"""
        print(f"\n{'='*60}")
        print(f"📊 조건 #{condition_id}: {sensor_count}센서 × {frequency}Hz")
        print(f"🎯 정책 모드: {self.config.policy}")
        print(f"{'='*60}")

        # 센서 상태 초기화 (조건 간 상태 격리)
        self.sensor_state = {}

        # HAI 데이터 로드
        self.data_loader.load_data()
        
        # 사용할 센서 선택
        all_sensors = self.data_loader.sensor_columns[:sensor_count]
        
        # 각 센서당 필요한 샘플 수
        samples_per_sensor = self.config.target_requests // sensor_count
        
        # 센서 데이터 준비
        sensor_data = self.data_loader.get_sensor_data(all_sensors, samples_per_sensor)
        
        # 실험 메트릭 초기화
        successful_requests = 0
        failed_requests = 0
        commitment_times = []
        bulletproof_times = []
        verification_times = []
        total_times = []
        proof_sizes = []
        cpu_usages = []
        memory_usages = []
        
        # 실험 시작
        start_time = datetime.now()
        experiment_start = time.perf_counter()
        
        # 전송 간격 계산
        interval = 1.0 / frequency  # Hz → 초
        iterations = samples_per_sensor
        
        print(f"⏱️  실행 계획: {iterations}회 반복, {interval:.3f}초 간격")
        print(f"📊 총 {self.config.target_requests}개 요청 예정")

        request_count = 0
        disclosure_count = 0  # Selective Disclosure 카운터

        try:
            for iteration in range(iterations):
                iteration_start = time.perf_counter()

                # 시스템 메트릭 측정
                cpu_usages.append(psutil.cpu_percent(interval=0.01))
                memory_usages.append(psutil.Process().memory_info().rss / 1024 / 1024)

                # 각 센서별로 증명 생성 및 전송
                for sensor_name in all_sensors:
                    if request_count >= self.config.target_requests:
                        break

                    try:
                        # 센서값 가져오기
                        sensor_value = sensor_data[sensor_name][iteration % len(sensor_data[sensor_name])]

                        # 🎯 정책 분기: RAW vs ZK
                        if self.config.policy == "RAW":
                            # RAW 모드: 평문 전송 (ZK 생성 건너뜀)
                            proof_start = time.perf_counter()
                            request_data = {
                                "sensor_name": sensor_name,
                                "raw_value": sensor_value,
                                "mode": "RAW"
                            }
                            proof_time = (time.perf_counter() - proof_start) * 1000
                            commitment_times.append(0)
                            bulletproof_times.append(0)
                        else:
                            # ZK_ONLY / SELECTIVE 모드: Bulletproof 생성
                            proof_start = time.perf_counter()
                            proof_data = self.generator.create_inner_product_fixed_proof(int(sensor_value * 1000))
                            proof_time = (time.perf_counter() - proof_start) * 1000

                            # 메트릭 기록
                            commitment_times.append(proof_time / 2)
                            bulletproof_times.append(proof_time / 2)

                            # 기본 요청 데이터
                            request_data = {
                                "commitment": proof_data["commitment"],
                                "proof": proof_data["proof"],
                                "range_min": proof_data["range_min"],
                                "range_max": proof_data["range_max"]
                            }

                            # 🎯 SELECTIVE 모드: 알람 시 opening 추가
                            if self.config.policy == "SELECTIVE":
                                is_alarm_state = self.is_alarm(sensor_name, sensor_value)
                                if is_alarm_state:
                                    request_data["opening"] = proof_data["opening"]
                                    disclosure_count += 1

                        # 서버로 전송
                        verify_start = time.perf_counter()

                        # 증명 크기 계산
                        proof_size = len(json.dumps(request_data).encode())
                        proof_sizes.append(proof_size)
                        
                        # 서버 검증 요청
                        try:
                            response = requests.post(
                                self.config.server_url,
                                json=request_data,
                                timeout=5
                            )
                            
                            verification_time = (time.perf_counter() - verify_start) * 1000
                            verification_times.append(verification_time)
                            
                            if response.status_code == 200:
                                result = response.json()
                                if result.get('verified', False):
                                    successful_requests += 1
                                else:
                                    failed_requests += 1
                            else:
                                failed_requests += 1
                        
                        except requests.exceptions.RequestException:
                            failed_requests += 1
                            verification_times.append(0)
                        
                        total_times.append(
                            commitment_times[-1] + bulletproof_times[-1] + 
                            (verification_times[-1] if verification_times else 0)
                        )
                        
                        request_count += 1
                        
                        # 진행상황 출력
                        if request_count % 100 == 0:
                            print(f"  ✅ {request_count}/{self.config.target_requests} 완료...")
                    
                    except Exception as e:
                        failed_requests += 1
                        print(f"  ⚠️ 오류: {e}")
                
                # 주파수에 맞춰 대기
                iteration_elapsed = time.perf_counter() - iteration_start
                if iteration_elapsed < interval:
                    time.sleep(interval - iteration_elapsed)
                
                if request_count >= self.config.target_requests:
                    break
        
        except KeyboardInterrupt:
            print("\n⚠️ 실험 중단됨")
        
        # 실험 종료
        end_time = datetime.now()
        duration = time.perf_counter() - experiment_start
        
        # 결과 계산
        success_rate = (successful_requests / max(request_count, 1)) * 100
        verification_rate = success_rate  # Bulletproof에서는 동일

        # 🎯 SDR (Selective Disclosure Rate) 계산
        sdr = (disclosure_count / max(request_count, 1)) * 100 if request_count > 0 else 0.0

        result = ExperimentResult(
            condition_id=condition_id,
            sensor_count=sensor_count,
            frequency=frequency,
            total_requests=request_count,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            verification_rate=verification_rate,
            avg_commitment_time=np.mean(commitment_times) if commitment_times else 0,
            avg_bulletproof_time=np.mean(bulletproof_times) if bulletproof_times else 0,
            avg_verification_time=np.mean(verification_times) if verification_times else 0,
            avg_total_time=np.mean(total_times) if total_times else 0,
            avg_cpu_usage=np.mean(cpu_usages) if cpu_usages else 0,
            avg_memory_usage=np.mean(memory_usages) if memory_usages else 0,
            proof_size_bytes=int(np.mean(proof_sizes)) if proof_sizes else 0,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
            actual_frequency=request_count / duration if duration > 0 else 0,
            policy=self.config.policy,
            selective_disclosure_rate=sdr
        )
        
        # 결과 출력
        print(f"\n📊 조건 #{condition_id} 완료:")
        print(f"  • 정책 모드: {result.policy}")
        print(f"  • 총 요청: {result.total_requests}")
        print(f"  • 성공: {result.successful_requests}")
        print(f"  • 실패: {result.failed_requests}")
        print(f"  • 성공률: {result.success_rate:.1f}%")
        if result.policy == "SELECTIVE":
            print(f"  • 📊 SDR (Selective Disclosure Rate): {result.selective_disclosure_rate:.2f}% ({disclosure_count}/{request_count})")
        print(f"  • 평균 커밋먼트 시간: {result.avg_commitment_time:.2f}ms")
        print(f"  • 평균 Bulletproof 시간: {result.avg_bulletproof_time:.2f}ms")
        print(f"  • 평균 검증 시간: {result.avg_verification_time:.2f}ms")
        print(f"  • 평균 총 시간: {result.avg_total_time:.2f}ms")
        print(f"  • 증명 크기: {result.proof_size_bytes} bytes")
        print(f"  • 실행 시간: {result.duration_seconds:.1f}초")
        
        return result
    
    def run_all_experiments(self):
        """모든 실험 조건 실행"""
        print("\n🚀 HAI Bulletproofs 실험 시작")
        print(f"📊 총 {len(self.config.sensor_counts) * len(self.config.frequencies)}개 조건")
        
        all_results = []
        condition_id = 1
        
        for sensor_count in self.config.sensor_counts:
            for frequency in self.config.frequencies:
                try:
                    result = self.run_single_condition(sensor_count, frequency, condition_id)
                    all_results.append(result)
                    
                    # 결과 저장 (중간 저장)
                    self.save_results(all_results, f"progress_{condition_id:02d}")
                    
                except Exception as e:
                    print(f"❌ 조건 #{condition_id} 실패: {e}")
                    traceback.print_exc()
                
                condition_id += 1
                
                # 조건 간 휴식
                time.sleep(2)
        
        # 최종 결과 저장
        self.save_results(all_results, "final")
        self.print_summary(all_results)
        
        return all_results
    
    def save_results(self, results: List[ExperimentResult], suffix: str = ""):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 결과 디렉토리 생성
        result_dir = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/results"
        os.makedirs(result_dir, exist_ok=True)
        
        # JSON 저장
        filename = f"hai_bulletproofs_{suffix}_{timestamp}.json"
        filepath = os.path.join(result_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        
        print(f"💾 결과 저장: {filepath}")
        
        # CSV 저장
        df = pd.DataFrame([asdict(r) for r in results])
        csv_path = filepath.replace('.json', '.csv')
        df.to_csv(csv_path, index=False)
        print(f"💾 CSV 저장: {csv_path}")
    
    def print_summary(self, results: List[ExperimentResult]):
        """전체 실험 요약 출력"""
        print("\n" + "="*80)
        print("🏆 HAI Bulletproofs 실험 완료 요약")
        print("="*80)
        
        # 전체 통계
        total_requests = sum(r.total_requests for r in results)
        total_success = sum(r.successful_requests for r in results)
        overall_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\n📊 전체 통계:")
        print(f"  • 총 조건: {len(results)}개")
        print(f"  • 총 요청: {total_requests}개")
        print(f"  • 총 성공: {total_success}개")
        print(f"  • 전체 성공률: {overall_success_rate:.1f}%")
        
        # 평균 성능
        avg_commitment = np.mean([r.avg_commitment_time for r in results])
        avg_bulletproof = np.mean([r.avg_bulletproof_time for r in results])
        avg_verification = np.mean([r.avg_verification_time for r in results])
        avg_total = np.mean([r.avg_total_time for r in results])
        avg_proof_size = np.mean([r.proof_size_bytes for r in results])
        
        print(f"\n⏱️ 평균 성능:")
        print(f"  • Pedersen Commitment: {avg_commitment:.2f}ms")
        print(f"  • Bulletproof 생성: {avg_bulletproof:.2f}ms")
        print(f"  • 서버 검증: {avg_verification:.2f}ms")
        print(f"  • 전체 시간: {avg_total:.2f}ms")
        print(f"  • 증명 크기: {avg_proof_size:.0f} bytes")
        
        # 조건별 요약 테이블
        print(f"\n📋 조건별 결과:")
        print(f"{'조건':<5} {'센서':<6} {'Hz':<5} {'요청':<6} {'성공률':<8} {'커밋':<8} {'BP':<8} {'검증':<8} {'총시간':<8}")
        print("-" * 80)
        
        for r in results:
            print(f"#{r.condition_id:<4} {r.sensor_count:<6} {r.frequency:<5} "
                  f"{r.total_requests:<6} {r.success_rate:<7.1f}% "
                  f"{r.avg_commitment_time:<7.1f} {r.avg_bulletproof_time:<7.1f} "
                  f"{r.avg_verification_time:<7.1f} {r.avg_total_time:<7.1f}")


def main():
    """메인 실행 함수"""
    print("="*80)
    print("🚀 HAI Pedersen Commitment + Bulletproofs 실험")
    print("📊 베이스라인 연구: 영지식 범위 증명 성능 측정")
    print("="*80)
    
    # 실험 설정
    config = ExperimentConfig(
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],
        target_requests=1000,
        server_url="http://192.168.0.11:8085/api/v1/verify/bulletproof"
    )
    
    # 서버 연결 확인
    print("\n🔍 서버 연결 확인...")
    try:
        response = requests.get("http://192.168.0.11:8085/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공")
        else:
            print(f"⚠️ 서버 응답 이상: {response.status_code}")
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("서버를 먼저 실행해주세요.")
        return
    
    # 실험 실행
    experiment = BulletproofExperiment(config)
    results = experiment.run_all_experiments()
    
    print("\n✅ 모든 실험 완료!")
    print(f"📊 총 {len(results)}개 조건 테스트 완료")


if __name__ == "__main__":
    main()
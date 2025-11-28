#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HAI Bulletproof Performance Experiment
16가지 조건 (센서 수 × 주파수) 성능 측정

측정 메트릭:
1. 엔드투엔드 지연시간 (E2E Latency)
2. 서버 검증시간 (Server Verification Time)
3. CPU 사용량
4. 메모리 사용량
5. 성공률 (%)
"""

import os
import sys
import time
import json
import random
import hashlib
import argparse
import threading
from datetime import datetime
from typing import Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import psutil
import numpy as np

# Bulletproof 모듈
try:
    from crypto.bulletproof_prover_production import generate_range_proof
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from crypto.bulletproof_prover_production import generate_range_proof


class PerformanceExperiment:
    """HAI Bulletproof 성능 실험"""

    def __init__(self, server_url: str, output_dir: str = "results"):
        self.server_url = server_url
        self.output_dir = output_dir
        self.domain = "ICS_BULLETPROOF_VERIFIER_v1"
        self.n_bits = 32

        # 실험 조건: (센서 수, Hz, 총 요청 수)
        self.experiment_conditions = [
            # Phase 1: 1센서
            (1, 1, 100),     # 1센서, 1Hz, 100개
            (1, 2, 100),     # 1센서, 2Hz, 100개
            (1, 10, 100),    # 1센서, 10Hz, 100개
            (1, 100, 100),   # 1센서, 100Hz, 100개

            # Phase 2: 10센서
            (10, 1, 100),
            (10, 2, 100),
            (10, 10, 100),
            (10, 100, 100),

            # Phase 3: 50센서
            (50, 1, 100),
            (50, 2, 100),
            (50, 10, 100),
            (50, 100, 100),

            # Phase 4: 100센서
            (100, 1, 100),
            (100, 2, 100),
            (100, 10, 100),
            (100, 100, 100),
        ]

        # 결과 저장
        self.results = []

        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)

        print("=" * 70)
        print("HAI Bulletproof Performance Experiment")
        print("=" * 70)
        print(f"Server: {server_url}")
        print(f"Output: {output_dir}")
        print(f"Conditions: {len(self.experiment_conditions)}")
        print("=" * 70)

    def _generate_nonce(self) -> str:
        """고유 nonce 생성"""
        timestamp = str(time.time()).encode('utf-8')
        random_bytes = str(random.random()).encode('utf-8')
        return hashlib.sha256(timestamp + random_bytes).hexdigest()

    def _get_system_metrics(self) -> Dict[str, float]:
        """시스템 메트릭 수집"""
        process = psutil.Process()
        return {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
        }

    def send_single_request(self, sensor_id: str, value: float) -> Dict[str, Any]:
        """단일 요청 전송 및 메트릭 수집"""
        nonce = self._generate_nonce()
        event_ts = int(time.time() * 1000)

        # 값 스케일링
        value_int = int(value * 1_000_000)
        if value_int < 0:
            value_int = 0
        if value_int >= 2**self.n_bits:
            value_int = 2**self.n_bits - 1

        result = {
            "sensor_id": sensor_id,
            "value": value,
            "value_int": value_int,
            "nonce": nonce[:16],
            "success": False,
            "verified": False,
            "e2e_latency_ms": 0,
            "server_time_ms": 0,
            "proof_gen_time_ms": 0,
            "network_time_ms": 0,
            "error": None,
        }

        try:
            # 1. Bulletproof 생성 시간 측정
            proof_start = time.perf_counter()
            proof_result = generate_range_proof(
                value_int=value_int,
                nonce=nonce,
                n=self.n_bits,
                domain=self.domain,
                mode="production"
            )
            proof_end = time.perf_counter()
            result["proof_gen_time_ms"] = (proof_end - proof_start) * 1000

            # 2. 서버 요청 (E2E 시간 측정)
            payload = {
                "mode": "ZK_ONLY",
                "sensor": sensor_id,
                "ts": event_ts,
                "nonce": nonce,
                "type": "sensor_value",
                "range_min": 0,
                "range_max": 2**self.n_bits - 1,
                "commitment": proof_result["commitment"],
                "proof": proof_result["proof"],
                "metadata": {
                    "domain": self.domain,
                    "n": self.n_bits,
                }
            }

            e2e_start = time.perf_counter()
            response = requests.post(
                f"{self.server_url}/api/v1/verify/bulletproof",
                json=payload,
                timeout=30
            )
            e2e_end = time.perf_counter()

            result["e2e_latency_ms"] = (e2e_end - e2e_start) * 1000

            if response.status_code == 200:
                resp_data = response.json()
                result["success"] = True
                result["verified"] = resp_data.get("verified", False)
                result["server_time_ms"] = resp_data.get("processing_time_ms", 0)
                result["network_time_ms"] = result["e2e_latency_ms"] - result["server_time_ms"]
            else:
                result["error"] = f"HTTP {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def run_condition(self, num_sensors: int, frequency_hz: int,
                      total_requests: int) -> Dict[str, Any]:
        """단일 조건 실험 실행"""

        condition_name = f"{num_sensors}sensors_{frequency_hz}Hz"
        print(f"\n{'='*60}")
        print(f"Condition: {condition_name} ({total_requests} requests)")
        print(f"{'='*60}")

        # 센서 ID 생성
        sensor_ids = [f"SENSOR-{i:03d}" for i in range(num_sensors)]
        requests_per_sensor = total_requests // num_sensors

        # 메트릭 수집용
        metrics = {
            "condition": condition_name,
            "num_sensors": num_sensors,
            "frequency_hz": frequency_hz,
            "total_requests": total_requests,
            "start_time": datetime.now().isoformat(),

            # 성능 메트릭
            "e2e_latencies_ms": [],
            "server_times_ms": [],
            "proof_gen_times_ms": [],
            "network_times_ms": [],

            # 시스템 메트릭
            "cpu_samples": [],
            "memory_samples": [],

            # 결과
            "success_count": 0,
            "verified_count": 0,
            "error_count": 0,
            "errors": [],
        }

        # 시스템 메트릭 샘플링 스레드
        stop_monitoring = threading.Event()

        def monitor_system():
            while not stop_monitoring.is_set():
                sys_metrics = self._get_system_metrics()
                metrics["cpu_samples"].append(sys_metrics["cpu_percent"])
                metrics["memory_samples"].append(sys_metrics["memory_mb"])
                time.sleep(0.5)

        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()

        # 요청 간격 계산
        interval = 1.0 / frequency_hz

        # 요청 전송
        request_count = 0
        experiment_start = time.perf_counter()

        for sensor_id in sensor_ids:
            for i in range(requests_per_sensor):
                request_start = time.perf_counter()

                # 랜덤 센서 값 (0.5 ~ 2.0 범위)
                value = random.uniform(0.5, 2.0)

                # 요청 전송
                result = self.send_single_request(sensor_id, value)

                # 결과 수집
                if result["success"]:
                    metrics["success_count"] += 1
                    metrics["e2e_latencies_ms"].append(result["e2e_latency_ms"])
                    metrics["server_times_ms"].append(result["server_time_ms"])
                    metrics["proof_gen_times_ms"].append(result["proof_gen_time_ms"])
                    metrics["network_times_ms"].append(result["network_time_ms"])

                    if result["verified"]:
                        metrics["verified_count"] += 1
                else:
                    metrics["error_count"] += 1
                    if result["error"]:
                        metrics["errors"].append(result["error"])

                request_count += 1

                # 진행 상황 출력 (10% 단위)
                if request_count % (total_requests // 10) == 0:
                    progress = (request_count / total_requests) * 100
                    print(f"  Progress: {progress:.0f}% ({request_count}/{total_requests})")

                # 주파수 제어
                elapsed = time.perf_counter() - request_start
                sleep_time = max(0, interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        experiment_end = time.perf_counter()

        # 모니터링 중지
        stop_monitoring.set()
        monitor_thread.join(timeout=1)

        # 통계 계산
        metrics["end_time"] = datetime.now().isoformat()
        metrics["total_duration_sec"] = experiment_end - experiment_start
        metrics["actual_rps"] = request_count / metrics["total_duration_sec"]

        if metrics["e2e_latencies_ms"]:
            metrics["stats"] = {
                "e2e_latency": {
                    "avg_ms": np.mean(metrics["e2e_latencies_ms"]),
                    "min_ms": np.min(metrics["e2e_latencies_ms"]),
                    "max_ms": np.max(metrics["e2e_latencies_ms"]),
                    "std_ms": np.std(metrics["e2e_latencies_ms"]),
                    "p50_ms": np.percentile(metrics["e2e_latencies_ms"], 50),
                    "p95_ms": np.percentile(metrics["e2e_latencies_ms"], 95),
                    "p99_ms": np.percentile(metrics["e2e_latencies_ms"], 99),
                },
                "server_time": {
                    "avg_ms": np.mean(metrics["server_times_ms"]),
                    "min_ms": np.min(metrics["server_times_ms"]),
                    "max_ms": np.max(metrics["server_times_ms"]),
                },
                "proof_gen_time": {
                    "avg_ms": np.mean(metrics["proof_gen_times_ms"]),
                    "min_ms": np.min(metrics["proof_gen_times_ms"]),
                    "max_ms": np.max(metrics["proof_gen_times_ms"]),
                },
                "network_time": {
                    "avg_ms": np.mean(metrics["network_times_ms"]),
                    "min_ms": np.min(metrics["network_times_ms"]),
                    "max_ms": np.max(metrics["network_times_ms"]),
                },
                "cpu": {
                    "avg_percent": np.mean(metrics["cpu_samples"]) if metrics["cpu_samples"] else 0,
                    "max_percent": np.max(metrics["cpu_samples"]) if metrics["cpu_samples"] else 0,
                },
                "memory": {
                    "avg_mb": np.mean(metrics["memory_samples"]) if metrics["memory_samples"] else 0,
                    "max_mb": np.max(metrics["memory_samples"]) if metrics["memory_samples"] else 0,
                },
                "success_rate": (metrics["success_count"] / total_requests) * 100,
                "verification_rate": (metrics["verified_count"] / total_requests) * 100,
            }

        # 결과 출력
        print(f"\n  Results:")
        print(f"    Success: {metrics['success_count']}/{total_requests} ({metrics['stats']['success_rate']:.1f}%)")
        print(f"    Verified: {metrics['verified_count']}/{total_requests} ({metrics['stats']['verification_rate']:.1f}%)")
        print(f"    E2E Latency: {metrics['stats']['e2e_latency']['avg_ms']:.2f}ms (avg)")
        print(f"    Server Time: {metrics['stats']['server_time']['avg_ms']:.2f}ms (avg)")
        print(f"    CPU: {metrics['stats']['cpu']['avg_percent']:.1f}%")
        print(f"    Memory: {metrics['stats']['memory']['avg_mb']:.1f}MB")
        print(f"    Actual RPS: {metrics['actual_rps']:.2f}")

        # 상세 데이터 제거 (저장 용량 절약)
        del metrics["e2e_latencies_ms"]
        del metrics["server_times_ms"]
        del metrics["proof_gen_times_ms"]
        del metrics["network_times_ms"]
        del metrics["cpu_samples"]
        del metrics["memory_samples"]

        return metrics

    def run_all(self):
        """모든 조건 실험 실행"""
        print(f"\nStarting all {len(self.experiment_conditions)} conditions...")
        print(f"Total requests: {sum(c[2] for c in self.experiment_conditions)}")

        all_results = {
            "experiment": "HAI Bulletproof Performance",
            "server_url": self.server_url,
            "start_time": datetime.now().isoformat(),
            "conditions": [],
        }

        for i, (num_sensors, freq_hz, total_req) in enumerate(self.experiment_conditions, 1):
            print(f"\n[{i}/{len(self.experiment_conditions)}]")

            result = self.run_condition(num_sensors, freq_hz, total_req)
            all_results["conditions"].append(result)

            # 조건 간 휴식
            time.sleep(2)

        all_results["end_time"] = datetime.now().isoformat()

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"performance_{timestamp}.json")

        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n{'='*70}")
        print(f"Experiment Complete!")
        print(f"Results saved to: {output_file}")
        print(f"{'='*70}")

        # 요약 출력
        self._print_summary(all_results)

        return all_results

    def _print_summary(self, results: Dict):
        """결과 요약 출력"""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"{'Condition':<25} {'E2E(ms)':<12} {'Server(ms)':<12} {'CPU(%)':<10} {'Mem(MB)':<10} {'Success':<10}")
        print("-" * 70)

        for cond in results["conditions"]:
            stats = cond.get("stats", {})
            e2e = stats.get("e2e_latency", {}).get("avg_ms", 0)
            server = stats.get("server_time", {}).get("avg_ms", 0)
            cpu = stats.get("cpu", {}).get("avg_percent", 0)
            mem = stats.get("memory", {}).get("avg_mb", 0)
            success = stats.get("success_rate", 0)

            print(f"{cond['condition']:<25} {e2e:<12.2f} {server:<12.2f} {cpu:<10.1f} {mem:<10.1f} {success:<10.1f}%")

        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="HAI Bulletproof Performance Experiment")
    parser.add_argument("--server", default="http://192.168.0.11:8085",
                        help="Server URL")
    parser.add_argument("--output", default="results",
                        help="Output directory")
    parser.add_argument("--requests", type=int, default=100,
                        help="Requests per condition")
    args = parser.parse_args()

    experiment = PerformanceExperiment(
        server_url=args.server,
        output_dir=args.output
    )

    # 요청 수 조정
    if args.requests != 100:
        experiment.experiment_conditions = [
            (sensors, hz, args.requests)
            for sensors, hz, _ in experiment.experiment_conditions
        ]

    experiment.run_all()


if __name__ == "__main__":
    main()

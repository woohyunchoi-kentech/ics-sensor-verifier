#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HAI Sensor Client with IPP Trace (ZK-IPP Endpoint)

HAI 데이터셋에서 센서 값을 주기적으로 읽고,
각 값에 대해 Pedersen Commitment와 Bulletproof Range Proof를 생성하며,
client_trace (generators, rounds, final)를 포함하여
http://192.168.0.11:8085/api/v1/verify/zk-ipp 엔드포인트로 전송합니다.

기밀성 원칙:
- 센서 값 v는 절대 서버로 전송하지 않습니다
- 블라인딩 인자 r는 절대 서버로 전송하지 않습니다
- 내부 벡터 a_vec, b_vec는 절대 전송하지 않습니다
"""

import sys
import os
import time
import csv
import json
import argparse
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# crypto 모듈 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crypto'))
from bulletproof_prover_production_with_trace import BulletproofProverWithTrace


class HAISensorIPPClient:
    """HAI 센서 클라이언트 (IPP Trace 포함)"""

    def __init__(self, server_url: str, sensor_name: str,
                 csv_path: Optional[str] = None,
                 range_min: float = 0.0, range_max: float = 1000.0,
                 mode: str = "production", verbose: bool = False):
        self.server_url = server_url
        self.sensor_name = sensor_name
        self.csv_path = csv_path
        self.range_min = range_min
        self.range_max = range_max
        self.mode = mode
        self.verbose = verbose

        # ZK-IPP 엔드포인트
        self.endpoint = f"{server_url}/api/v1/verify/zk-ipp"

        # Bulletproof Prover (with Trace)
        self.prover = BulletproofProverWithTrace(bit_length=32, domain="ICS_BULLETPROOF_VERIFIER_v1")

        # CSV 데이터
        self.csv_data = []
        self.csv_index = 0

        if csv_path:
            self._load_csv()

        print(f"[INIT] HAI Sensor IPP Client")
        print(f"[INIT] Server: {server_url}")
        print(f"[INIT] Sensor: {sensor_name}")
        print(f"[INIT] Endpoint: {self.endpoint}")
        print(f"[INIT] Mode: {mode}")
        print(f"[INIT] Range: [{range_min}, {range_max}]")
        if csv_path:
            print(f"[INIT] CSV: {csv_path} ({len(self.csv_data)} records)")
        print()

    def _load_csv(self):
        """CSV 파일 로드"""
        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 센서 컬럼 찾기
                    if self.sensor_name in row:
                        value = float(row[self.sensor_name])
                        self.csv_data.append(value)

            if not self.csv_data:
                print(f"[ERROR] No data for sensor {self.sensor_name} in CSV")
                sys.exit(1)

        except Exception as e:
            print(f"[ERROR] Failed to load CSV: {e}")
            sys.exit(1)

    def _get_next_value(self) -> Optional[float]:
        """다음 센서 값 가져오기"""
        if not self.csv_path:
            # CSV 없으면 랜덤 값 생성
            import random
            return random.uniform(self.range_min, self.range_max)

        if self.csv_index >= len(self.csv_data):
            print("[INFO] CSV data exhausted, wrapping around")
            self.csv_index = 0

        value = self.csv_data[self.csv_index]
        self.csv_index += 1
        return value

    def _generate_proof_with_trace(self, sensor_value: float, nonce: str) -> Optional[Dict[str, Any]]:
        """Bulletproof 증명 생성 (client_trace 포함)"""
        try:
            # Scale value: value * 1000
            scaled_value = int(sensor_value * 1000)

            # Validate range
            if scaled_value < 0 or scaled_value >= 2**32:
                print(f"[ERROR] Scaled value {scaled_value} out of range [0, 2^32-1]")
                return None

            # Generate Bulletproof with Trace
            result = self.prover.generate_range_proof_with_trace(scaled_value, nonce)

            return result

        except Exception as e:
            print(f"[ERROR] Proof generation failed: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return None

    def _send_to_server(self, payload: Dict[str, Any]) -> bool:
        """서버로 전송"""
        try:
            response = requests.post(self.endpoint, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()
                verified = result.get("verified", False)

                if verified:
                    processing_time = result.get("processing_time_ms", 0)
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                    if not self.verbose:
                        # Production: 간결한 로그
                        print(f"[{timestamp}] sensor={self.sensor_name} result=SUCCESS server_time={processing_time:.1f}ms")
                    else:
                        # Verbose: 상세 로그
                        print(f"[OK] IPP Verification SUCCESS")
                        print(f"     Processing time: {processing_time:.1f}ms")
                        comparison = result.get("comparison_details", {})
                        if comparison:
                            print(f"     Rounds matched: {comparison.get('matching_rounds', 0)}/{comparison.get('total_rounds', 0)}")
                            print(f"     Final checks: {'PASSED' if comparison.get('final_checks_passed') else 'FAILED'}")

                    return True
                else:
                    # 검증 실패
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    reason = result.get("error", "unknown")
                    print(f"[{timestamp}] sensor={self.sensor_name} result=FAIL reason={reason}")

                    if self.verbose:
                        print(f"     Server response: {json.dumps(result, indent=2)}")

                    return False
            else:
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                print(f"[{timestamp}] sensor={self.sensor_name} result=HTTP_ERROR status={response.status_code}")
                if self.verbose:
                    print(f"     Response: {response.text}")
                return False

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            print(f"[{timestamp}] sensor={self.sensor_name} result=EXCEPTION error={str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def process_single_value(self) -> bool:
        """단일 센서 값 처리"""
        # 1. HAI 값 읽기
        sensor_value = self._get_next_value()
        if sensor_value is None:
            return False

        # 2. Nonce 생성
        nonce = f"{self.sensor_name}_{int(time.time())}_{self.csv_index}"

        start_time = time.time()

        # 3. Bulletproof + client_trace 생성
        proof_data = self._generate_proof_with_trace(sensor_value, nonce)

        if proof_data is None:
            return False

        proof_time = (time.time() - start_time) * 1000

        # 4. 서버 요청 페이로드 구성
        payload = {
            "commitment": proof_data["commitment"],
            "proof": proof_data["proof"],
            "client_trace": proof_data["client_trace"]
        }

        # 기밀성 검증: v, r, a_vec, b_vec가 포함되지 않았는지 확인
        payload_str = json.dumps(payload)
        if "value" in payload_str or "blinding_factor" in payload_str:
            print("[CRITICAL] Confidential data leak detected in payload!")
            return False

        if self.verbose:
            print(f"[INFO] Sensor value: {sensor_value:.3f} (scaled: {int(sensor_value * 1000)})")
            print(f"[INFO] Proof generation time: {proof_time:.2f}ms")
            print(f"[INFO] Payload size: {len(payload_str)} bytes")

        # 5. 서버로 전송
        return self._send_to_server(payload)

    def run(self, interval: float = 2.0, once: bool = False):
        """주기적 실행"""
        print(f"[START] Running sensor client (interval={interval}s)")
        print()

        if once:
            self.process_single_value()
        else:
            while True:
                try:
                    self.process_single_value()
                    time.sleep(interval)
                except KeyboardInterrupt:
                    print("\n[STOP] Sensor client stopped by user")
                    break
                except Exception as e:
                    print(f"[ERROR] Unexpected error: {e}")
                    if self.verbose:
                        import traceback
                        traceback.print_exc()
                    time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="HAI Sensor Client with IPP Trace")
    parser.add_argument("--server", required=True, help="Server URL (e.g., http://192.168.0.11:8085)")
    parser.add_argument("--sensor", required=True, help="Sensor name (e.g., DM-PIT01)")
    parser.add_argument("--csv", help="CSV file path")
    parser.add_argument("--range-min", type=float, default=0.0, help="Min range value")
    parser.add_argument("--range-max", type=float, default=1000.0, help="Max range value")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval in seconds")
    parser.add_argument("--mode", choices=["production", "dev"], default="production", help="Mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--once", action="store_true", help="Run once and exit")

    args = parser.parse_args()

    client = HAISensorIPPClient(
        server_url=args.server,
        sensor_name=args.sensor,
        csv_path=args.csv,
        range_min=args.range_min,
        range_max=args.range_max,
        mode=args.mode,
        verbose=args.verbose
    )

    client.run(interval=args.interval, once=args.once)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Client with Selective Disclosure (Policy + Privacy) - Production Ready

기본 동작:
- ZK_ONLY 모드로 Pedersen Commitment + Bulletproof만 전송
- RAW 값은 별도 Reveal 서버(http://127.0.0.1:9000)로 전송하여 저장
- 서버가 /api/v1/reveal-raw로 요청하면 Reveal 서버가 RAW 값 제공

Dependencies:
    pip3 install requests pandas

Usage:
    # Production Mode (간결한 로그)
    python3 sensor_client_selective_disclosure.py --server http://192.168.0.11:8085 --sensor DM-PIT01 --csv ./data/hai.csv --mode production

    # Test Mode (상세 로그)
    python3 sensor_client_selective_disclosure.py --server http://192.168.0.11:8085 --sensor DM-PIT01 --csv ./data/hai.csv --mode test
"""

import sys
import time
import json
import argparse
import random
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install with: pip3 install requests")
    sys.exit(1)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: 'pandas' not installed. CSV mode disabled. Install with: pip3 install pandas")

try:
    from crypto.bulletproof_prover_production import generate_range_proof
    PROVER_AVAILABLE = True
    print("[INIT] Using Production Mode Bulletproof prover (server-compatible)")
except ImportError as e:
    PROVER_AVAILABLE = False
    print(f"Error: Bulletproof prover not available: {e}")
    print("Make sure crypto/bulletproof_prover_production.py exists and petlib is installed")
    print("Install petlib with: pip3 install petlib")
    sys.exit(1)


class SelectiveDisclosureClient:
    """Policy + Selective Disclosure 센서 클라이언트 (Production Ready)"""

    def __init__(self, server_url: str, sensor_name: str,
                 reveal_url: str = "http://127.0.0.1:9000",
                 csv_path: Optional[str] = None,
                 range_min: float = 0.0, range_max: float = 4294967.295,
                 mode: str = "production"):
        """
        Args:
            server_url: 검증 서버 URL (Bulletproof 서버)
            sensor_name: 센서 ID
            reveal_url: RAW 값 저장 서버 URL
            csv_path: CSV 파일 경로 (None이면 시뮬레이션)
            range_min: 센서 값 최소 범위 (기본: 0.0)
            range_max: 센서 값 최대 범위 (기본: 4294967.295)
            mode: 'production' (간결한 로그) or 'test' (상세 로그)
        """
        self.server_url = server_url
        self.sensor_name = sensor_name
        self.endpoint = f"{server_url}/api/v1/verify/bulletproof"
        self.reveal_url = reveal_url
        self.reveal_store_endpoint = f"{reveal_url}/api/v1/store-raw"
        self.range_min = range_min
        self.range_max = range_max
        self.domain = "ICS_BULLETPROOF_VERIFIER_v1"
        self.n_bits = 32
        self.mode = mode  # production or test
        self.verbose = (mode == "test")  # test 모드에서만 상세 로그

        # CSV 데이터 로드
        self.csv_data = None
        self.csv_index = 0
        if csv_path and PANDAS_AVAILABLE:
            self._load_csv(csv_path)

    def _load_csv(self, csv_path: str):
        """CSV 파일 로드"""
        try:
            df = pd.read_csv(csv_path)
            if self.sensor_name not in df.columns:
                available = list(df.columns[:10])
                print(f"Error: Sensor '{self.sensor_name}' not in CSV. Available: {available}")
                sys.exit(1)

            self.csv_data = df[self.sensor_name].dropna().values
            print(f"[INIT] CSV 로드: {len(self.csv_data)} rows, range=[{self.csv_data.min():.3f}, {self.csv_data.max():.3f}]")
        except Exception as e:
            print(f"Error loading CSV: {e}")
            sys.exit(1)

    def _get_next_value(self) -> float:
        """다음 센서 값 가져오기"""
        if self.csv_data is not None:
            value = float(self.csv_data[self.csv_index % len(self.csv_data)])
            self.csv_index += 1
            return value
        else:
            # 시뮬레이션: 정규분포 (평균=5, 표준편차=2)
            return max(0, random.gauss(5.0, 2.0))

    def _generate_nonce(self) -> str:
        """24자리 랜덤 hex nonce 생성"""
        return ''.join(random.choices('0123456789ABCDEF', k=24))

    def _compute_fiat_shamir_challenges(self, proof: Dict[str, Any]) -> Dict[str, str]:
        """Fiat-Shamir 챌린지 계산"""
        A = proof.get("A", "")
        S = proof.get("S", "")
        T1 = proof.get("T1", "")
        T2 = proof.get("T2", "")

        # y = H(domain||n||A||S)
        h_y = hashlib.sha256()
        h_y.update(self.domain.encode('utf-8'))
        h_y.update(self.n_bits.to_bytes(4, 'big'))
        h_y.update(bytes.fromhex(A))
        h_y.update(bytes.fromhex(S))
        y = h_y.hexdigest().upper()

        # z = H(domain||n||A||S||y)
        h_z = hashlib.sha256()
        h_z.update(self.domain.encode('utf-8'))
        h_z.update(self.n_bits.to_bytes(4, 'big'))
        h_z.update(bytes.fromhex(A))
        h_z.update(bytes.fromhex(S))
        h_z.update(bytes.fromhex(y))
        z = h_z.hexdigest().upper()

        # x = H(domain||n||T1||T2||z)
        h_x = hashlib.sha256()
        h_x.update(self.domain.encode('utf-8'))
        h_x.update(self.n_bits.to_bytes(4, 'big'))
        h_x.update(bytes.fromhex(T1))
        h_x.update(bytes.fromhex(T2))
        h_x.update(bytes.fromhex(z))
        x = h_x.hexdigest().upper()

        return {"y": y, "z": z, "x": x}

    def _build_zk_request(self, sensor_value: float, event_ts: int, nonce: str) -> Optional[Dict[str, Any]]:
        """ZK_ONLY 요청 생성 (실제 Bulletproof 증명 생성)"""
        # Scale value: convert float to integer (value * 1000)
        scaled_value = int(sensor_value * 1000)

        # Validate range: must fit in 32 bits (0 to 2^32-1)
        if scaled_value < 0 or scaled_value >= 2**self.n_bits:
            print(f"[⚠️ RANGE-ERROR] Scaled value {scaled_value} out of range [0, {2**self.n_bits-1}]")
            return None

        try:
            # Generate fresh Bulletproof for this value (Production Mode)
            proof_data = generate_range_proof(scaled_value, nonce, n=self.n_bits, domain=self.domain, mode="production")

            # Extract commitment, proof, and blinding factor
            commitment = proof_data["commitment"]
            proof = proof_data["proof"]
            blinding_factor = proof_data["blinding_factor"]

            # Prepare value in hex format
            value_hex = format(scaled_value, '064x')

            # Convert range to scaled integers (value * 1000)
            scaled_range_min = int(self.range_min * 1000)
            scaled_range_max = int(self.range_max * 1000)

            # ZK_ONLY 모드: opening 필드 제외 (RAW 값은 Reveal 서버로만 전송)
            request = {
                "mode": "ZK_ONLY",
                "sensor": self.sensor_name,
                "ts": event_ts,
                "nonce": nonce,
                "type": "sensor_value",
                "range_min": scaled_range_min,
                "range_max": scaled_range_max,
                "commitment": commitment,
                "proof": proof,
                "metadata": {
                    "domain": self.domain,
                    "n": self.n_bits,
                    "encoding": "secp256k1-compressed-hex",
                    "client": "sensor_client_selective_disclosure.py",
                    "policy": "selective_disclosure",
                    "raw_value_available": True,
                    "proof_generation": "real_bulletproof",
                    "client_mode": self.mode
                }
            }

            # Compute Fiat-Shamir challenges for cross-verification
            request["challenges"] = self._compute_fiat_shamir_challenges(proof)

            return request

        except Exception as e:
            print(f"[⚠️ PROOF-ERROR] Failed to generate proof: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return None

    def _store_raw_value(self, sensor_id: str, event_ts: int, nonce: str, raw_value: float) -> bool:
        """RAW 값을 Reveal 서버에 저장"""
        try:
            response = requests.post(
                self.reveal_store_endpoint,
                json={
                    "sensor_id": sensor_id,
                    "event_ts": event_ts,
                    "nonce": nonce,
                    "raw_value": raw_value
                },
                timeout=2
            )

            if response.status_code == 200:
                return True
            else:
                if self.verbose:
                    print(f"[⚠️ STORE-FAIL] Reveal 서버 응답: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            if self.verbose:
                print(f"[⚠️ STORE-FAIL] Reveal 서버 연결 실패 ({self.reveal_url})")
            return False
        except Exception as e:
            if self.verbose:
                print(f"[⚠️ STORE-FAIL] {e}")
            return False

    def send_value(self) -> bool:
        """센서 값 전송 (ZK_ONLY 모드)"""
        sensor_value = self._get_next_value()
        event_ts = int(time.time())
        nonce = self._generate_nonce()
        start_time = time.time()

        # 범위 체크
        range_status = "OK"
        if sensor_value < self.range_min:
            range_status = f"BELOW_MIN"
        elif sensor_value > self.range_max:
            range_status = f"ABOVE_MAX"

        # 1. RAW 값을 Reveal 서버에 저장
        self._store_raw_value(self.sensor_name, event_ts, nonce, sensor_value)

        # 2. ZK 요청 생성 (실제 Bulletproof 증명 생성)
        request = self._build_zk_request(sensor_value, event_ts, nonce)

        # 증명 생성 실패 시 종료
        if request is None:
            if self.verbose:
                print(f"[⚠️ SKIP] sensor={self.sensor_name}, ts={event_ts}, nonce={nonce}, value={sensor_value:.6f} (proof generation failed)")
            return False

        try:
            response = requests.post(self.endpoint, json=request, timeout=10)
            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                result = response.json()

                # ✅ FIX: 서버 응답 스펙에 맞춰서 파싱
                # 우선순위: success > verified > ok
                success = result.get("success", result.get("verified", result.get("ok", False)))

                if success:
                    # Production Mode: 간결한 헬스체크 로그
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    scaled_value = int(sensor_value * 1000)

                    if not self.verbose:
                        # Production 모드: 한 줄 헬스체크 로그
                        print(f"[{timestamp}] sensor={self.sensor_name} value={sensor_value:.3f} scaled={scaled_value} result=SUCCESS latency_ms={latency_ms:.1f}")
                    else:
                        # Test 모드: 상세 로그
                        print(f"[OK] Bulletproof verified (sensor={self.sensor_name}, value={sensor_value:.6f}, scaled={scaled_value}, ts={event_ts}, nonce={nonce}, latency_ms={latency_ms:.1f}, range_status={range_status})")
                        if result.get("verified") is not None:
                            print(f"     └─ Server: verified={result.get('verified')}, algorithm={result.get('algorithm')}, processing_time_ms={result.get('processing_time_ms', 0):.1f}")

                    return True
                else:
                    # 검증 실패
                    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    scaled_value = int(sensor_value * 1000)
                    reason = result.get("error_message") or result.get("reason") or "unknown"

                    if not self.verbose:
                        # Production 모드: 간결한 에러 로그
                        print(f"[{timestamp}] sensor={self.sensor_name} value={sensor_value:.3f} scaled={scaled_value} result=FAIL latency_ms={latency_ms:.1f} reason={reason}")
                    else:
                        # Test 모드: 상세 에러 로그
                        print(f"[FAIL] Bulletproof verification failed (sensor={self.sensor_name}, value={sensor_value:.6f}, ts={event_ts}, reason={reason})")
                        print(f"       Server response: {json.dumps(result, indent=2)}")

                    return False
            else:
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                print(f"[{timestamp}] sensor={self.sensor_name} result=HTTP_ERROR status={response.status_code}")
                if self.verbose:
                    print(f"       Response: {response.text}")
                return False

        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            print(f"[{timestamp}] sensor={self.sensor_name} result=EXCEPTION error={str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False

    def run(self, interval: float = 1.0, once: bool = False):
        """센서 전송 루프 실행"""
        mode_display = "PRODUCTION" if self.mode == "production" else "TEST"
        print(f"[START] Mode={mode_display}, Interval={interval}s, Once={once}")

        try:
            while True:
                self.send_value()

                if once:
                    print("[DONE] Single transmission completed")
                    break

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[STOP] Stopped by user")


def main():
    parser = argparse.ArgumentParser(description="Sensor Client with Selective Disclosure (Production Ready)")
    parser.add_argument("--server", required=True, help="Bulletproof server URL (e.g., http://192.168.0.11:8085)")
    parser.add_argument("--sensor", required=True, help="Sensor name (e.g., DM-PIT01)")
    parser.add_argument("--reveal-url", default="http://127.0.0.1:9000", help="Reveal server URL (default: http://127.0.0.1:9000)")
    parser.add_argument("--csv", help="CSV file path (optional)")
    parser.add_argument("--interval", type=float, default=2.0, help="Transmission interval in seconds (default: 2.0)")
    parser.add_argument("--once", action="store_true", help="Send once and exit")
    parser.add_argument("--range-min", type=float, default=0.0, help="Minimum valid sensor value (default: 0.0)")
    parser.add_argument("--range-max", type=float, default=4294967.295, help="Maximum valid sensor value (default: 4294967.295)")
    parser.add_argument("--mode", choices=["production", "test"], default="production",
                       help="Operation mode: 'production' (간결한 로그) or 'test' (상세 로그, 기본값: production)")

    args = parser.parse_args()

    print("=" * 70)
    print("  HAI Sensor Client - Selective Disclosure (Production Ready)")
    print("=" * 70)
    print(f"[INIT] Mode: {args.mode.upper()}")
    print(f"[INIT] Bulletproof Server: {args.server}")
    print(f"[INIT] Reveal Server: {args.reveal_url}")
    print(f"[INIT] Sensor: {args.sensor}")
    print(f"[INIT] ZK Mode: ZK_ONLY (RAW 값은 Reveal 서버로 전송)")
    print(f"[INIT] Proof Generation: REAL Bulletproof (secp256k1, n=32)")
    print(f"[INIT] Valid Range: [{args.range_min:.3f}, {args.range_max:.3f}]")
    print(f"[INIT] Scaled Range: [0, {2**32-1}] (after *1000 scaling)")
    print("=" * 70)
    print()

    # 센서 클라이언트 생성
    client = SelectiveDisclosureClient(
        server_url=args.server,
        sensor_name=args.sensor,
        reveal_url=args.reveal_url,
        csv_path=args.csv,
        range_min=args.range_min,
        range_max=args.range_max,
        mode=args.mode
    )

    # 전송 시작
    client.run(interval=args.interval, once=args.once)


if __name__ == "__main__":
    main()

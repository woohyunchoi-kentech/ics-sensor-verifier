#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensor Client for HAI Bulletproof System

Sends sensor values to the server in either RAW or ZK_ONLY mode.
Supports CSV data source or simulated random values.

Dependencies:
    pip3 install requests pandas

Usage:
    # RAW mode
    python sensor_client.py --server http://localhost:8085 --sensor P1_PIT01 --mode RAW --interval 1.0

    # ZK_ONLY mode with proof file
    python sensor_client.py --server http://localhost:8085 --sensor P1_PIT01 --mode ZK_ONLY --proof-file fixtures/sample_proof.json --interval 1.0

    # With CSV data
    python sensor_client.py --server http://localhost:8085 --sensor P1_PIT01 --csv ./HAI/HAI1.csv --mode ZK_ONLY

    # Single transmission
    python sensor_client.py --server http://localhost:8085 --sensor P1_PIT01 --mode RAW --once
"""

import sys
import time
import json
import argparse
import random
import os
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


# Built-in sample proof (valid structure, can be used when --proof-file is not provided)
BUILTIN_SAMPLE_PROOF = {
    "commitment": "034D77548D572A8E965219FFF17F091B3791A2D8523B0057499A40FAC091B4F6AC",
    "proof": {
        "A": "0368F80F288E58E1E42127C928AE9E5CA4EF9BC70AD754D5373FA6832D3D17B4FC",
        "S": "02CC2B44DAE7DA3E24D9E228DC36EFBDBD6C16FB7A527013D8F3DBC2EDEFCD68AC",
        "T1": "03814B852F2FF6D828E7A3F83EABC357AC2090C4ED162199C997A3AD4B04BB4B52",
        "T2": "03EAC7594FD693D586F1DE7C58EE630E71129CF650B0E0516DAAF959F615CA408C",
        "tau_x": "3A377B7A12372A2CE9B7DB5A7702F29D6C30412F2262C766FFDA824133738947",
        "mu": "65CD85652F49E9E4B3E8479AFE37FEFC23633A4E85D2956074C16B9A14AA618C",
        "t": "0D5914402639857A98E1298D30C0DA736EBE7A62907AD2212F42B999619BC402",
        "inner_product_proof": {
            "L": [
                "03EB9F6AB58F504327B57B2BAA4A7D362FEB4393F9780AA09337B1B8681F4D13F5",
                "032C36544EB6F787C3E301912886B8483CE2E998695CEF1C1DEFBAF29D8317FFC6",
                "03267CF28D9CD2E4317A2C13CD2B27D83ACA5CEF83631E43D49A9174E5FB82CF6D",
                "02F15DC6714FF5BED493D91615EB2078CDBAE3E6F222F21D2458EE3C56FD4ED82A",
                "02A7E1D35F6F4C3B8E2D1A9C5F7E3B2D8C4A6F1E9B7D3C5A2F8E1B4D7C9A6E3B5F"
            ],
            "R": [
                "0245B8C9E2D3F1A4B6C8E7D9F2A5B3C7E1D4F8A6B9C2E5D7F3A8B1C4E6D9F2A5AB",
                "03C7E4B2D9F6A3C1E8B5D2F7A4C9E6B3D1F8A5C2E7B4D9F6A3C1E8B5D2F7A4C9EF",
                "029F8E7D6C5B4A3E2D1C9B8A7F6E5D4C3B2A1F9E8D7C6B5A4E3D2C1B9A8F7E6CDA",
                "02D3C2B1A9F8E7D6C5B4A3E2D1C9B8A7F6E5D4C3B2A1F9E8D7C6B5A4E3D2C1B9AB",
                "03F4E3D2C1B9A8F7E6D5C4B3A2E1D9C8B7A6F5E4D3C2B1A9F8E7D6C5B4A3E2D1CD"
            ],
            "a": "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
            "b": "1111111111111111111111111111111111111111111111111111111111111111"
        }
    },
    "challenges": {
        "y": "FBA85BE52776426D547F4B2F2D7DBDFEDAA48D7B906D84AFC3E7FE0EF15C8B7B",
        "z": "DBBED5A53753F44C472B861D1526AE7CF7C059B68AB7C9324CE9F8D3C06AD534",
        "x": "E9791E77ACCE8DA1A6ED0A3C01CDABEC1814878275336C37759136E45BD5CEEA"
    }
}


class SensorClient:
    """Sensor client for transmitting values to verification server"""

    def __init__(self, server_url: str, sensor_name: str, mode: str,
                 proof_data: Optional[Dict] = None, csv_path: Optional[str] = None,
                 compute_challenges: bool = False):
        """
        Initialize sensor client

        Args:
            server_url: Server endpoint URL
            sensor_name: Sensor identifier
            mode: "ZK_ONLY" or "RAW"
            proof_data: Proof template (if None, uses builtin sample)
            csv_path: Path to CSV file (if None, simulates random values)
            compute_challenges: If True, compute and include FS challenges in request
        """
        self.server_url = server_url.rstrip('/')
        self.sensor_name = sensor_name
        self.mode = mode.upper()
        self.proof_template = proof_data if proof_data else BUILTIN_SAMPLE_PROOF
        self.csv_path = csv_path
        self.compute_challenges = compute_challenges

        # CSV data
        self.csv_data = None
        self.csv_index = 0

        if self.mode not in ["ZK_ONLY", "RAW"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'ZK_ONLY' or 'RAW'")

        # Load CSV if provided
        if csv_path:
            if not PANDAS_AVAILABLE:
                raise RuntimeError("CSV mode requires pandas. Install with: pip3 install pandas")
            self._load_csv()

        print(f"[INIT] Sensor Client")
        print(f"  Server: {self.server_url}")
        print(f"  Sensor: {self.sensor_name}")
        print(f"  Mode: {self.mode}")
        print(f"  Data source: {'CSV' if csv_path else 'Simulated'}")
        if self.mode == "ZK_ONLY":
            print(f"  Proof: {'Loaded' if proof_data else 'Built-in sample'}")
            print(f"  Compute FS challenges: {'Yes' if compute_challenges else 'No (server-side)'}")

    def _load_csv(self):
        """Load CSV data"""
        try:
            self.csv_data = pd.read_csv(self.csv_path)
            if self.sensor_name not in self.csv_data.columns:
                available = [col for col in self.csv_data.columns if col.startswith('P')][:5]
                raise ValueError(f"Sensor '{self.sensor_name}' not in CSV. Available: {available}")
            print(f"  CSV rows: {len(self.csv_data)}")
            print(f"  Value range: [{self.csv_data[self.sensor_name].min():.3f}, {self.csv_data[self.sensor_name].max():.3f}]")
        except Exception as e:
            raise RuntimeError(f"Failed to load CSV: {e}")

    def _get_sensor_value(self) -> float:
        """
        Get next sensor value from CSV or simulation

        Returns:
            Sensor value (float)
        """
        if self.csv_data is not None:
            # Read from CSV
            if self.csv_index >= len(self.csv_data):
                self.csv_index = 0  # Loop
            value = float(self.csv_data[self.sensor_name].iloc[self.csv_index])
            self.csv_index += 1
            return value
        else:
            # Simulate: normal distribution (mean=5, std=2)
            return max(0.0, random.gauss(5.0, 2.0))

    def _generate_nonce(self) -> str:
        """Generate 12-byte hex nonce"""
        return ''.join(random.choices('0123456789ABCDEF', k=24))

    def _compute_fiat_shamir_challenges(self) -> Dict[str, str]:
        """
        Compute Fiat-Shamir challenges for cross-verification

        Rules:
            y = H(domain||n||A||S)
            z = H(domain||n||A||S||y)
            x = H(domain||n||T1||T2||z)

        Returns:
            Dictionary with y, z, x challenges (64 hex chars each)
        """
        domain = "ICS_BULLETPROOF_VERIFIER_v1"
        n = 32

        proof = self.proof_template.get("proof", {})
        A = proof.get("A", "")
        S = proof.get("S", "")
        T1 = proof.get("T1", "")
        T2 = proof.get("T2", "")

        # y = H(domain||n||A||S)
        h_y = hashlib.sha256()
        h_y.update(domain.encode('utf-8'))
        h_y.update(n.to_bytes(4, 'big'))
        h_y.update(bytes.fromhex(A))
        h_y.update(bytes.fromhex(S))
        y = h_y.hexdigest().upper()

        # z = H(domain||n||A||S||y)
        h_z = hashlib.sha256()
        h_z.update(domain.encode('utf-8'))
        h_z.update(n.to_bytes(4, 'big'))
        h_z.update(bytes.fromhex(A))
        h_z.update(bytes.fromhex(S))
        h_z.update(bytes.fromhex(y))
        z = h_z.hexdigest().upper()

        # x = H(domain||n||T1||T2||z)
        h_x = hashlib.sha256()
        h_x.update(domain.encode('utf-8'))
        h_x.update(n.to_bytes(4, 'big'))
        h_x.update(bytes.fromhex(T1))
        h_x.update(bytes.fromhex(T2))
        h_x.update(bytes.fromhex(z))
        x = h_x.hexdigest().upper()

        return {
            "y": y,
            "z": z,
            "x": x
        }

    def _build_request(self, sensor_value: float) -> Dict[str, Any]:
        """
        Build request JSON

        Args:
            sensor_value: Sensor reading

        Returns:
            Request dictionary
        """
        ts = int(time.time())
        nonce = self._generate_nonce()

        # Common fields
        request = {
            "mode": self.mode,
            "sensor": self.sensor_name,
            "ts": ts,
            "nonce": nonce,
            "type": "sensor_value",
            "range_min": 0,
            "range_max": 4294967295,
            "metadata": {
                "domain": "ICS_BULLETPROOF_VERIFIER_v1",
                "n": 32,
                "encoding": "secp256k1-compressed-hex",
                "client": "sensor_client.py"
            }
        }

        # Convert sensor value to 64-char hex (32 bytes, big-endian)
        scaled_value = int(sensor_value * 1000)
        value_hex = format(scaled_value, '064x')  # 64 hex chars (32 bytes)

        # ZK_ONLY: add cryptographic proof and opening
        if self.mode == "ZK_ONLY":
            request["commitment"] = self.proof_template.get("commitment", "")
            request["proof"] = self.proof_template.get("proof", {})
            request["opening"] = {
                "x": value_hex,  # 64-char hex
                "r": "0" * 64  # Placeholder 32-byte hex
            }
            # Include challenges if compute_challenges is enabled (for cross-verification)
            if self.compute_challenges:
                request["challenges"] = self._compute_fiat_shamir_challenges()
        else:
            # RAW mode: include dummy commitment and opening for server schema
            request["commitment"] = "02" + "0" * 64  # Dummy 33-byte compressed point
            request["opening"] = {
                "x": value_hex,  # 64-char hex
                "r": "0" * 64
            }
            request["raw_value"] = sensor_value

        return request

    def send_value(self, sensor_value: float) -> bool:
        """
        Send sensor value to server

        Args:
            sensor_value: Sensor reading

        Returns:
            True if successful, False otherwise
        """
        request_data = self._build_request(sensor_value)
        endpoint = f"{self.server_url}/api/v1/verify/bulletproof"

        try:
            response = requests.post(endpoint, json=request_data, timeout=10)
            status_code = response.status_code

            # Check for success
            if status_code == 200:
                try:
                    result = response.json()
                    if result.get("ok") == True or result.get("verified") == True:
                        print(f"[✅ OK] sensor={self.sensor_name} value={sensor_value:.3f}")
                        return True
                    else:
                        body_preview = json.dumps(result)[:180]
                        print(f"[⚠️ FAIL] sensor={self.sensor_name} value={sensor_value:.3f} body={body_preview}")
                        return False
                except json.JSONDecodeError:
                    body_preview = response.text[:180]
                    print(f"[⚠️ FAIL] sensor={self.sensor_name} value={sensor_value:.3f} body={body_preview}")
                    return False
            else:
                body_preview = response.text[:180]
                print(f"[⚠️ FAIL] sensor={self.sensor_name} value={sensor_value:.3f} code={status_code} body={body_preview}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[⚠️ FAIL] sensor={self.sensor_name} value={sensor_value:.3f} error={str(e)[:180]}")
            return False
        except Exception as e:
            print(f"[⚠️ FAIL] sensor={self.sensor_name} value={sensor_value:.3f} exception={str(e)[:180]}")
            return False

    def run(self, interval: float = 1.0, once: bool = False):
        """
        Run sensor transmission loop

        Args:
            interval: Time between transmissions (seconds)
            once: If True, send only once and exit
        """
        print(f"\n[START] Transmission loop (interval={interval}s, once={once})")
        print("=" * 60)

        iteration = 0
        try:
            while True:
                iteration += 1
                sensor_value = self._get_sensor_value()
                self.send_value(sensor_value)

                if once:
                    print(f"\n[DONE] Single transmission completed")
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n[STOP] User interrupted after {iteration} transmissions")
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()


def load_proof_file(filepath: str) -> Dict:
    """
    Load proof JSON from file

    Args:
        filepath: Path to proof JSON file

    Returns:
        Proof dictionary
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            print(f"[LOAD] Proof file: {filepath}")
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"Proof file not found: {filepath}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in proof file: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Sensor Client for HAI Bulletproof System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # RAW mode (plaintext)
  python sensor_client.py --server http://192.168.0.11:8085 --sensor P1_PIT01 --mode RAW --interval 1.0

  # ZK_ONLY mode with built-in proof
  python sensor_client.py --server http://192.168.0.11:8085 --sensor P1_PIT01 --mode ZK_ONLY

  # ZK_ONLY mode with custom proof file
  python sensor_client.py --server http://192.168.0.11:8085 --sensor P1_PIT01 --mode ZK_ONLY --proof-file fixtures/sample_proof.json

  # Using CSV data
  python sensor_client.py --server http://192.168.0.11:8085 --sensor P1_PIT01 --csv ./data/HAI1.csv --mode ZK_ONLY

  # Single transmission
  python sensor_client.py --server http://192.168.0.11:8085 --sensor P1_PIT01 --mode RAW --once
        """
    )

    parser.add_argument("--server", required=True,
                        help="Server URL (e.g., http://192.168.0.11:8085)")
    parser.add_argument("--sensor", required=True,
                        help="Sensor name (e.g., P1_PIT01)")
    parser.add_argument("--mode", choices=["ZK_ONLY", "RAW"], default="ZK_ONLY",
                        help="Transmission mode: ZK_ONLY (with proof) or RAW (plaintext)")
    parser.add_argument("--proof-file", default=None,
                        help="Path to proof JSON file (ZK_ONLY mode). Uses built-in sample if not provided.")
    parser.add_argument("--csv", default=None,
                        help="Path to CSV file with sensor data. If not provided, simulates random values.")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Time interval between transmissions in seconds (default: 1.0)")
    parser.add_argument("--once", action="store_true",
                        help="Send only one transmission and exit")
    parser.add_argument("--compute-challenges", action="store_true",
                        help="Compute and include Fiat-Shamir challenges for cross-verification (ZK_ONLY mode only)")

    args = parser.parse_args()

    print("=" * 60)
    print("HAI Sensor Client")
    print("=" * 60)

    # Load proof if ZK_ONLY and file provided
    proof_data = None
    if args.mode == "ZK_ONLY" and args.proof_file:
        try:
            proof_data = load_proof_file(args.proof_file)
        except Exception as e:
            print(f"[ERROR] Failed to load proof file: {e}")
            print(f"[INFO] Using built-in sample proof instead")
            proof_data = None

    # Check CSV availability
    if args.csv and not PANDAS_AVAILABLE:
        print(f"[ERROR] CSV mode requires pandas library")
        print(f"[INFO] Install with: pip3 install pandas")
        return 1

    # Create client
    try:
        client = SensorClient(
            server_url=args.server,
            sensor_name=args.sensor,
            mode=args.mode,
            proof_data=proof_data,
            csv_path=args.csv,
            compute_challenges=args.compute_challenges
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return 1

    # Run transmission loop
    try:
        client.run(interval=args.interval, once=args.once)
    except Exception as e:
        print(f"[ERROR] Client error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

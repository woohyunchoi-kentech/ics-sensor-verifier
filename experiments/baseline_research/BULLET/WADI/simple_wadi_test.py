#!/usr/bin/env python3
"""
WADI BulletProof 간단 테스트 - 성공 패턴 사용
"""

import requests
import json
import time

def test_simple_bulletproof():
    """간단한 BulletProof 테스트"""
    print("=== WADI 간단 BulletProof 테스트 ===")

    # HAI에서 성공한 패턴 사용
    proof_data = {
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
                "L": [
                    "02a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef12345678",
                    "03b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef123456789a",
                    "02c3d4e5f67890abcdef1234567890abcdef1234567890abcdef123456789abc",
                    "03d4e5f67890abcdef1234567890abcdef1234567890abcdef123456789abcd",
                    "02e5f67890abcdef1234567890abcdef1234567890abcdef123456789abcde"
                ],
                "R": [
                    "03f67890abcdef1234567890abcdef1234567890abcdef123456789abcdef1",
                    "0267890abcdef1234567890abcdef1234567890abcdef123456789abcdef12",
                    "037890abcdef1234567890abcdef1234567890abcdef123456789abcdef123",
                    "02890abcdef1234567890abcdef1234567890abcdef123456789abcdef1234",
                    "0390abcdef1234567890abcdef1234567890abcdef123456789abcdef12345"
                ],
                "a": "56819823",
                "b": "82cbfc54"
            }
        },
        "range_min": 0,
        "range_max": 4294967295,
        "sensor_name": "WADI_TEST_001",
        "sensor_value": 1234
    }

    print("성공 패턴 증명 구조로 테스트...")

    try:
        start_time = time.perf_counter()

        response = requests.post(
            'http://192.168.0.11:8085/api/v1/verify/bulletproof',
            json=proof_data,
            timeout=10
        )

        end_time = time.perf_counter()
        response_time = (end_time - start_time) * 1000

        print(f"서버 응답 시간: {response_time:.3f}ms")
        print(f"HTTP 상태: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"응답: {json.dumps(result, indent=2)}")

            if result.get('success', False):
                print("✅ BulletProof 서버 연결 성공!")
                return True
            else:
                print("❌ 서버 연결되지만 검증 실패")
                return False
        else:
            print(f"❌ 서버 오류: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

def run_mini_experiment():
    """작은 실험 (조건 1개만)"""
    print("\n=== 미니 실험 (1센서 × 1Hz × 10개 요청) ===")

    success_count = 0
    total_requests = 10

    for i in range(total_requests):
        print(f"요청 {i+1}/{total_requests}...")

        # 간단한 증명 데이터 (센서 값만 변경)
        proof_data = {
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
            "range_max": 4294967295,
            "sensor_name": f"WADI_001_{i+1:03d}",
            "sensor_value": 1000 + i * 10  # 센서 값 변경
        }

        try:
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof_data,
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    success_count += 1
                    print(f"  ✅ 성공")
                else:
                    print(f"  ❌ 검증 실패")
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")

        except Exception as e:
            print(f"  ❌ 요청 실패: {e}")

        time.sleep(1)  # 1Hz

    success_rate = success_count / total_requests * 100
    print(f"\n미니 실험 결과: {success_count}/{total_requests} 성공 ({success_rate:.1f}%)")

    if success_rate >= 80:
        print("🎉 미니 실험 성공! 본격 실험 준비 완료")
        return True
    else:
        print("⚠️ 미니 실험 실패. 추가 디버깅 필요")
        return False

def main():
    """메인 함수"""
    print("WADI BulletProof 간단 테스트 시작\n")

    # 1. 단일 테스트
    single_test = test_simple_bulletproof()

    if single_test:
        # 2. 미니 실험
        mini_experiment = run_mini_experiment()

        if mini_experiment:
            print("\n✅ 모든 테스트 성공! 체크리스트대로 실험 가능합니다.")
        else:
            print("\n❌ 미니 실험 실패")
    else:
        print("\n❌ 기본 연결 실패")

if __name__ == "__main__":
    main()
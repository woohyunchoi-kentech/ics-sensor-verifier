#!/usr/bin/env python3
"""
WADI BulletProofs 초고속 테스트
각 조건당 10개씩만 테스트해서 시간 추정
"""

import time
import requests
import numpy as np
from datetime import datetime

def quick_test():
    print("⚡ WADI BulletProofs 초고속 테스트")
    print("📋 16조건 × 10요청 = 160개 (시간 추정용)")

    server_url = "http://192.168.0.11:8085/api/v1/verify/bulletproof"

    # 성공 패턴 템플릿
    proof_template = {
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

    sensor_counts = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]

    condition_times = []
    condition_id = 1

    for sensor_count in sensor_counts:
        print(f"\n📊 {sensor_count}센서:")

        for frequency in frequencies:
            start_time = datetime.now()

            delay = 1.0 / frequency
            print(f"  조건 {condition_id:2d}: {frequency:3d}Hz (간격: {delay:.3f}초)", end=" → ")

            successes = 0
            total_time = 0

            # 10개 요청만 테스트
            for i in range(10):
                if i > 0:
                    time.sleep(delay)

                try:
                    request_start = time.perf_counter()

                    request_data = proof_template.copy()
                    request_data["sensor_name"] = f"TEST_{sensor_count}_{i+1}"
                    request_data["sensor_value"] = 1000 + i

                    response = requests.post(server_url, json=request_data, timeout=5)

                    if response.status_code == 200:
                        successes += 1

                    request_end = time.perf_counter()
                    total_time += (request_end - request_start) * 1000

                except Exception as e:
                    print(f"오류: {e}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            success_rate = successes / 10 * 100
            avg_time = total_time / 10

            print(f"성공률: {success_rate:5.0f}%, 평균: {avg_time:6.1f}ms, 소요: {duration:5.1f}초")

            condition_times.append(duration)
            condition_id += 1

    # 시간 추정
    total_test_time = sum(condition_times)
    avg_condition_time = total_test_time / 16

    print(f"\n📈 === 시간 추정 결과 ===")
    print(f"10개 요청 총 시간: {total_test_time/60:.1f}분")
    print(f"조건당 평균 시간: {avg_condition_time:.1f}초")

    # 1000개 요청 시간 추정
    estimated_1000_per_condition = avg_condition_time * 100  # 10 → 1000 (100배)
    estimated_total_1000 = estimated_1000_per_condition * 16 / 60  # 16조건, 분

    print(f"\n⏰ 1000개 요청 예상 시간:")
    print(f"조건당 평균: {estimated_1000_per_condition/60:.1f}분")
    print(f"전체 16조건: {estimated_total_1000:.0f}분 (~{estimated_total_1000/60:.1f}시간)")

    # 현실적인 추천
    if estimated_total_1000 < 60:  # 1시간 미만
        print(f"\n🎉 1000개 요청 실험 가능! (~{estimated_total_1000:.0f}분)")
        print(f"🚀 지금 바로 1000개 요청 실험을 시작하시겠습니까?")
    elif estimated_total_1000 < 180:  # 3시간 미만
        print(f"\n⚠️ 시간이 오래 걸립니다 (~{estimated_total_1000/60:.1f}시간)")
        print(f"💡 대신 100개 요청으로 시작하시겠습니까? (예상: {estimated_total_1000/10:.0f}분)")
    else:
        print(f"\n❌ 너무 오래 걸립니다 (~{estimated_total_1000/60:.1f}시간)")
        print(f"💡 100개 요청 실험을 추천합니다 (예상: {estimated_total_1000/10:.0f}분)")

if __name__ == "__main__":
    quick_test()
#!/usr/bin/env python3
"""
WADI BulletProof 연결 테스트
"""

import sys
import time
import json
import requests
from datetime import datetime

# HAI 디렉토리에서 Bulletproof 생성기 임포트
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI')
from real_bulletproof_library import RealBulletproofLibrary
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256
import secrets

def test_single_bulletproof():
    """단일 BulletProof 테스트"""
    print("=== WADI BulletProof 단일 테스트 ===")

    # 1. BulletProof 생성기 초기화
    group = EcGroup(714)  # secp256k1
    g = group.generator()
    order = group.order()

    # H 생성
    g_bytes = g.export()
    h_hash = sha256(g_bytes + b"bulletproof_h").digest()
    h_scalar = Bn.from_binary(h_hash) % order
    h = h_scalar * g

    print("BulletProof 생성기 초기화 완료")

    # 2. 테스트 값
    test_value = 1234  # WADI 센서 값 시뮬레이션
    r = Bn.from_decimal(str(secrets.randbelow(int(str(order)))))
    v = Bn(test_value)

    # 3. Commitment 생성
    commitment_start = time.perf_counter()
    commitment = v * g + r * h
    commitment_end = time.perf_counter()
    commitment_time = (commitment_end - commitment_start) * 1000

    print(f"Commitment 생성 완료: {commitment_time:.3f}ms")

    # 4. BulletProof 생성
    bulletproof_start = time.perf_counter()
    try:
        bulletproof_gen = RealBulletproofLibrary(32)
        proof = bulletproof_gen.prove_range(test_value, r)
        bulletproof_end = time.perf_counter()
        bulletproof_time = (bulletproof_end - bulletproof_start) * 1000

        print(f"BulletProof 생성 완료: {bulletproof_time:.3f}ms")

        # 증명 크기 계산
        proof_data = {
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
        }

        proof_size = len(json.dumps(proof_data))
        print(f"증명 크기: {proof_size} bytes")

    except Exception as e:
        print(f"BulletProof 생성 실패: {e}")
        return False

    # 5. 서버 검증 테스트
    verification_start = time.perf_counter()

    payload = {
        'sensor_id': 'WADI_TEST_001',
        'sensor_value': test_value,
        'timestamp': time.time(),
        'commitment': commitment.export().hex(),
        'bulletproof': proof_data
    }

    try:
        response = requests.post(
            'http://192.168.0.11:8085/api/v1/verify/bulletproof',
            json=payload,
            timeout=10
        )

        verification_end = time.perf_counter()
        verification_time = (verification_end - verification_start) * 1000

        print(f"서버 응답 시간: {verification_time:.3f}ms")
        print(f"HTTP 상태: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"검증 결과: {result}")

            if result.get('verified', False):
                print("✅ BulletProof 검증 성공!")
                return True
            else:
                print("❌ BulletProof 검증 실패")
                return False
        else:
            print(f"❌ 서버 오류: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_wadi_data_loading():
    """WADI 데이터 로딩 테스트"""
    print("\n=== WADI 데이터 로딩 테스트 ===")

    try:
        import pandas as pd
        import numpy as np

        wadi_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv"
        df = pd.read_csv(wadi_path, nrows=100)  # 첫 100행만 테스트

        print(f"WADI 데이터 로드 성공: {df.shape}")

        # 센서 컬럼 식별
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_patterns = ['time', 'timestamp', 'label', 'attack', 'normal', 'row']
        sensor_columns = [col for col in numeric_columns
                         if not any(pattern.lower() in col.lower() for pattern in exclude_patterns)]

        print(f"센서 컬럼 수: {len(sensor_columns)}")
        print(f"센서 컬럼 샘플: {sensor_columns[:5]}")

        # 샘플 센서 값 추출
        if sensor_columns:
            sample_sensor = sensor_columns[0]
            sample_values = df[sample_sensor].dropna().head(5)
            print(f"'{sample_sensor}' 샘플 값: {list(sample_values)}")

            # 정규화 테스트
            for val in sample_values:
                normalized = max(0, min(int(abs(val * 1000)), (1 << 32) - 1))
                print(f"  {val} → {normalized}")

        return True

    except Exception as e:
        print(f"❌ WADI 데이터 로딩 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("WADI BulletProof 시스템 테스트 시작\n")

    # 1. WADI 데이터 로딩 테스트
    data_test = test_wadi_data_loading()

    # 2. BulletProof 단일 테스트
    bulletproof_test = test_single_bulletproof()

    # 결과 요약
    print(f"\n=== 테스트 결과 요약 ===")
    print(f"WADI 데이터 로딩: {'✅ 성공' if data_test else '❌ 실패'}")
    print(f"BulletProof 검증: {'✅ 성공' if bulletproof_test else '❌ 실패'}")

    if data_test and bulletproof_test:
        print("\n🎉 모든 테스트 통과! 본격적인 실험 준비 완료")
        return True
    else:
        print("\n⚠️  일부 테스트 실패. 문제 해결 후 재시도하세요.")
        return False

if __name__ == "__main__":
    main()
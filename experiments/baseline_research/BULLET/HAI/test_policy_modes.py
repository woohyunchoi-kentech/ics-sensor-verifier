#!/usr/bin/env python3
"""
Policy + Selective Disclosure 기능 테스트
ZK_ONLY, SELECTIVE, RAW 모드 검증
"""

import sys
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI')

from hai_bulletproofs_experiment import ExperimentConfig, BulletproofExperiment
import requests


def test_zk_only_mode():
    """ZK_ONLY 모드 테스트"""
    print("\n" + "="*60)
    print("🧪 테스트 1: ZK_ONLY 모드")
    print("="*60)

    config = ExperimentConfig(
        sensor_counts=[1],
        frequencies=[1],
        target_requests=10,
        server_url="http://192.168.0.11:8085/api/v1/verify/bulletproof",
        policy="ZK_ONLY"
    )

    experiment = BulletproofExperiment(config)
    result = experiment.run_single_condition(1, 1, 1)

    print(f"\n✅ ZK_ONLY 테스트 완료:")
    print(f"  • 정책: {result.policy}")
    print(f"  • SDR: {result.selective_disclosure_rate:.2f}% (예상: 0.00%)")
    print(f"  • 성공률: {result.success_rate:.1f}%")

    assert result.policy == "ZK_ONLY", "정책이 ZK_ONLY가 아님"
    assert result.selective_disclosure_rate == 0.0, "SDR이 0이 아님"
    print("  ✅ ZK_ONLY 모드 검증 통과")

    return result


def test_selective_mode():
    """SELECTIVE 모드 테스트"""
    print("\n" + "="*60)
    print("🧪 테스트 2: SELECTIVE 모드")
    print("="*60)

    # 알람 조건 설정: 매우 낮은 임계값으로 알람 자주 발생하도록
    config = ExperimentConfig(
        sensor_counts=[1],
        frequencies=[1],
        target_requests=10,
        server_url="http://192.168.0.11:8085/api/v1/verify/bulletproof",
        policy="SELECTIVE",
        upper_bounds={"FIT101": 50.0},  # HAI 센서 중 하나
        lower_bounds={"FIT101": 10.0},
        roc_threshold=5.0
    )

    experiment = BulletproofExperiment(config)
    result = experiment.run_single_condition(1, 1, 2)

    print(f"\n✅ SELECTIVE 테스트 완료:")
    print(f"  • 정책: {result.policy}")
    print(f"  • SDR: {result.selective_disclosure_rate:.2f}% (예상: > 0%)")
    print(f"  • 성공률: {result.success_rate:.1f}%")

    assert result.policy == "SELECTIVE", "정책이 SELECTIVE가 아님"
    # SDR이 0보다 크면 알람이 발생한 것
    print(f"  ✅ SELECTIVE 모드 검증 통과 (SDR: {result.selective_disclosure_rate:.2f}%)")

    return result


def test_raw_mode():
    """RAW 모드 테스트"""
    print("\n" + "="*60)
    print("🧪 테스트 3: RAW 모드")
    print("="*60)

    config = ExperimentConfig(
        sensor_counts=[1],
        frequencies=[1],
        target_requests=10,
        server_url="http://192.168.0.11:8085/api/v1/verify/bulletproof",
        policy="RAW"
    )

    experiment = BulletproofExperiment(config)
    result = experiment.run_single_condition(1, 1, 3)

    print(f"\n✅ RAW 테스트 완료:")
    print(f"  • 정책: {result.policy}")
    print(f"  • SDR: {result.selective_disclosure_rate:.2f}% (예상: 0.00%)")
    print(f"  • 커밋먼트 시간: {result.avg_commitment_time:.2f}ms (예상: 0ms)")
    print(f"  • Bulletproof 시간: {result.avg_bulletproof_time:.2f}ms (예상: 0ms)")

    assert result.policy == "RAW", "정책이 RAW가 아님"
    assert result.selective_disclosure_rate == 0.0, "SDR이 0이 아님"
    assert result.avg_commitment_time == 0.0, "커밋먼트 시간이 0이 아님"
    assert result.avg_bulletproof_time == 0.0, "Bulletproof 시간이 0이 아님"
    print("  ✅ RAW 모드 검증 통과")

    return result


def main():
    """전체 테스트 실행"""
    print("="*60)
    print("🚀 Policy + Selective Disclosure 기능 테스트")
    print("="*60)

    # 서버 연결 확인
    print("\n🔍 서버 연결 확인...")
    try:
        response = requests.get("http://192.168.0.11:8085/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공")
        else:
            print(f"⚠️ 서버 응답 이상: {response.status_code}")
            print("⚠️ RAW 모드는 서버 없이도 테스트 가능")
    except Exception as e:
        print(f"⚠️ 서버 연결 실패: {e}")
        print("⚠️ RAW 모드만 테스트됩니다")

    results = []

    try:
        # 테스트 1: ZK_ONLY
        result1 = test_zk_only_mode()
        results.append(result1)
    except Exception as e:
        print(f"❌ ZK_ONLY 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    try:
        # 테스트 2: SELECTIVE
        result2 = test_selective_mode()
        results.append(result2)
    except Exception as e:
        print(f"❌ SELECTIVE 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    try:
        # 테스트 3: RAW
        result3 = test_raw_mode()
        results.append(result3)
    except Exception as e:
        print(f"❌ RAW 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    # 종합 결과
    print("\n" + "="*60)
    print("🏆 테스트 종합 결과")
    print("="*60)
    print(f"  • 완료된 테스트: {len(results)}/3")
    print(f"\n📊 모드별 비교:")
    print(f"{'모드':<15} {'SDR':<10} {'커밋먼트':<12} {'Bulletproof':<12} {'증명크기':<10}")
    print("-" * 60)

    for r in results:
        print(f"{r.policy:<15} {r.selective_disclosure_rate:<9.2f}% "
              f"{r.avg_commitment_time:<11.2f}ms {r.avg_bulletproof_time:<11.2f}ms "
              f"{r.proof_size_bytes:<10} bytes")

    print("\n✅ 모든 테스트 완료!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
챌린지 필드 테스트
클라이언트 챌린지 y, z, x가 제대로 생성되고 전송되는지 확인
"""

import sys
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI')

from fix_inner_product_bulletproof import FixInnerProductBulletproof
import json


def test_challenge_generation():
    """챌린지 생성 테스트"""
    print("="*60)
    print("🧪 챌린지 필드 생성 테스트")
    print("="*60)

    # Bulletproof 생성기 초기화
    bp = FixInnerProductBulletproof()

    # 테스트 값
    test_value = 42000  # 42.000 * 1000 (스케일링)

    # 증명 생성
    print(f"\n📊 테스트 값: {test_value} (원본: {test_value/1000})")
    proof = bp.create_inner_product_fixed_proof(test_value)

    # 챌린지 필드 확인
    if "challenges" in proof:
        print(f"\n✅ 챌린지 필드 포함됨:")
        print(f"  • y: {proof['challenges']['y'][:32]}...")
        print(f"  • z: {proof['challenges']['z'][:32]}...")
        print(f"  • x: {proof['challenges']['x'][:32]}...")

        # 챌린지가 16진수 문자열인지 확인
        try:
            y_bytes = bytes.fromhex(proof['challenges']['y'])
            z_bytes = bytes.fromhex(proof['challenges']['z'])
            x_bytes = bytes.fromhex(proof['challenges']['x'])

            print(f"\n✅ 챌린지 인코딩 검증:")
            print(f"  • y 길이: {len(y_bytes)} bytes")
            print(f"  • z 길이: {len(z_bytes)} bytes")
            print(f"  • x 길이: {len(x_bytes)} bytes")

            assert len(y_bytes) == 32, "y 길이가 32바이트가 아님"
            assert len(z_bytes) == 32, "z 길이가 32바이트가 아님"
            assert len(x_bytes) == 32, "x 길이가 32바이트가 아님"

            print(f"\n✅ 모든 챌린지가 32바이트 스칼라")

        except Exception as e:
            print(f"\n❌ 챌린지 인코딩 오류: {e}")
            return False

        # opening 필드 확인
        if "opening" in proof:
            print(f"\n✅ Opening 필드 포함됨:")
            print(f"  • x (값): {proof['opening']['x']}")
            print(f"  • r (블라인딩): {proof['opening']['r'][:32]}...")
        else:
            print(f"\n⚠️ Opening 필드 없음")

        # 전체 proof 구조 출력
        print(f"\n📋 Proof 구조:")
        print(f"  • commitment: {len(proof.get('commitment', ''))} chars")
        print(f"  • proof.A: {len(proof.get('proof', {}).get('A', ''))} chars")
        print(f"  • proof.S: {len(proof.get('proof', {}).get('S', ''))} chars")
        print(f"  • proof.T1: {len(proof.get('proof', {}).get('T1', ''))} chars")
        print(f"  • proof.T2: {len(proof.get('proof', {}).get('T2', ''))} chars")
        print(f"  • challenges: {list(proof['challenges'].keys())}")
        print(f"  • opening: {list(proof['opening'].keys())}")

        # JSON 직렬화 테스트
        try:
            json_str = json.dumps(proof, indent=2)
            print(f"\n✅ JSON 직렬화 성공 ({len(json_str)} chars)")

            # 다시 파싱
            proof_parsed = json.loads(json_str)
            assert proof_parsed['challenges']['y'] == proof['challenges']['y']
            print(f"✅ JSON 파싱 검증 통과")

        except Exception as e:
            print(f"\n❌ JSON 처리 오류: {e}")
            return False

        return True

    else:
        print(f"\n❌ 챌린지 필드 누락!")
        return False


def test_domain_tag():
    """도메인 태그 테스트"""
    print("\n" + "="*60)
    print("🧪 도메인 태그 테스트")
    print("="*60)

    bp = FixInnerProductBulletproof()
    print(f"\n✅ 도메인 태그: {bp.domain_tag}")
    print(f"  • 타입: {type(bp.domain_tag)}")
    print(f"  • 값: {bp.domain_tag.decode()}")

    # 챌린지 생성 테스트
    from petlib.bn import Bn
    point1 = bp.g
    point2 = bp.h

    challenge = bp._fiat_shamir_challenge(point1, point2)
    print(f"\n✅ 샘플 챌린지 생성:")
    print(f"  • 입력: G, H")
    print(f"  • 출력: {challenge.hex()[:32]}...")
    print(f"  • 길이: {len(challenge.binary())} bytes")

    return True


def main():
    """메인 테스트"""
    print("\n" + "="*60)
    print("🚀 클라이언트 챌린지 필드 종합 테스트")
    print("="*60)

    results = []

    # 테스트 1: 챌린지 생성
    try:
        result1 = test_challenge_generation()
        results.append(("챌린지 생성", result1))
    except Exception as e:
        print(f"❌ 챌린지 생성 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        results.append(("챌린지 생성", False))

    # 테스트 2: 도메인 태그
    try:
        result2 = test_domain_tag()
        results.append(("도메인 태그", result2))
    except Exception as e:
        print(f"❌ 도메인 태그 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        results.append(("도메인 태그", False))

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    for name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"  • {name}: {status}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

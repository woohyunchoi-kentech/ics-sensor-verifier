#!/usr/bin/env python3
"""
골든 벡터 기반 IPP 트레이스 생성 및 서버 전송
서버와 동일한 증명으로 IPP compare 테스트 수행
"""

import json
import hashlib
import requests
from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn

# secp256k1 curve
GROUP = EcGroup(714)
ORDER = GROUP.order()

# 골든 벡터 데이터
GOLDEN_VECTOR = {
    "version": "v1.0",
    "description": "Golden vector for Bulletproof verification regression test",
    "source": "debug_proof_CURRENT_DM-FT03.json (local verification passed)",
    "created": "2025-11-27",
    "domain": "ICS_BULLETPROOF_VERIFIER_v1",
    "bit_length": 32,
    "commitment": "029A0B3EF46FC355D46AB3968D142874C1F80A0A3C063FBD06A35C990568F2535C",
    "proof": {
        "A": "0388EFA223C8D86306A12363E20F133DA7D1F538815E4F7467542EFADBCA204248",
        "S": "02D3012CFB9DE0E785E37D6C03C54FC4BAA235B1175CB0378F29A20FA65ABF9027",
        "T1": "0258EB66B30AE0B0CAD5FB5DB7870933F8A7C7164C469AA2E5FE792A5FB38C92DA",
        "T2": "03C92827E101222467B90A719EE1341F429D8430417F8D003C2AB1594514BBEAD7",
        "tau_x": "29113AC44F434968145DEEACA020DD606A8E76283AB8F10CCC4516C57A939B8E",
        "mu": "9BADEB7C244A1442973D07CF309D71B46D05029E12586FADC1458C0A2F83FA78",
        "t": "B90386AFED96B7F7E3BF21B91EAD158446557798695FE62016FBDA4F37DA56F2",
        "inner_product_proof": {
            "L": [
                "0289874359051F2DB2063EEFC4A16F40E9B95C7A58180844943D8CB401BE15166F",
                "03E6F2B0DFBD51FE65786BD52D5B48BFB8D9431D4BFFDBC01252BE58EB00A65BCC",
                "027D997CC37B54E8D8C805BC8C6D7FF00851D09A52E601EB8A3CA50370EC0091CB",
                "02FB16B5C04F3646853DCCB8D4405DD366CC7083D6BD4383CF0388CE1375AD92F6",
                "029929F87464CB955B62A8277D7AA336B4E1D478680A3290C217D60090743A3D89"
            ],
            "R": [
                "02875686CB22177538D9A33DC9262B13E81CFBA126FC099F12D0E2B3697BD222A8",
                "02F35FC1AC8635632E08B0D926CB8E4A755530B6F317682230F024BD17BF698B81",
                "03D4D7E359267F23D341B111E19021835DC5E6DF4454125CD709E809BF52A60E74",
                "0236CEC51EDE9C80E565DF536D49DC2EFE2C761F7D1504622C2C9400AD8B4EE6AF",
                "0367276E55802B0BC4A7A30AE889AC86B7879B8D5A63536E8F10FFDF93AA7D7268"
            ],
            "a": "1B4A4574C3EF1221885478948947D2466AD691C901CA85E6DDBBB2EE5D14CEB7",
            "b": "D14BEA4F2B8C922E50A039F339AB2608211C94C535767564F7A1596FDA3B8C3D"
        }
    },
    "range_min": 0,
    "range_max": 4294967295,
    "expected_scalars": {
        "value": 206794,
        "y": "92BEE47A737894653311C5EED191996BDA6912077E697B0B8665E7FF95CA6C3C",
        "z": "FF3E4DC8658902B1916EC185C43DEE6B27B692924A6185503668F239B29F445F",
        "x": "052098D6C28940EEF8ADD7D35DF66B612CDE64493DACC585654E4BCABA81DD64",
        "delta": "9494C90B71C39DC2A0C3C9B5A7FE17EE3D7D378E68C0CF70006ABB8209742CDB"
    },
    "expected_points": {
        "left": "032088671C110D72530442DACAECCD2016E62999BC4465B8655FFBCCB51645ACE1",
        "right": "032088671C110D72530442DACAECCD2016E62999BC4465B8655FFBCCB51645ACE1"
    },
    "local_verification_result": {
        "main_equation_match": True,
        "inner_product_check": True,
        "all_checks_pass": True
    }
}


def hex_to_point(hex_str: str) -> EcPt:
    """Hex string을 EC point로 변환"""
    return EcPt.from_binary(bytes.fromhex(hex_str), GROUP)


def hex_to_scalar(hex_str: str) -> Bn:
    """Hex string을 scalar로 변환"""
    return Bn.from_hex(hex_str) % ORDER


def point_to_hex(pt: EcPt) -> str:
    """EC point를 compressed hex string으로 변환"""
    return pt.export().hex().upper()


def scalar_to_hex(scalar: Bn) -> str:
    """Scalar를 32-byte hex string으로 변환"""
    return scalar.hex().zfill(64).upper()


def compute_challenge(domain: bytes, size: int, L: EcPt, R: EcPt, round_num: int = -1) -> Bn:
    """
    Fiat-Shamir challenge 계산
    w = H(domain_tag || bit_length || L || R)
    """
    hasher = hashlib.sha256()

    # Domain tag (30 bytes, no null terminator)
    domain_bytes = domain
    hasher.update(domain_bytes)

    # Bit length (4 bytes, big-endian)
    size_bytes = size.to_bytes(4, 'big')
    hasher.update(size_bytes)

    # L (33 bytes, SEC1 compressed)
    L_bytes = L.export()
    hasher.update(L_bytes)

    # R (33 bytes, SEC1 compressed)
    R_bytes = R.export()
    hasher.update(R_bytes)

    # ✅ 1. Fiat-Shamir 입력 바이트 hex 출력
    if round_num >= 0:
        print(f"  [FS DEBUG] Round {round_num}:")
        print(f"    domain_tag (len={len(domain_bytes)}): {domain_bytes.hex().upper()}")
        print(f"    bit_length (4 bytes BE): {size_bytes.hex().upper()}")
        print(f"    L (33 bytes): {L_bytes.hex().upper()}")
        print(f"    R (33 bytes): {R_bytes.hex().upper()}")

        # 전체 입력 바이트 결합
        full_input = domain_bytes + size_bytes + L_bytes + R_bytes
        print(f"    FS_input(hex) = {full_input.hex().upper()}")
        print(f"    FS_input length = {len(full_input)} bytes")

    # Hash to scalar
    digest = hasher.digest()
    w = Bn.from_binary(digest) % ORDER

    if round_num >= 0:
        print(f"    SHA256 digest: {digest.hex().upper()}")
        print(f"    w (before mod): {Bn.from_binary(digest).hex().upper()}")
        print(f"    w (after mod ORDER): {w.hex().upper()}")

    return w


def generate_ipp_trace():
    """골든 벡터 기반 IPP 트레이스 생성"""

    print("=" * 80)
    print("골든 벡터 기반 IPP 트레이스 생성")
    print("=" * 80)
    print()

    # Domain tag
    domain = GOLDEN_VECTOR["domain"].encode('utf-8')
    bit_length = GOLDEN_VECTOR["bit_length"]

    print(f"Domain: {GOLDEN_VECTOR['domain']}")
    print(f"Bit length: {bit_length}")
    print()

    # Parse proof elements
    proof = GOLDEN_VECTOR["proof"]
    A = hex_to_point(proof["A"])
    S = hex_to_point(proof["S"])
    x = hex_to_scalar(GOLDEN_VECTOR["expected_scalars"]["x"])

    # 1. P_initial = A + x·S
    print("=" * 80)
    print("STEP 1: P_initial 계산")
    print("=" * 80)
    print(f"A = {proof['A']}")
    print(f"S = {proof['S']}")
    print(f"x = {GOLDEN_VECTOR['expected_scalars']['x']}")
    print()

    P_initial = A + (x * S)
    P_initial_hex = point_to_hex(P_initial)

    print(f"P_initial = A + x·S")
    print(f"P_initial = {P_initial_hex}")
    print()

    # 2. IPP folding rounds
    print("=" * 80)
    print("STEP 2: IPP 5 라운드 폴딩")
    print("=" * 80)
    print()

    ipp = proof["inner_product_proof"]
    L_vec = [hex_to_point(L_hex) for L_hex in ipp["L"]]
    R_vec = [hex_to_point(R_hex) for R_hex in ipp["R"]]

    rounds_data = []
    P_old = P_initial
    vector_size = bit_length

    for i in range(5):  # 5 rounds for 32-bit
        print(f"Round {i}:")
        print(f"  Vector size: {vector_size} → {vector_size // 2}")

        L = L_vec[i]
        R = R_vec[i]

        L_hex = point_to_hex(L)
        R_hex = point_to_hex(R)

        print(f"  L[{i}] = {L_hex}")
        print(f"  R[{i}] = {R_hex}")

        # ✅ 1. Fiat-Shamir 디버그 출력 활성화
        w = compute_challenge(domain, vector_size, L, R, round_num=i)
        w_inv = w.mod_inverse(ORDER)

        w_hex = scalar_to_hex(w)
        w_inv_hex = scalar_to_hex(w_inv)

        print(f"  w (scalar)     = {w_hex}")
        print(f"  w_inv (scalar) = {w_inv_hex}")

        # P_new = w_inv·L + P_old + w·R
        P_new = (w_inv * L) + P_old + (w * R)

        P_old_hex = point_to_hex(P_old)
        P_new_hex = point_to_hex(P_new)

        print(f"  P_old = {P_old_hex}")
        print(f"  P_new = {P_new_hex}")
        print()

        rounds_data.append({
            "round": i,
            "L": L_hex,
            "R": R_hex,
            "w": w_hex,
            "w_inv": w_inv_hex,
            "P_old": P_old_hex,
            "P_new": P_new_hex,
            "vector_size_before": vector_size,
            "vector_size_after": vector_size // 2
        })

        # Update for next round
        P_old = P_new
        vector_size = vector_size // 2

    P_final = P_old
    P_final_hex = point_to_hex(P_final)

    print("=" * 80)
    print("STEP 3: 최종 값")
    print("=" * 80)
    print(f"P_final = {P_final_hex}")
    print(f"a_final = {ipp['a']}")
    print(f"b_final = {ipp['b']}")
    print()

    # 3. 전송할 트레이스 JSON 생성 (서버 스키마에 맞춤)
    trace_data = {
        "commitment": GOLDEN_VECTOR["commitment"],
        "generators": {
            "G": "0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798",
            "H": "0385D37F1247E19D2C3D9596B03A134022C8786F88480A1DDEA86055860ED97ABA"
        },
        "rounds": rounds_data,  # ipp_folding 제거하고 최상위로 이동
        "final": {
            "a_final": ipp["a"],
            "b_final": ipp["b"],
            "t": proof["t"],
            "P_final": P_final_hex
        }
    }

    return trace_data


def send_to_server(trace_data: dict):
    """서버 compare 엔드포인트로 전송"""

    print("=" * 80)
    print("STEP 4: 서버로 전송")
    print("=" * 80)
    print()

    url = "http://192.168.0.11:8085/api/v1/verify/zk-ipp"

    # commitment를 최상위 레벨로 이동
    commitment = trace_data.pop("commitment")

    # 완전한 proof 구조 생성 (A, S, T1, T2, tau_x, mu, t, inner_product_proof)
    golden_proof = GOLDEN_VECTOR["proof"]

    # P_final은 trace_data의 final에서 가져옴
    P_final_hex = trace_data["final"]["P_final"]

    proof_structure = {
        "A": golden_proof["A"],
        "S": golden_proof["S"],
        "T1": golden_proof["T1"],
        "T2": golden_proof["T2"],
        "tau_x": golden_proof["tau_x"],
        "mu": golden_proof["mu"],
        "t": golden_proof["t"],
        "inner_product_proof": {
            "L": golden_proof["inner_product_proof"]["L"],
            "R": golden_proof["inner_product_proof"]["R"],
            "a": golden_proof["inner_product_proof"]["a"],
            "b": golden_proof["inner_product_proof"]["b"],
            "P_final": P_final_hex
        }
    }

    # 서버가 요구하는 형식: commitment, proof, client_trace 분리
    request_payload = {
        "commitment": commitment,
        "proof": proof_structure,
        "client_trace": trace_data
    }

    print(f"엔드포인트: {url}")
    print(f"요청 크기: {len(json.dumps(request_payload))} bytes")
    print()

    # 디버깅: 실제 전송되는 payload 저장
    debug_payload_path = "logs/request_payload_debug.json"
    with open(debug_payload_path, 'w') as f:
        json.dump(request_payload, f, indent=2)
    print(f"🔍 디버그: 요청 payload 저장 → {debug_payload_path}")
    print()

    try:
        response = requests.post(url, json=request_payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        print(f"✅ 응답 수신 (HTTP {response.status_code})")
        print()
        print("=" * 80)
        print("서버 응답:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print()

        # 결과 저장
        output_path = "logs/server_ipp_compare_result.json"
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"✅ 결과 저장: {output_path}")
        print()

        # 성공 여부 판단
        verified = result.get("verified", False)
        left_equals_right = result.get("left_equals_right", False)

        print("=" * 80)
        print("검증 결과:")
        print("=" * 80)

        if verified and left_equals_right:
            print("🎉 성공!")
            print("✅ verified = true")
            print("✅ left_equals_right = true")
            print("✅ IPP 검증 통과")
            return 0
        else:
            print("❌ 검증 실패")
            print(f"verified: {verified}")
            print(f"left_equals_right: {left_equals_right}")

            if "divergence_type" in result:
                print(f"divergence_type: {result['divergence_type']}")
                print(f"divergence_round: {result.get('divergence_round', 'N/A')}")

            return 1

    except requests.exceptions.RequestException as e:
        print(f"❌ 서버 연결 실패: {e}")
        return 2
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 3


def main():
    """메인 함수"""

    print()
    print("=" * 80)
    print("골든 벡터 기반 IPP 트레이스 생성 및 서버 검증")
    print("=" * 80)
    print()

    # ✅ 5. H 생성 로직 출력
    print("=" * 80)
    print("H GENERATOR 정보")
    print("=" * 80)
    print("H_generation_method: Hardcoded from GOLDEN_VECTOR")
    print("H (from golden vector): 0385D37F1247E19D2C3D9596B03A134022C8786F88480A1DDEA86055860ED97ABA")
    print()
    print("⚠️  주의: 골든 벡터에서 H는 하드코딩된 값을 사용합니다.")
    print("   서버의 H 생성 방식과 일치 여부를 확인해야 합니다.")
    print("   서버가 SHA256(\"bulletproof_h\" || G) * G 방식을 사용한다면")
    print("   이 H 값이 서버 H와 정확히 일치해야 최종 검증이 통과됩니다.")
    print("=" * 80)
    print()

    # ✅ 4. a_final, b_final 정보 출력
    print("=" * 80)
    print("a_final, b_final 정보")
    print("=" * 80)
    print("⚠️  주의: 골든 벡터 테스트에서는 a_final, b_final이")
    print("   이미 계산된 값으로 제공됩니다 (계산 과정 없음).")
    print()
    print(f"a_final (from GOLDEN_VECTOR): {GOLDEN_VECTOR['proof']['inner_product_proof']['a']}")
    print(f"b_final (from GOLDEN_VECTOR): {GOLDEN_VECTOR['proof']['inner_product_proof']['b']}")
    print()
    print("실제 센서 구현에서는 다음과 같이 계산해야 합니다:")
    print("  1. 초기 벡터 a_vec (길이 32), b_vec (길이 32)")
    print("  2. 각 라운드마다 challenge w로 fold:")
    print("     a_vec_new[i] = a_vec_left[i] * w + a_vec_right[i]")
    print("     b_vec_new[i] = b_vec_left[i] * w_inv + b_vec_right[i]")
    print("  3. 최종 라운드 후 a_final = a_vec[0], b_final = b_vec[0]")
    print("=" * 80)
    print()

    # 1. IPP 트레이스 생성
    trace_data = generate_ipp_trace()

    # 트레이스 저장
    trace_path = "logs/ipp_trace_golden_vector.json"
    with open(trace_path, 'w') as f:
        json.dump(trace_data, f, indent=2)

    print(f"✅ 트레이스 저장: {trace_path}")
    print()

    # 2. 서버로 전송
    exit_code = send_to_server(trace_data)

    return exit_code


if __name__ == "__main__":
    import sys
    sys.exit(main())

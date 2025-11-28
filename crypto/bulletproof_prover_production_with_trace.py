#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulletproof Prover with IPP Trace Generation

Production prover 확장 버전으로, Bulletproof Range Proof 생성 시
client_trace (generators, rounds, final) 데이터를 함께 생성합니다.

이 모듈은 센서 클라이언트가 /api/v1/verify/zk-ipp 엔드포인트로
완전한 IPP 검증 데이터를 전송할 수 있도록 합니다.
"""

import sys
import os

# 절대 경로로 crypto 모듈 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bulletproof_prover_production import BulletproofProverProduction
from petlib.ec import EcPt
from petlib.bn import Bn
from typing import Dict, Any, List
import time


class BulletproofProverWithTrace(BulletproofProverProduction):
    """IPP Trace 생성 기능이 추가된 Bulletproof Prover"""

    def __init__(self, bit_length: int = 32, domain: str = "ICS_BULLETPROOF_VERIFIER_v1"):
        """
        Args:
            bit_length: 비트 길이 (기본: 32)
            domain: Fiat-Shamir 도메인 분리 태그
        """
        super().__init__(bit_length=bit_length, domain=domain)

    def _point_to_hex(self, pt: EcPt) -> str:
        """EC point를 compressed hex string으로 변환"""
        return pt.export().hex().upper()

    def _scalar_to_hex(self, scalar: Bn) -> str:
        """Scalar를 32-byte hex string으로 변환"""
        return scalar.hex().upper().zfill(64)

    def _generate_inner_product_proof_with_trace(self, a: List[Bn], b: List[Bn],
                                                  g_vec: List[EcPt], h_vec: List[EcPt],
                                                  y: Bn, x: Bn, A: EcPt, S: EcPt) -> Dict[str, Any]:
        """
        재귀적 Inner Product Proof 생성 + IPP 트레이스 캡처

        Returns:
            {
                "inner_product_proof": {...},  # 기존 IPP 증명
                "rounds_trace": [...],          # 라운드별 상세 정보
                "P_final": "..."                # 최종 포인트
            }
        """
        n = len(a)

        # y의 역원 계산 (h' = h^{y^-1} 변환용)
        y_inv = y.mod_inverse(self.order)

        # h_vec' = h_vec^{y^-n, ..., y^-1} 변환
        h_vec_prime = []
        y_inv_power = y_inv.mod_pow(Bn(n - 1), self.order)
        for i in range(n):
            h_vec_prime.append(y_inv_power * h_vec[i])
            y_inv_power = (y_inv_power * y) % self.order

        # P_initial = A + x·S
        P_current = A + (x * S)

        L_vec = []
        R_vec = []
        rounds_trace = []
        round_num = 0

        # 재귀적으로 벡터 크기 절반씩 줄이기
        while len(a) > 1:
            n = len(a) // 2

            # 벡터 분할
            aL = a[:n]
            aR = a[n:]
            bL = b[:n]
            bR = b[n:]
            gL = g_vec[:n]
            gR = g_vec[n:]
            hL = h_vec_prime[:n]
            hR = h_vec_prime[n:]

            # Cross terms
            cL = self._inner_product(aL, bR)
            cR = self._inner_product(aR, bL)

            # Randomness
            dL = self._random_scalar()
            dR = self._random_scalar()

            # L = g^aL * h'^bR * h^dL
            L = self._vector_commit(aL, gR, bR, hL) + dL * self.h
            # R = g^aR * h'^bL * h^dR
            R = self._vector_commit(aR, gL, bL, hR) + dR * self.h

            L_hex = self._point_to_hex(L)
            R_hex = self._point_to_hex(R)

            L_vec.append(L_hex)
            R_vec.append(R_hex)

            # Challenge w
            w = self._fiat_shamir_challenge(L, R)
            w_inv = w.mod_inverse(self.order)

            w_hex = self._scalar_to_hex(w)
            w_inv_hex = self._scalar_to_hex(w_inv)

            # P_new = w_inv·L + P_current + w·R
            P_new = (w_inv * L) + P_current + (w * R)

            # 라운드 트레이스 기록
            rounds_trace.append({
                "round": round_num,
                "L": L_hex,
                "R": R_hex,
                "w": w_hex,
                "w_inv": w_inv_hex,
                "P_old": self._point_to_hex(P_current),
                "P_new": self._point_to_hex(P_new),
                "vector_size_before": len(a),
                "vector_size_after": n
            })

            # Fold vectors
            # a' = aL*w + aR*w^-1
            a = [(aL[i] * w + aR[i] * w_inv) % self.order for i in range(n)]
            # b' = bL*w^-1 + bR*w
            b = [(bL[i] * w_inv + bR[i] * w) % self.order for i in range(n)]
            # g' = gL*w^-1 + gR*w
            g_vec = [w_inv * gL[i] + w * gR[i] for i in range(n)]
            # h' = hL*w + hR*w^-1
            h_vec_prime = [w * hL[i] + w_inv * hR[i] for i in range(n)]

            # Update for next round
            P_current = P_new
            round_num += 1

        # 최종 값
        final_a = a[0]
        final_b = b[0]
        P_final = P_current

        inner_product_proof = {
            "L": L_vec,
            "R": R_vec,
            "a": self._scalar_to_hex(final_a),
            "b": self._scalar_to_hex(final_b),
            "P_final": self._point_to_hex(P_final)
        }

        return {
            "inner_product_proof": inner_product_proof,
            "rounds_trace": rounds_trace,
            "P_final": self._point_to_hex(P_final)
        }

    def generate_range_proof_with_trace(self, value: int, nonce: str = "") -> Dict[str, Any]:
        """
        Bulletproof Range Proof + client_trace 생성

        Args:
            value: 증명할 값 (0 <= value < 2^bit_length)
            nonce: 고유 nonce

        Returns:
            {
                "commitment": "...",
                "proof": {...},
                "client_trace": {
                    "generators": {"G": "...", "H": "..."},
                    "rounds": [...],
                    "final": {"a_final": "...", "b_final": "...", "t": "...", "P_final": "..."}
                }
            }
        """
        start_time = time.time()

        # 값 범위 검증
        if value < 0 or value >= (1 << self.bit_length):
            raise ValueError(f"Value {value} out of range [0, 2^{self.bit_length})")

        n = self.bit_length

        # === Step 1: Commitment 생성 ===
        gamma = self._random_scalar()
        v_bn = Bn(value)
        V = v_bn * self.g + gamma * self.h

        # === Step 2: Bit decomposition ===
        aL = self._bit_decompose(value)
        aR = [(ai - Bn(1)) % self.order for ai in aL]

        # === Step 3: Blinding vectors ===
        alpha = self._random_scalar()
        sL = [self._random_scalar() for _ in range(n)]
        sR = [self._random_scalar() for _ in range(n)]
        rho = self._random_scalar()

        # === Step 4: Compute A, S ===
        A = alpha * self.h + self._vector_commit(aL, self.g_vec, aR, self.h_vec)
        S = rho * self.h + self._vector_commit(sL, self.g_vec, sR, self.h_vec)

        # === Step 5: Fiat-Shamir challenges y, z ===
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)

        # === Step 6: Polynomial vectors l(x), r(x) ===
        z_vec = [z for _ in range(n)]

        # y^n 벡터
        y_vec = []
        y_power = Bn(1)
        for i in range(n):
            y_vec.append(y_power)
            y_power = (y_power * y) % self.order

        # 2^n 벡터
        two_vec = [Bn(1 << i) for i in range(n)]

        z2 = (z * z) % self.order

        # Polynomial coefficients
        l0 = self._vector_sub(aL, z_vec)
        l1 = sL
        r0 = self._vector_hadamard(y_vec, self._vector_add(aR, z_vec))
        r0 = self._vector_add(r0, self._vector_scalar_mul(z2, two_vec))
        r1 = self._vector_hadamard(y_vec, sR)

        # === Step 7: Polynomial t(x) = <l(x), r(x)> ===
        t0 = self._inner_product(l0, r0)
        t1 = (self._inner_product(l0, r1) + self._inner_product(l1, r0)) % self.order
        t2 = self._inner_product(l1, r1)

        # === Step 8: Commitments T1, T2 ===
        tau_1 = self._random_scalar()
        tau_2 = self._random_scalar()

        T1 = t1 * self.g + tau_1 * self.h
        T2 = t2 * self.g + tau_2 * self.h

        # === Step 9: Challenge x ===
        x = self._fiat_shamir_challenge(T1, T2, z)

        # === Step 10: Response values ===
        x2 = (x * x) % self.order
        tau_x = (tau_2 * x2 + tau_1 * x + z2 * gamma) % self.order
        mu = (alpha + rho * x) % self.order

        # l = l(x) = l_0 + l_1*x
        l_vec = self._vector_add(l0, self._vector_scalar_mul(x, l1))
        # r = r(x) = r_0 + r_1*x
        r_vec = self._vector_add(r0, self._vector_scalar_mul(x, r1))
        # t = <l, r>
        t_hat = self._inner_product(l_vec, r_vec)

        # === Step 11: Inner Product Proof with Trace ===
        ipp_with_trace = self._generate_inner_product_proof_with_trace(
            l_vec, r_vec, self.g_vec, self.h_vec, y, x, A, S
        )

        proof_time = (time.time() - start_time) * 1000  # ms

        # === client_trace 구성 ===
        client_trace = {
            "generators": {
                "G": self._point_to_hex(self.g),
                "H": self._point_to_hex(self.h)
            },
            "rounds": ipp_with_trace["rounds_trace"],
            "final": {
                "a_final": ipp_with_trace["inner_product_proof"]["a"],
                "b_final": ipp_with_trace["inner_product_proof"]["b"],
                "t": self._scalar_to_hex(t_hat),
                "P_final": ipp_with_trace["P_final"]
            }
        }

        # === 결과 반환 ===
        return {
            "commitment": V.export().hex().upper(),
            "proof": {
                "A": A.export().hex().upper(),
                "S": S.export().hex().upper(),
                "T1": T1.export().hex().upper(),
                "T2": T2.export().hex().upper(),
                "tau_x": tau_x.hex().upper().zfill(64),
                "mu": mu.hex().upper().zfill(64),
                "t": t_hat.hex().upper().zfill(64),
                "inner_product_proof": {
                    "L": ipp_with_trace["inner_product_proof"]["L"],
                    "R": ipp_with_trace["inner_product_proof"]["R"],
                    "a": ipp_with_trace["inner_product_proof"]["a"],
                    "b": ipp_with_trace["inner_product_proof"]["b"],
                    "P_final": ipp_with_trace["inner_product_proof"]["P_final"]
                }
            },
            "client_trace": client_trace,
            "timing": {
                "proof_generation_ms": proof_time
            }
        }


if __name__ == "__main__":
    # 테스트
    print("Testing BulletproofProverWithTrace")
    print("=" * 60)

    test_value = 206794  # HAI 데이터셋 예시 값
    test_nonce = "TEST_IPP_TRACE"

    print(f"Value: {test_value}")
    print(f"Nonce: {test_nonce}")
    print()

    prover = BulletproofProverWithTrace(bit_length=32, domain="ICS_BULLETPROOF_VERIFIER_v1")

    start = time.time()
    result = prover.generate_range_proof_with_trace(test_value, test_nonce)
    elapsed = (time.time() - start) * 1000

    print(f"✅ Proof + Trace generation successful!")
    print(f"⏱️  Generation time: {elapsed:.2f}ms")
    print()
    print(f"Commitment: {result['commitment'][:66]}...")
    print()
    print("Proof Components:")
    print(f"  A: {result['proof']['A'][:66]}...")
    print(f"  S: {result['proof']['S'][:66]}...")
    print(f"  T1: {result['proof']['T1'][:66]}...")
    print(f"  T2: {result['proof']['T2'][:66]}...")
    print(f"  tau_x: {result['proof']['tau_x'][:64]}")
    print(f"  mu: {result['proof']['mu'][:64]}")
    print(f"  t: {result['proof']['t'][:64]}")
    print(f"  IPP L vector: {len(result['proof']['inner_product_proof']['L'])} rounds")
    print(f"  IPP R vector: {len(result['proof']['inner_product_proof']['R'])} rounds")
    print()
    print("Client Trace:")
    print(f"  Generators: G, H")
    print(f"  Rounds: {len(result['client_trace']['rounds'])} rounds")
    print(f"  Final: a_final, b_final, t, P_final")
    print()

    # 검증: client_trace의 값들이 proof와 일치하는지
    print("Consistency Checks:")
    ipp = result['proof']['inner_product_proof']
    trace_final = result['client_trace']['final']

    a_match = (ipp['a'] == trace_final['a_final'])
    b_match = (ipp['b'] == trace_final['b_final'])
    t_match = (result['proof']['t'] == trace_final['t'])
    p_match = (ipp['P_final'] == trace_final['P_final'])

    print(f"  a values match: {a_match}")
    print(f"  b values match: {b_match}")
    print(f"  t values match: {t_match}")
    print(f"  P_final match: {p_match}")
    print()

    if a_match and b_match and t_match and p_match:
        print("✅ All consistency checks PASSED")
    else:
        print("❌ Consistency check FAILED")

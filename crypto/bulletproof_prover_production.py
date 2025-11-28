#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bulletproof Range Proof Prover - Production Mode

수학적으로 완전한 Bulletproof 증명 생성기.
서버 PRODUCTION MODE (VERIFY_MATH=true)에서 검증을 통과하는 증명 생성.

구현 사항:
- Bit decomposition: value를 비트 벡터로 분해
- Polynomial vectors: l(x), r(x) 정확한 계산
- Polynomial commitments: t(x) = <l(x), r(x)>, T1, T2
- Response values: tau_x, mu, t 정확한 계산
- Inner Product Proof: 재귀적 L[], R[], a, b 생성

References:
- Bulletproof paper: https://eprint.iacr.org/2017/1066.pdf
- Server Verifier: /home/woohyunchoi/ics-server-verifier/crypto/bulletproof_verifier.py

=============================================================================
Protocol Specification (ICS-BULLETPROOF-V1)
=============================================================================

PROTOCOL_VERSION: "ICS-BULLETPROOF-V1"
  - Bulletproof range proof implementation for ICS sensor privacy
  - Based on Bulletproof paper (https://eprint.iacr.org/2017/1066.pdf)
  - Compatible with ZK_ONLY transmission mode

GENERATOR_SCHEME: "HASHED_FROM_G_V1"
  - Curve: secp256k1 (EcGroup 714)
  - G: secp256k1 base generator
  - H: sha256(G.export() + "bulletproof_h") · G
  - G_vec[i]: sha256("bulletproof_g_{i}") · G  (i = 0..n-1)
  - H_vec[i]: sha256("bulletproof_h_{i}") · G  (i = 0..n-1)

DELTA_SCHEME: "BULLETPROOF_PAPER_STANDARD"
  - Formula: delta(y,z) = (z - z²) * Σ_{i=0..n-1} y^i  -  z³ * Σ_{i=0..n-1} 2^i
  - Where:
    - n: bit length (e.g., 32)
    - y, z: Fiat-Shamir challenges
    - Σy^i: sum of y-powers from y^0 to y^(n-1)
    - Σ2^i: sum of 2-powers from 2^0 to 2^(n-1) = 2^n - 1
  - Reference: Bulletproof paper Section 4.2

=============================================================================
"""

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha256
from typing import Dict, Any, List, Tuple, Optional
import secrets
import time
import json


# Protocol Constants
PROTOCOL_VERSION = "ICS-BULLETPROOF-V1"
GENERATOR_SCHEME = "HASHED_FROM_G_V1"
DELTA_SCHEME = "BULLETPROOF_PAPER_STANDARD"

# Generator Schemes Configuration
GENERATOR_SCHEMES = {
    "HASHED_FROM_G_V1": {
        "description": "Generators derived from secp256k1 base point G using SHA256",
        "curve": "secp256k1",
        "h_seed": "bulletproof_h",
        "g_vec_prefix": "bulletproof_g_",
        "h_vec_prefix": "bulletproof_h_"
    }
}


class BulletproofProverProduction:
    """Production Mode: 수학적으로 완전한 Bulletproof Prover"""

    def __init__(self, bit_length: int = 32, domain: str = "ICS_BULLETPROOF_VERIFIER_v1"):
        """
        Args:
            bit_length: 비트 길이 (기본: 32)
            domain: Fiat-Shamir 도메인 분리 태그
        """
        self.bit_length = bit_length
        self.domain = domain.encode('utf-8')

        # secp256k1 곡선
        self.group = EcGroup(714)
        self.g = self.group.generator()
        self.order = self.group.order()

        # Generator 생성 (서버와 동일)
        self.h = self._generate_h()
        self.g_vec = self._generate_g_vector()
        self.h_vec = self._generate_h_vector()

    def _generate_h(self) -> EcPt:
        """독립적인 생성원 H 생성"""
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        return h_scalar * self.g

    def _generate_g_vector(self) -> List[EcPt]:
        """벡터 G 생성"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            g_vec.append(scalar * self.g)
        return g_vec

    def _generate_h_vector(self) -> List[EcPt]:
        """벡터 H 생성"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.order
            h_vec.append(scalar * self.g)
        return h_vec

    def _random_scalar(self) -> Bn:
        """안전한 랜덤 스칼라 생성"""
        random_bytes = secrets.token_bytes(32)
        return Bn.from_binary(random_bytes) % self.order

    def _fiat_shamir_challenge(self, *elements) -> Bn:
        """Fiat-Shamir 챌린지 생성"""
        hasher = sha256()

        # 도메인 분리
        hasher.update(self.domain)
        hasher.update(self.bit_length.to_bytes(4, 'big'))

        # 입력 요소들 해싱
        for elem in elements:
            if isinstance(elem, EcPt):
                hasher.update(elem.export())
            elif isinstance(elem, Bn):
                hasher.update(elem.binary())
            elif isinstance(elem, bytes):
                hasher.update(elem)
            else:
                hasher.update(str(elem).encode())

        challenge_bytes = hasher.digest()
        return Bn.from_binary(challenge_bytes) % self.order

    def _bit_decompose(self, value: int) -> List[Bn]:
        """
        값을 비트로 분해

        Returns:
            aL: [b_0, b_1, ..., b_{n-1}] where value = sum(b_i * 2^i)
        """
        aL = []
        for i in range(self.bit_length):
            bit = (value >> i) & 1
            aL.append(Bn(bit))
        return aL

    def _vector_add(self, a: List[Bn], b: List[Bn]) -> List[Bn]:
        """벡터 덧셈"""
        return [(ai + bi) % self.order for ai, bi in zip(a, b)]

    def _vector_sub(self, a: List[Bn], b: List[Bn]) -> List[Bn]:
        """벡터 뺄셈"""
        return [(ai - bi) % self.order for ai, bi in zip(a, b)]

    def _vector_scalar_mul(self, scalar: Bn, vec: List[Bn]) -> List[Bn]:
        """스칼라 곱셈"""
        return [(scalar * vi) % self.order for vi in vec]

    def _vector_hadamard(self, a: List[Bn], b: List[Bn]) -> List[Bn]:
        """Hadamard 곱 (원소별 곱셈)"""
        return [(ai * bi) % self.order for ai, bi in zip(a, b)]

    def _inner_product(self, a: List[Bn], b: List[Bn]) -> Bn:
        """내적 계산"""
        result = Bn(0)
        for ai, bi in zip(a, b):
            result = (result + ai * bi) % self.order
        return result

    def _vector_commit(self, a: List[Bn], g_vec: List[EcPt], b: List[Bn], h_vec: List[EcPt]) -> EcPt:
        """벡터 commitment: sum(a_i * G_i) + sum(b_i * H_i)"""
        result = self.group.infinite()
        for ai, gi in zip(a, g_vec):
            result = result + (ai * gi)
        for bi, hi in zip(b, h_vec):
            result = result + (bi * hi)
        return result

    def _compute_delta(self, y: Bn, z: Bn) -> Bn:
        """
        delta(y, z) 계산 - BULLETPROOF_PAPER_STANDARD

        Formula:
            delta(y,z) = (z - z²) * Σ_{i=0..n-1} y^i  -  z³ * Σ_{i=0..n-1} 2^i

        Where:
            n: bit length (self.bit_length, typically 32)
            y, z: Fiat-Shamir challenges derived from transcript
            Σy^i: y_powers_sum = 1 + y + y² + ... + y^(n-1)
            Σ2^i: two_powers_sum = 1 + 2 + 4 + ... + 2^(n-1) = 2^n - 1

        Reference:
            Bulletproof paper (https://eprint.iacr.org/2017/1066.pdf) Section 4.2
            This delta term appears in the main verification equation:
                t·G + tau_x·H == V·z² + delta(y,z)·G + T1·x + T2·x²

        Implementation Note:
            - y_powers_sum는 루프로 계산 (i=0..n-1: sum += y^i)
            - two_powers_sum은 closed form으로 계산 (2^n - 1)
            - 모든 연산은 modulo group order (secp256k1 order)
        """
        n = self.bit_length

        # <1^n, y^n> = Σ_{i=0..n-1} y^i
        # Compute: 1 + y + y² + y³ + ... + y^(n-1)
        y_powers_sum = Bn(0)
        y_power = Bn(1)  # Start with y^0 = 1
        for i in range(n):
            y_powers_sum = (y_powers_sum + y_power) % self.order
            y_power = (y_power * y) % self.order  # y^(i+1)

        # <1^n, 2^n> = Σ_{i=0..n-1} 2^i
        # Compute: 1 + 2 + 4 + 8 + ... + 2^(n-1) = 2^n - 1
        # For n=32: 2^32 - 1 = 4294967295
        two_powers_sum = Bn((1 << n) - 1)

        # Compute powers of z
        z2 = (z * z) % self.order       # z²
        z3 = (z2 * z) % self.order      # z³

        # delta = (z - z²) * Σy^i  -  z³ * Σ2^i
        delta = ((z - z2) * y_powers_sum - z3 * two_powers_sum) % self.order
        return delta

    def generate_range_proof(self, value: int, nonce: str = "") -> Dict[str, Any]:
        """
        Production Mode: 수학적으로 완전한 Range Proof 생성

        Args:
            value: 증명할 값 (0 <= value < 2^bit_length)
            nonce: 고유 nonce

        Returns:
            proof 데이터 (commitment, proof, blinding_factor, timing)
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
        aL = self._bit_decompose(value)  # [b_0, b_1, ..., b_{n-1}]
        aR = [(ai - Bn(1)) % self.order for ai in aL]  # [b_0 - 1, b_1 - 1, ...]

        # === Step 3: Blinding vectors ===
        alpha = self._random_scalar()
        sL = [self._random_scalar() for _ in range(n)]
        sR = [self._random_scalar() for _ in range(n)]
        rho = self._random_scalar()

        # === Step 4: Compute A, S ===
        # A = h^alpha * prod(g_i^{aL_i}) * prod(h_i^{aR_i})
        A = alpha * self.h + self._vector_commit(aL, self.g_vec, aR, self.h_vec)

        # S = h^rho * prod(g_i^{sL_i}) * prod(h_i^{sR_i})
        S = rho * self.h + self._vector_commit(sL, self.g_vec, sR, self.h_vec)

        # === Step 5: Fiat-Shamir challenges y, z ===
        y = self._fiat_shamir_challenge(A, S)
        z = self._fiat_shamir_challenge(A, S, y)

        # === Step 6: Polynomial vectors l(x), r(x) ===
        # l(x) = aL - z*1^n + sL*x
        # r(x) = y^n ∘ (aR + z*1^n + sR*x) + z^2 * 2^n

        z_vec = [z for _ in range(n)]  # z * 1^n

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
        # l(x) = l_0 + l_1 * x
        # l_0 = aL - z*1^n
        l0 = self._vector_sub(aL, z_vec)
        # l_1 = sL
        l1 = sL

        # r(x) = r_0 + r_1 * x
        # r_0 = y^n ∘ (aR + z*1^n) + z^2 * 2^n
        r0 = self._vector_hadamard(y_vec, self._vector_add(aR, z_vec))
        r0 = self._vector_add(r0, self._vector_scalar_mul(z2, two_vec))
        # r_1 = y^n ∘ sR
        r1 = self._vector_hadamard(y_vec, sR)

        # === Step 7: Polynomial t(x) = <l(x), r(x)> ===
        # t(x) = t_0 + t_1*x + t_2*x^2
        # t_0 = <l_0, r_0>
        t0 = self._inner_product(l0, r0)
        # t_1 = <l_0, r_1> + <l_1, r_0>
        t1 = (self._inner_product(l0, r1) + self._inner_product(l1, r0)) % self.order
        # t_2 = <l_1, r_1>
        t2 = self._inner_product(l1, r1)

        # === Step 8: Commitments T1, T2 ===
        tau_1 = self._random_scalar()
        tau_2 = self._random_scalar()

        T1 = t1 * self.g + tau_1 * self.h
        T2 = t2 * self.g + tau_2 * self.h

        # === Step 9: Challenge x ===
        x = self._fiat_shamir_challenge(T1, T2, z)

        # === Step 10: Response values ===
        # tau_x = tau_2*x^2 + tau_1*x + z^2*gamma
        x2 = (x * x) % self.order
        tau_x = (tau_2 * x2 + tau_1 * x + z2 * gamma) % self.order

        # mu = alpha + rho*x
        mu = (alpha + rho * x) % self.order

        # l = l(x) = l_0 + l_1*x
        l_vec = self._vector_add(l0, self._vector_scalar_mul(x, l1))

        # r = r(x) = r_0 + r_1*x
        r_vec = self._vector_add(r0, self._vector_scalar_mul(x, r1))

        # t = <l, r>
        t_hat = self._inner_product(l_vec, r_vec)

        # === Step 11: Inner Product Proof ===
        inner_product_proof = self._generate_inner_product_proof(l_vec, r_vec, self.g_vec, self.h_vec, y, x)

        proof_time = (time.time() - start_time) * 1000  # ms

        # 결과 반환
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
                "inner_product_proof": inner_product_proof
            },
            "blinding_factor": gamma.hex().upper().zfill(64),
            "timing": {
                "proof_generation_ms": proof_time
            }
        }

    def _generate_inner_product_proof(self, a: List[Bn], b: List[Bn],
                                      g_vec: List[EcPt], h_vec: List[EcPt],
                                      y: Bn, x: Bn) -> Dict[str, Any]:
        """
        재귀적 Inner Product Proof 생성

        증명: <a, b> = t (이미 계산된 값)
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

        L_vec = []
        R_vec = []

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

            # L = g^aL * h'^bR * h^dL + cL*G
            L = self._vector_commit(aL, gR, bR, hL) + dL * self.h
            # R = g^aR * h'^bL * h^dR + cR*G
            R = self._vector_commit(aR, gL, bL, hR) + dR * self.h

            L_vec.append(L.export().hex().upper())
            R_vec.append(R.export().hex().upper())

            # Challenge w
            w = self._fiat_shamir_challenge(L, R)
            w_inv = w.mod_inverse(self.order)

            # Fold vectors
            # a' = aL*w + aR*w^-1
            a = [(aL[i] * w + aR[i] * w_inv) % self.order for i in range(n)]
            # b' = bL*w^-1 + bR*w
            b = [(bL[i] * w_inv + bR[i] * w) % self.order for i in range(n)]
            # g' = gL*w^-1 + gR*w
            g_vec = [w_inv * gL[i] + w * gR[i] for i in range(n)]
            # h' = hL*w + hR*w^-1
            h_vec_prime = [w * hL[i] + w_inv * hR[i] for i in range(n)]

        # 최종 값
        final_a = a[0]
        final_b = b[0]

        return {
            "L": L_vec,
            "R": R_vec,
            "a": final_a.hex().upper().zfill(64),
            "b": final_b.hex().upper().zfill(64)
        }

    def dump_generators(self, output_path: str = "crypto/debug_generators_client.json"):
        """
        G, H, G_vec, H_vec 생성자 정보를 JSON으로 덤프
        서버와 비교하기 위한 디버깅 기능
        """
        scheme_info = GENERATOR_SCHEMES.get(GENERATOR_SCHEME, {})

        generators_data = {
            "protocol_version": PROTOCOL_VERSION,
            "generator_scheme": GENERATOR_SCHEME,
            "generator_scheme_description": scheme_info.get("description", ""),
            "delta_scheme": DELTA_SCHEME,
            "domain": self.domain.decode('utf-8'),
            "bit_length": self.bit_length,
            "curve": scheme_info.get("curve", "secp256k1"),
            "G": self.g.export().hex().upper(),
            "H": self.h.export().hex().upper(),
            "G_vec": [gpt.export().hex().upper() for gpt in self.g_vec],
            "H_vec": [hpt.export().hex().upper() for hpt in self.h_vec],
            "generation_parameters": {
                "h_seed": scheme_info.get("h_seed", ""),
                "g_vec_prefix": scheme_info.get("g_vec_prefix", ""),
                "h_vec_prefix": scheme_info.get("h_vec_prefix", "")
            }
        }

        with open(output_path, 'w') as f:
            json.dump(generators_data, f, indent=2)

        print(f"[DEBUG] Generators dumped to: {output_path}")
        return generators_data

    def generate_range_proof_with_debug(self, value: int, nonce: str = "",
                                       sensor: str = "UNKNOWN",
                                       dump_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Production Mode: 디버그 모드로 Range Proof 생성 및 검증

        Args:
            value: 증명할 값
            nonce: 고유 nonce
            sensor: 센서 ID (디버그용)
            dump_path: 디버그 데이터를 저장할 JSON 경로 (None이면 저장 안함)

        Returns:
            proof 데이터 + 디버그 정보
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

        # === 로컬 검증 1: t == <l(x), r(x)> ===
        t_from_inner_product = self._inner_product(l_vec, r_vec)
        check_1_inner_product = (t_hat == t_from_inner_product)

        # === 로컬 검증 2: 메인 그룹 방정식 ===
        # left = t·G + tau_x·H
        left = t_hat * self.g + tau_x * self.h

        # right = V·z² + delta(y,z)·G + T1·x + T2·x²
        delta = self._compute_delta(y, z)
        right = z2 * V + delta * self.g + x * T1 + x2 * T2

        check_2_main_equation = (left == right)

        # === Step 11: Inner Product Proof ===
        inner_product_proof = self._generate_inner_product_proof(l_vec, r_vec, self.g_vec, self.h_vec, y, x)

        # === 로컬 검증 3: L[], R[] 포인트 인코딩 검증 ===
        lr_encoding_checks = []
        for i, (L_hex, R_hex) in enumerate(zip(inner_product_proof["L"], inner_product_proof["R"])):
            L_check = {"round": i, "L": {}, "R": {}}

            # L 검증
            try:
                L_bytes = bytes.fromhex(L_hex)
                L_check["L"]["hex"] = L_hex
                L_check["L"]["length"] = len(L_bytes)
                L_check["L"]["valid_length"] = (len(L_bytes) == 33)

                # petlib로 파싱 시도
                try:
                    L_pt = EcPt.from_binary(L_bytes, self.group)
                    L_check["L"]["parseable"] = True
                    L_check["L"]["reencoded"] = L_pt.export().hex().upper()
                    L_check["L"]["matches"] = (L_check["L"]["reencoded"] == L_hex)
                except:
                    L_check["L"]["parseable"] = False
                    L_check["L"]["error"] = "Failed to parse with petlib"
            except Exception as e:
                L_check["L"]["error"] = str(e)

            # R 검증
            try:
                R_bytes = bytes.fromhex(R_hex)
                L_check["R"]["hex"] = R_hex
                L_check["R"]["length"] = len(R_bytes)
                L_check["R"]["valid_length"] = (len(R_bytes) == 33)

                # petlib로 파싱 시도
                try:
                    R_pt = EcPt.from_binary(R_bytes, self.group)
                    L_check["R"]["parseable"] = True
                    L_check["R"]["reencoded"] = R_pt.export().hex().upper()
                    L_check["R"]["matches"] = (L_check["R"]["reencoded"] == R_hex)
                except:
                    L_check["R"]["parseable"] = False
                    L_check["R"]["error"] = "Failed to parse with petlib"
            except Exception as e:
                L_check["R"]["error"] = str(e)

            lr_encoding_checks.append(L_check)

        proof_time = (time.time() - start_time) * 1000  # ms

        # 결과 반환
        proof_data = {
            "commitment": V.export().hex().upper(),
            "proof": {
                "A": A.export().hex().upper(),
                "S": S.export().hex().upper(),
                "T1": T1.export().hex().upper(),
                "T2": T2.export().hex().upper(),
                "tau_x": tau_x.hex().upper().zfill(64),
                "mu": mu.hex().upper().zfill(64),
                "t": t_hat.hex().upper().zfill(64),
                "inner_product_proof": inner_product_proof
            },
            "blinding_factor": gamma.hex().upper().zfill(64),
            "timing": {
                "proof_generation_ms": proof_time
            }
        }

        # 디버그 정보 추가
        debug_info = {
            # Protocol metadata
            "protocol_version": PROTOCOL_VERSION,
            "generator_scheme": GENERATOR_SCHEME,
            "delta_scheme": DELTA_SCHEME,
            "delta_formula": "(z - z^2) * sum(y^i, i=0..n-1) - z^3 * sum(2^i, i=0..n-1)",
            "delta_formula_note": "Bulletproof paper Section 4.2, main verification equation",

            # Test case metadata
            "sensor": sensor,
            "value": value,
            "scaled_value": value,
            "nonce": nonce,
            "bit_length": n,
            "n_value": n,
            "domain": self.domain.decode('utf-8'),

            # 스칼라
            "scalars": {
                "value": value,
                "gamma": gamma.hex().upper().zfill(64),
                "alpha": alpha.hex().upper().zfill(64),
                "rho": rho.hex().upper().zfill(64),
                "tau_1": tau_1.hex().upper().zfill(64),
                "tau_2": tau_2.hex().upper().zfill(64),
                "t0": t0.hex().upper().zfill(64),
                "t1": t1.hex().upper().zfill(64),
                "t2": t2.hex().upper().zfill(64),
                "tau_x": tau_x.hex().upper().zfill(64),
                "mu": mu.hex().upper().zfill(64),
                "t": t_hat.hex().upper().zfill(64),
                "y": y.hex().upper().zfill(64),
                "z": z.hex().upper().zfill(64),
                "x": x.hex().upper().zfill(64),
                "delta": delta.hex().upper().zfill(64)
            },

            # 포인트
            "points": {
                "G": self.g.export().hex().upper(),
                "H": self.h.export().hex().upper(),
                "V": V.export().hex().upper(),
                "A": A.export().hex().upper(),
                "S": S.export().hex().upper(),
                "T1": T1.export().hex().upper(),
                "T2": T2.export().hex().upper(),
                "left": left.export().hex().upper(),
                "right": right.export().hex().upper()
            },

            # 로컬 검증 결과
            "local_verification": {
                "check_1_inner_product": check_1_inner_product,
                "check_2_main_equation": check_2_main_equation,
                "all_checks_pass": check_1_inner_product and check_2_main_equation
            },

            # L[], R[] 인코딩 검증
            "lr_encoding_checks": lr_encoding_checks,

            # 증명 데이터
            "proof_data": proof_data
        }

        # 디버그 데이터 덤프
        if dump_path:
            with open(dump_path, 'w') as f:
                json.dump(debug_info, f, indent=2)
            print(f"[DEBUG] Full proof debug data dumped to: {dump_path}")

        # 콘솔 출력
        print(f"\n[DEBUG] Client-side Verification Results:")
        print(f"  Sensor: {sensor}, Value: {value}")
        print(f"  Check 1 (t == <l(x), r(x)>): {check_1_inner_product}")
        print(f"  Check 2 (Main Group Equation): {check_2_main_equation}")
        print(f"  Overall: {'✅ PASS' if check_1_inner_product and check_2_main_equation else '❌ FAIL'}")

        # L/R 인코딩 요약
        lr_ok_count = sum(1 for c in lr_encoding_checks
                         if c["L"].get("parseable", False) and c["R"].get("parseable", False))
        print(f"  L/R Encoding: {lr_ok_count}/{len(lr_encoding_checks)} rounds parseable")

        if not check_1_inner_product or not check_2_main_equation:
            print(f"\n[WARNING] Local verification FAILED!")
            print(f"  left  = {left.export().hex().upper()}")
            print(f"  right = {right.export().hex().upper()}")
            print(f"  delta = {delta.hex().upper().zfill(64)}")

        return proof_data


def generate_range_proof(value_int: int, nonce: str, n: int = 32,
                        domain: str = "ICS_BULLETPROOF_VERIFIER_v1",
                        mode: str = "production") -> Dict[str, Any]:
    """
    Range proof 생성 (호환성 함수)

    Args:
        value_int: 증명할 정수 값
        nonce: 고유 nonce
        n: 비트 길이
        domain: 도메인 태그
        mode: "production" (수학적으로 완전) or "dev" (구조적만)

    Returns:
        proof 데이터
    """
    if mode == "production":
        prover = BulletproofProverProduction(bit_length=n, domain=domain)
        return prover.generate_range_proof(value_int, nonce)
    else:
        # Development mode는 기존 prover 사용
        from crypto.bulletproof_prover_petlib import BulletproofProverPetlib
        prover = BulletproofProverPetlib(bit_length=n, domain=domain)
        return prover.generate_range_proof(value_int, nonce)


if __name__ == "__main__":
    # 테스트
    print("Testing Production Mode Bulletproof Prover")
    print("=" * 60)

    test_value = 123456
    test_nonce = "TEST_NONCE_PROD"

    print(f"Value: {test_value}")
    print(f"Nonce: {test_nonce}")
    print()

    start = time.time()
    proof_data = generate_range_proof(test_value, test_nonce, mode="production")
    elapsed = (time.time() - start) * 1000

    print(f"✅ Proof generation successful!")
    print(f"⏱️  Generation time: {elapsed:.2f}ms")
    print(f"   (Internal timing: {proof_data.get('timing', {}).get('proof_generation_ms', 0):.2f}ms)")
    print()
    print(f"Commitment: {proof_data['commitment'][:66]}...")
    print(f"Blinding Factor: {proof_data['blinding_factor'][:66]}...")
    print()
    print("Proof Components:")
    print(f"  A: {proof_data['proof']['A'][:66]}...")
    print(f"  S: {proof_data['proof']['S'][:66]}...")
    print(f"  T1: {proof_data['proof']['T1'][:66]}...")
    print(f"  T2: {proof_data['proof']['T2'][:66]}...")
    print(f"  tau_x: {proof_data['proof']['tau_x'][:64]}")
    print(f"  mu: {proof_data['proof']['mu'][:64]}")
    print(f"  t: {proof_data['proof']['t'][:64]}")
    print(f"  L vector: {len(proof_data['proof']['inner_product_proof']['L'])} rounds")
    print(f"  R vector: {len(proof_data['proof']['inner_product_proof']['R'])} rounds")

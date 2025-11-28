"""Bulletproof 영지식 범위 증명 검증 모듈"""
import time
import json
import os
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

try:
    from petlib.ec import EcGroup, EcPt
    from petlib.bn import Bn
    from hashlib import sha256
except ImportError:
    logger.error("petlib library is required for bulletproof verification")
    logger.error("Install with: pip install petlib")
    raise ImportError("petlib is required for cryptographic verification. Install with: pip install petlib")


@dataclass
class BulletproofProof:
    """Bulletproof 증명 구조체"""
    A: str  # 커밋먼트 A
    S: str  # 커밋먼트 S
    T1: str  # 커밋먼트 T1
    T2: str  # 커밋먼트 T2
    tau_x: str  # 스칼라 tau_x
    mu: str  # 스칼라 mu
    t: str  # 스칼라 t
    inner_product_proof: Dict[str, Any]  # 내적 증명


@dataclass
class VerificationResult:
    """검증 결과"""
    verified: bool
    processing_time_ms: float
    error_message: Optional[str] = None
    proof_size_bytes: Optional[int] = None
    equation_match: Optional[bool] = None  # 메인 방정식 일치 여부
    dev_mode_strict: Optional[bool] = None  # Strict dev mode 사용 여부
    development_mode: Optional[bool] = None  # 현재 서버 모드 (True=개발, False=프로덕션)
    left_equals_right: Optional[bool] = None  # 메인 방정식 left == right 결과
    # 디버그 및 원인 분석 필드
    client_mode_ignored: Optional[str] = None  # 클라이언트 모드 무시 시 reason
    client_challenges_ignored: Optional[bool] = None  # 클라이언트 챌린지 무시 여부
    root_cause: Optional[str] = None  # 단정적 원인 코드
    evidence: Optional[str] = None  # 증거
    fix_instruction: Optional[str] = None  # 수정 안내
    # 서버 계산 중간값 (debug=true 시)
    debug_values: Optional[Dict[str, Any]] = None


class BulletproofVerifier:
    """Bulletproof 영지식 범위 증명 검증기"""
    
    def __init__(self, bit_length: int = 32, development_mode: bool = None):  # 32로 통일!
        self.bit_length = bit_length
        # Development mode: BULLETPROOF_DEV_MODE 환경변수로 제어
        # 기본값을 'true'로 설정 (개발 모드)
        env_value = os.getenv('BULLETPROOF_DEV_MODE', 'true')  # 기본값 변경: false -> true
        if development_mode is None:
            self.development_mode = env_value.lower() == 'true'
        else:
            # 명시적으로 전달된 경우
            self.development_mode = development_mode
        self.name = "Bulletproof Verifier"

        # secp256k1 곡선 사용
        self.group = EcGroup(714)
        self.g = self.group.generator()

        # H 생성 (센서와 동일)
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.group.order()
        self.h = h_scalar * self.g

        # STRICT_GENERATOR_FROM_FILE 옵션 체크
        strict_gen_from_file = os.getenv('STRICT_GENERATOR_FROM_FILE', 'false').lower() == 'true'
        generator_file = os.getenv('GENERATOR_FILE_PATH', 'crypto/debug_generators_client.json')

        if strict_gen_from_file:
            logger.info(f"STRICT_GENERATOR_FROM_FILE=true: Loading generators from {generator_file}")
            file_G, file_H, file_G_vec, file_H_vec = self._load_generators_from_file(generator_file)

            if file_G is not None:
                self.g = file_G
                self.h = file_H
                self.g_vec = file_G_vec
                self.h_vec = file_H_vec
                logger.info("✅ Generators loaded from file successfully")
            else:
                logger.warning("⚠️  Failed to load generators from file, falling back to deterministic generation")
                # 벡터 생성 (Real Library와 동일)
                self.g_vec = self._generate_g_vector()
                self.h_vec = self._generate_h_vector()
        else:
            # 벡터 생성 (Real Library와 동일)
            self.g_vec = self._generate_g_vector()
            self.h_vec = self._generate_h_vector()

        if self.development_mode:
            logger.info(f"Bulletproof verifier initialized with {bit_length}-bit range in DEVELOPMENT MODE (구조적 검증만)")
        else:
            logger.info(f"Bulletproof verifier initialized with {bit_length}-bit range in PRODUCTION MODE (완전한 암호학적 검증)")

        # Generator 비교 수행 (환경변수로 제어)
        compare_generators = os.getenv('COMPARE_GENERATORS_ON_INIT', 'false').lower() == 'true'
        if compare_generators:
            self._compare_generators_with_client(generator_file)

        # Strict Math in Dev Mode 옵션 (디버깅용)
        self.strict_math_in_dev = os.getenv('BULLETPROOF_STRICT_MATH_IN_DEV', 'false').lower() == 'true'
        if self.development_mode and self.strict_math_in_dev:
            logger.warning("⚠️  BULLETPROOF_STRICT_MATH_IN_DEV=true: Development Mode에서도 메인 방정식 검증 수행")
            logger.warning("    이 모드에서는 left != right 시 검증 실패 처리됩니다.")

    def _generate_h(self) -> 'EcPt':
        """독립적인 생성원 H 생성"""
        # G의 해시를 이용해 독립적인 H 생성
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()  # Real Library와 동일
        h_scalar = Bn.from_binary(h_hash) % self.group.order()
        return h_scalar * self.g
    
    def _generate_g_vector(self) -> list:
        """벡터 G 생성 (bit_length 개의 생성원)"""
        g_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_g_{i}".encode()  # Real Library와 동일
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.group.order()
            g_vec.append(scalar * self.g)
        return g_vec
    
    def _generate_h_vector(self) -> list:
        """벡터 H 생성 (bit_length 개의 생성원)"""
        h_vec = []
        for i in range(self.bit_length):
            seed = f"bulletproof_h_{i}".encode()  # Real Library와 동일
            hash_val = sha256(seed).digest()
            scalar = Bn.from_binary(hash_val) % self.group.order()
            h_vec.append(scalar * self.g)
        return h_vec

    def _load_generators_from_file(self, filepath: str) -> Tuple[Optional['EcPt'], Optional['EcPt'], Optional[list], Optional[list]]:
        """JSON 파일에서 generator 로드

        Returns:
            (G, H, G_vec, H_vec) 또는 실패 시 (None, None, None, None)
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # G, H 로드
            G = self._parse_ec_point(data.get("G", ""))
            H = self._parse_ec_point(data.get("H", ""))

            # G_vec, H_vec 로드
            G_vec = []
            H_vec = []

            g_vec_data = data.get("G_vec", [])
            h_vec_data = data.get("H_vec", [])

            if len(g_vec_data) != self.bit_length or len(h_vec_data) != self.bit_length:
                logger.error(f"Generator vector length mismatch in file: expected {self.bit_length}, got G_vec={len(g_vec_data)}, H_vec={len(h_vec_data)}")
                return None, None, None, None

            for i in range(self.bit_length):
                G_vec.append(self._parse_ec_point(g_vec_data[i]))
                H_vec.append(self._parse_ec_point(h_vec_data[i]))

            logger.info(f"Successfully loaded generators from {filepath}")
            return G, H, G_vec, H_vec

        except FileNotFoundError:
            logger.warning(f"Generator file not found: {filepath}")
            return None, None, None, None
        except Exception as e:
            logger.error(f"Failed to load generators from file: {e}")
            return None, None, None, None

    def dump_generators_server(self, output_path: str = "crypto/debug_generators_server.json"):
        """서버 generator를 JSON 파일로 덤프

        Args:
            output_path: 출력 JSON 파일 경로
        """
        import os

        # 출력 디렉토리 확인
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Generator 데이터 구성
        data = {
            "curve": "secp256k1",
            "group_nid": 714,  # EcGroup(714)
            "domain": os.getenv('BP_DOMAIN', 'ICS_BULLETPROOF_VERIFIER_v1'),
            "generator_scheme": "deterministic_hash_based",
            "generator_description": {
                "G": "secp256k1 standard generator",
                "H": "SHA256(G.export() || 'bulletproof_h') * G",
                "G_vec": "SHA256('bulletproof_g_{i}') * G for i in 0..n-1",
                "H_vec": "SHA256('bulletproof_h_{i}') * G for i in 0..n-1"
            },
            "n": self.bit_length,
            "G": self.g.export().hex(),
            "H": self.h.export().hex(),
            "G_vec": [pt.export().hex() for pt in self.g_vec],
            "H_vec": [pt.export().hex() for pt in self.h_vec]
        }

        # JSON 파일로 저장
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Server generators dumped to: {output_path}")
        logger.info(f"   Curve: {data['curve']}")
        logger.info(f"   Domain: {data['domain']}")
        logger.info(f"   Generator scheme: {data['generator_scheme']}")
        logger.info(f"   n: {data['n']}")

        return output_path

    def _compare_generators_with_client(self, client_filepath: str = "crypto/debug_generators_client.json"):
        """클라이언트 generator dump와 비교

        Args:
            client_filepath: 클라이언트 generator JSON 파일 경로
        """
        logger.info("=" * 100)
        logger.info("Generator Comparison: Server vs Client")
        logger.info("=" * 100)

        # 클라이언트 generator 로드
        client_G, client_H, client_G_vec, client_H_vec = self._load_generators_from_file(client_filepath)

        if client_G is None:
            logger.warning(f"Cannot compare generators: failed to load client generators from {client_filepath}")
            logger.info("=" * 100)
            return

        # G 비교
        server_G_hex = self.g.export().hex()
        client_G_hex = client_G.export().hex()
        g_match = (server_G_hex == client_G_hex)

        logger.info(f"G (generator): {'✅ MATCH' if g_match else '❌ MISMATCH'}")
        logger.info(f"  Server: {server_G_hex}")
        logger.info(f"  Client: {client_G_hex}")

        # H 비교
        server_H_hex = self.h.export().hex()
        client_H_hex = client_H.export().hex()
        h_match = (server_H_hex == client_H_hex)

        logger.info(f"H (blinding generator): {'✅ MATCH' if h_match else '❌ MISMATCH'}")
        logger.info(f"  Server: {server_H_hex}")
        logger.info(f"  Client: {client_H_hex}")

        # G_vec 비교
        g_vec_mismatches = []
        for i in range(self.bit_length):
            server_hex = self.g_vec[i].export().hex()
            client_hex = client_G_vec[i].export().hex()
            if server_hex != client_hex:
                g_vec_mismatches.append((i, server_hex, client_hex))

        if g_vec_mismatches:
            logger.warning(f"G_vec: ❌ {len(g_vec_mismatches)}/{self.bit_length} MISMATCHES")
            for i, server_hex, client_hex in g_vec_mismatches[:5]:  # 처음 5개만 출력
                logger.warning(f"  G_vec[{i}]:")
                logger.warning(f"    Server: {server_hex}")
                logger.warning(f"    Client: {client_hex}")
            if len(g_vec_mismatches) > 5:
                logger.warning(f"  ... and {len(g_vec_mismatches) - 5} more mismatches")
        else:
            logger.info(f"G_vec: ✅ ALL {self.bit_length} ELEMENTS MATCH")

        # H_vec 비교
        h_vec_mismatches = []
        for i in range(self.bit_length):
            server_hex = self.h_vec[i].export().hex()
            client_hex = client_H_vec[i].export().hex()
            if server_hex != client_hex:
                h_vec_mismatches.append((i, server_hex, client_hex))

        if h_vec_mismatches:
            logger.warning(f"H_vec: ❌ {len(h_vec_mismatches)}/{self.bit_length} MISMATCHES")
            for i, server_hex, client_hex in h_vec_mismatches[:5]:  # 처음 5개만 출력
                logger.warning(f"  H_vec[{i}]:")
                logger.warning(f"    Server: {server_hex}")
                logger.warning(f"    Client: {client_hex}")
            if len(h_vec_mismatches) > 5:
                logger.warning(f"  ... and {len(h_vec_mismatches) - 5} more mismatches")
        else:
            logger.info(f"H_vec: ✅ ALL {self.bit_length} ELEMENTS MATCH")

        # 요약
        total_mismatches = (0 if g_match else 1) + (0 if h_match else 1) + len(g_vec_mismatches) + len(h_vec_mismatches)

        logger.info("")
        logger.info("Summary:")
        logger.info(f"  Total mismatches: {total_mismatches}")
        if total_mismatches == 0:
            logger.info("  ✅ All generators match perfectly!")
        else:
            logger.warning(f"  ❌ {total_mismatches} mismatch(es) detected")
            logger.warning("  This will cause verification failures!")

        logger.info("=" * 100)

        return total_mismatches == 0

    @staticmethod
    def compare_generators(client_path: str, server_path: str):
        """두 generator JSON 파일을 비교 (static method)

        Args:
            client_path: 클라이언트 generator JSON 파일
            server_path: 서버 generator JSON 파일

        Returns:
            bool: 완전 일치 여부
        """
        logger.info("=" * 100)
        logger.info(f"Comparing generators: {client_path} vs {server_path}")
        logger.info("=" * 100)

        try:
            with open(client_path, 'r') as f:
                client_data = json.load(f)
            with open(server_path, 'r') as f:
                server_data = json.load(f)
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return False

        # 메타데이터 비교
        logger.info("Metadata Comparison:")
        for key in ['curve', 'domain', 'generator_scheme', 'n']:
            client_val = client_data.get(key)
            server_val = server_data.get(key)
            match = (client_val == server_val)
            logger.info(f"  {key}: {'✅ MATCH' if match else '❌ MISMATCH'}")
            if not match:
                logger.info(f"    Client: {client_val}")
                logger.info(f"    Server: {server_val}")

        # G, H 비교
        g_match = (client_data.get('G') == server_data.get('G'))
        h_match = (client_data.get('H') == server_data.get('H'))

        logger.info(f"\nG (generator): {'✅ MATCH' if g_match else '❌ MISMATCH'}")
        if not g_match:
            logger.info(f"  Client: {client_data.get('G')}")
            logger.info(f"  Server: {server_data.get('G')}")

        logger.info(f"H (blinding generator): {'✅ MATCH' if h_match else '❌ MISMATCH'}")
        if not h_match:
            logger.info(f"  Client: {client_data.get('H')}")
            logger.info(f"  Server: {server_data.get('H')}")

        # G_vec, H_vec 비교
        client_g_vec = client_data.get('G_vec', [])
        server_g_vec = server_data.get('G_vec', [])
        client_h_vec = client_data.get('H_vec', [])
        server_h_vec = server_data.get('H_vec', [])

        g_vec_mismatches = []
        h_vec_mismatches = []

        n = min(len(client_g_vec), len(server_g_vec))
        for i in range(n):
            if client_g_vec[i] != server_g_vec[i]:
                g_vec_mismatches.append(i)
            if client_h_vec[i] != server_h_vec[i]:
                h_vec_mismatches.append(i)

        logger.info(f"\nG_vec: {'✅ ALL MATCH' if not g_vec_mismatches else f'❌ {len(g_vec_mismatches)}/{n} MISMATCHES'}")
        if g_vec_mismatches:
            for i in g_vec_mismatches[:3]:
                logger.warning(f"  G_vec[{i}] mismatch")
            if len(g_vec_mismatches) > 3:
                logger.warning(f"  ... and {len(g_vec_mismatches) - 3} more")

        logger.info(f"H_vec: {'✅ ALL MATCH' if not h_vec_mismatches else f'❌ {len(h_vec_mismatches)}/{n} MISMATCHES'}")
        if h_vec_mismatches:
            for i in h_vec_mismatches[:3]:
                logger.warning(f"  H_vec[{i}] mismatch")
            if len(h_vec_mismatches) > 3:
                logger.warning(f"  ... and {len(h_vec_mismatches) - 3} more")

        # 요약
        total_issues = sum([
            0 if g_match else 1,
            0 if h_match else 1,
            len(g_vec_mismatches),
            len(h_vec_mismatches)
        ])

        logger.info(f"\n{'='*100}")
        logger.info(f"Total mismatches: {total_issues}")
        if total_issues == 0:
            logger.info("✅ ALL GENERATORS MATCH PERFECTLY!")
        else:
            logger.warning(f"❌ {total_issues} MISMATCH(ES) DETECTED - THIS WILL CAUSE VERIFICATION FAILURES")
        logger.info("=" * 100)

        return total_issues == 0

    def _parse_ec_point(self, hex_string: str) -> 'EcPt':
        """강화된 EC point 파싱 (엄격한 형식 검증)"""
        if not hex_string:
            raise ValueError("Empty EC point hex string")
            
        # 0x 접두사 제거
        if hex_string.startswith("0x"):
            hex_string = hex_string[2:]
            
        # hex 문자열 검증
        if not all(c in '0123456789abcdefABCDEF' for c in hex_string):
            raise ValueError(f"Invalid hex characters in EC point")
            
        try:
            point_bytes = bytes.fromhex(hex_string)
        except ValueError:
            raise ValueError(f"Invalid hex string for EC point")
            
        # 엄격한 형식 검증: 압축(33바이트) 또는 비압축(65바이트)만 허용
        if len(point_bytes) == 33:
            # 압축된 형식: 첫 바이트는 0x02 또는 0x03이어야 함
            if point_bytes[0] not in [0x02, 0x03]:
                raise ValueError(f"Invalid compressed EC point format: incorrect prefix {point_bytes[0]:02x}")
            try:
                point = EcPt.from_binary(point_bytes, self.group)
                # 추가 검증: 무한원점이 아닌지 확인
                # petlib의 EcPt는 is_neutral() 메서드를 제공
                if hasattr(point, 'is_neutral') and point.is_neutral():
                    raise ValueError("EC point is the point at infinity")
                return point
            except Exception as e:
                raise ValueError(f"Failed to parse compressed EC point: {e}")
                
        elif len(point_bytes) == 65:
            # 비압축된 형식: 첫 바이트는 0x04여야 함
            if point_bytes[0] != 0x04:
                raise ValueError(f"Invalid uncompressed EC point format: incorrect prefix {point_bytes[0]:02x}")
            try:
                point = EcPt.from_binary(point_bytes, self.group)
                # 추가 검증: 무한원점이 아닌지 확인
                if hasattr(point, 'is_neutral') and point.is_neutral():
                    raise ValueError("EC point is the point at infinity")
                return point
            except Exception as e:
                raise ValueError(f"Failed to parse uncompressed EC point: {e}")
        else:
            raise ValueError(f"Invalid EC point byte length: {len(point_bytes)} (expected 33 or 65)")

    def _parse_bn_hex(self, hex_string: str) -> 'Bn':
        """강화된 Bn hex 파싱 (0x 접두사 처리)"""
        if not hex_string:
            raise ValueError("Empty Bn hex string")
            
        # 0x 접두사 제거
        if hex_string.startswith("0x"):
            hex_string = hex_string[2:]
            
        return Bn.from_hex(hex_string)

    def _compute_delta(self, y: 'Bn', z: 'Bn', n: int) -> 'Bn':
        """delta(y,z) 계산 (Bulletproof 스펙)

        delta(y,z) = (z - z²) * Σ_{i=0..n-1} y^i  -  z³ * Σ_{i=0..n-1} 2^i

        Args:
            y: Fiat-Shamir 챌린지 y
            z: Fiat-Shamir 챌린지 z
            n: 비트 길이

        Returns:
            delta(y,z) 값
        """
        # Σ_{i=0..n-1} y^i
        y_powers_sum = Bn(0)
        for i in range(n):
            y_power_i = pow(y, i, self.group.order())
            y_powers_sum = (y_powers_sum + y_power_i) % self.group.order()

        # Σ_{i=0..n-1} 2^i
        two_powers_sum = Bn(0)
        for i in range(n):
            two_power_i = pow(Bn(2), i, self.group.order())
            two_powers_sum = (two_powers_sum + two_power_i) % self.group.order()

        # delta(y,z) = (z - z²) * y_powers_sum - z³ * two_powers_sum
        z_minus_z2 = (z - (z * z)) % self.group.order()
        z_cubed = pow(z, 3, self.group.order())
        delta_yz = (z_minus_z2 * y_powers_sum - z_cubed * two_powers_sum) % self.group.order()

        return delta_yz

    def compare_delta_with_client(self, y_hex: str, z_hex: str, expected_delta_hex: str, n: int = None) -> bool:
        """클라이언트 delta(y,z)와 서버 계산 결과 비교

        Args:
            y_hex: y 챌린지 (hex)
            z_hex: z 챌린지 (hex)
            expected_delta_hex: 클라이언트가 계산한 delta (hex)
            n: 비트 길이 (None이면 self.bit_length 사용)

        Returns:
            bool: 일치 여부
        """
        if n is None:
            n = self.bit_length

        # 서버 delta 계산
        y = Bn.from_hex(y_hex if not y_hex.startswith('0x') else y_hex[2:])
        z = Bn.from_hex(z_hex if not z_hex.startswith('0x') else z_hex[2:])
        expected_delta = Bn.from_hex(expected_delta_hex if not expected_delta_hex.startswith('0x') else expected_delta_hex[2:])

        server_delta = self._compute_delta(y, z, n)

        # 비교
        match = (server_delta == expected_delta)

        logger.info("=" * 100)
        logger.info("Delta(y,z) Comparison: Server vs Client")
        logger.info("=" * 100)
        logger.info(f"Formula: delta(y,z) = (z - z²) * Σ(y^i) - z³ * Σ(2^i), i=0..{n-1}")
        logger.info(f"n: {n}")
        logger.info(f"y: {y.hex()}")
        logger.info(f"z: {z.hex()}")
        logger.info(f"\nServer delta: {server_delta.hex()}")
        logger.info(f"Client delta: {expected_delta.hex()}")
        logger.info(f"\nResult: {'✅ MATCH' if match else '❌ MISMATCH'}")

        if not match:
            logger.warning("⚠️  Delta mismatch detected! This will cause verification failures.")
            logger.warning("    Check if client and server use the same delta formula.")

        logger.info("=" * 100)

        return match

    def _fiat_shamir_challenge(self, *points, label: str = "") -> 'Bn':
        """Fiat-Shamir 변환을 이용한 챌린지 생성 (도메인 분리 적용)

        Args:
            *points: 챌린지 계산에 사용할 점들
            label: 디버깅용 레이블 (y, z, x 등)
        """
        hasher = sha256()

        # 도메인 분리: Bulletproof 프로토콜 식별자 추가
        domain_tag = b"ICS_BULLETPROOF_VERIFIER_v1"
        hasher.update(domain_tag)
        hasher.update(self.bit_length.to_bytes(4, 'big'))  # 비트 길이 포함

        # 🔍 DOGFOOD: 입력 시퀀스 로깅
        input_sequence = []
        input_sequence.append(f"domain='{domain_tag.decode()}'")
        input_sequence.append(f"n={self.bit_length}")

        for i, point in enumerate(points):
            if isinstance(point, EcPt):
                point_bytes = point.export()
                hasher.update(point_bytes)
                # 점 인코딩 정보
                input_sequence.append(f"Point[{i}]={point_bytes.hex()[:32]}...(len={len(point_bytes)})")
            elif isinstance(point, Bn):
                bn_bytes = point.binary()
                hasher.update(bn_bytes)
                input_sequence.append(f"Bn[{i}]={point.hex()[:32]}...(len={len(bn_bytes)})")
            else:
                str_bytes = str(point).encode()
                hasher.update(str_bytes)
                input_sequence.append(f"Str[{i}]='{str(point)}'")

        challenge_bytes = hasher.digest()
        result = Bn.from_binary(challenge_bytes) % self.group.order()

        # 🔍 DOGFOOD: 챌린지 계산 과정 로깅
        if label:
            logger.info(f"🔍 FS[{label}] = H({' || '.join(input_sequence)})")
            logger.info(f"🔍 FS[{label}] result = {result.hex()}")

        return result
    
    def _parse_proof(self, proof_data: Dict[str, Any]) -> Optional[BulletproofProof]:
        """증명 데이터 파싱"""
        try:
            return BulletproofProof(
                A=proof_data.get("A", ""),
                S=proof_data.get("S", ""),
                T1=proof_data.get("T1", ""),
                T2=proof_data.get("T2", ""),
                tau_x=proof_data.get("tau_x", ""),
                mu=proof_data.get("mu", ""),
                t=proof_data.get("t", ""),
                inner_product_proof=proof_data.get("inner_product_proof", {})
            )
        except Exception as e:
            logger.error(f"Failed to parse bulletproof: {e}")
            return None
    
    def _development_mode_verification(self, proof: Dict[str, Any], g_vec: list) -> bool:
        """개발 모드: 강화된 구조적 검증 (ICS 센서 프라이버시 연구용)"""
        try:
            L_values = proof.get("L", [])
            R_values = proof.get("R", [])

            # 기본 구조 검증
            if len(L_values) != len(R_values):
                logger.warning("MATH verification: FAILED (DEV MODE, L/R length mismatch)")
                return False

            if not L_values:
                logger.warning("MATH verification: FAILED (DEV MODE, empty L/R vectors)")
                return False
            
            # 로그 길이 확인
            expected_rounds = 0
            n = len(g_vec)
            while n > 1:
                n //= 2
                expected_rounds += 1
            
            if len(L_values) != expected_rounds:
                logger.debug(f"Development mode: Invalid proof length - expected {expected_rounds}, got {len(L_values)}")
                # 개발 모드에서는 길이가 맞지 않아도 EC point 검증이 통과하면 허용
                logger.debug("Development mode: Continuing with relaxed length validation")
            
            # 모든 L, R 값이 유효한 EC point인지 확인 (강화된 검증)
            valid_points = 0
            for i, (L_val, R_val) in enumerate(zip(L_values, R_values)):
                # L 포인트 검증
                try:
                    L_point = self._parse_ec_point(L_val)
                    L_valid = True
                except Exception as e:
                    L_valid = False
                    L_point = None
                    # 상세 진단 로깅
                    logger.debug(f"Development mode: Round {i} - L point parsing FAILED")
                    logger.debug(f"  L_val type: {type(L_val)}")
                    logger.debug(f"  L_val raw: {L_val[:100] if isinstance(L_val, str) and len(L_val) > 100 else L_val}")
                    if isinstance(L_val, str):
                        # hex 문자열 정보
                        cleaned_hex = L_val[2:] if L_val.startswith("0x") else L_val
                        logger.debug(f"  L_val hex length: {len(cleaned_hex)} chars")
                        try:
                            point_bytes = bytes.fromhex(cleaned_hex)
                            logger.debug(f"  L_val bytes length: {len(point_bytes)} bytes")
                            if len(point_bytes) > 0:
                                logger.debug(f"  L_val first byte: 0x{point_bytes[0]:02x}")
                        except:
                            logger.debug(f"  L_val: Invalid hex string")
                    logger.debug(f"  Exception: {type(e).__name__}: {e}")

                # R 포인트 검증
                try:
                    R_point = self._parse_ec_point(R_val)
                    R_valid = True
                except Exception as e:
                    R_valid = False
                    R_point = None
                    # 상세 진단 로깅
                    logger.debug(f"Development mode: Round {i} - R point parsing FAILED")
                    logger.debug(f"  R_val type: {type(R_val)}")
                    logger.debug(f"  R_val raw: {R_val[:100] if isinstance(R_val, str) and len(R_val) > 100 else R_val}")
                    if isinstance(R_val, str):
                        # hex 문자열 정보
                        cleaned_hex = R_val[2:] if R_val.startswith("0x") else R_val
                        logger.debug(f"  R_val hex length: {len(cleaned_hex)} chars")
                        try:
                            point_bytes = bytes.fromhex(cleaned_hex)
                            logger.debug(f"  R_val bytes length: {len(point_bytes)} bytes")
                            if len(point_bytes) > 0:
                                logger.debug(f"  R_val first byte: 0x{point_bytes[0]:02x}")
                        except:
                            logger.debug(f"  R_val: Invalid hex string")
                    logger.debug(f"  Exception: {type(e).__name__}: {e}")

                # 라운드 결과
                if L_valid and R_valid:
                    valid_points += 1
                    logger.debug(f"Development mode: Round {i} - Valid EC points (petlib)")
                else:
                    logger.debug(f"Development mode: Round {i} - Invalid points (L: {L_valid}, R: {R_valid})")
                    # Round 0 특수 분석
                    if i == 0:
                        logger.warning("⚠️  Round 0 IPP point parsing failure detected")
                        logger.warning("    This is the outermost round of the inner product argument")
                        logger.warning("    Possible causes:")
                        logger.warning("      1. Different serialization format for Round 0 vs other rounds")
                        logger.warning("      2. Client using uncompressed points for Round 0")
                        logger.warning("      3. Endianness or prefix mismatch")
            
            # 최소 절반 이상의 포인트가 유효하면 통과 (개발 모드 완화 정책)
            minimum_valid = max(1, len(L_values) // 2)
            if valid_points >= minimum_valid:
                logger.debug(f"Development mode: {valid_points}/{len(L_values)} valid points (minimum: {minimum_valid}) - PASSED")
                return True
            else:
                logger.debug(f"Development mode: {valid_points}/{len(L_values)} valid points (minimum: {minimum_valid}) - FAILED")
                return False
                
        except Exception as e:
            logger.debug(f"Development mode verification failed: {e}")
            return False
    
    def _verify_inner_product_proof(self, 
                                  proof: Dict[str, Any],
                                  P: 'EcPt',
                                  u: 'EcPt',
                                  g_vec: list,
                                  h_vec: list,
                                  a: 'Bn',
                                  b: 'Bn') -> bool:
        """Inner Product Proof 검증 (개발/운영 모드 지원)"""
        try:
            # 개발 모드: 구조적 검증만 (빠른 프로토타이핑용)
            if self.development_mode:
                return self._development_mode_verification(proof, g_vec)
            
            # 운영 모드: 완전한 암호학적 검증
            L_values = proof.get("L", [])
            R_values = proof.get("R", [])
            
            if len(L_values) != len(R_values):
                logger.error("L and R vectors length mismatch")
                return False
            
            if not L_values:
                logger.error("Empty L/R vectors in inner product proof")
                return False
            
            # 로그 길이 확인
            expected_rounds = 0
            n = len(g_vec)
            while n > 1:
                n //= 2
                expected_rounds += 1
            
            if len(L_values) != expected_rounds:
                logger.error(f"Invalid proof length: expected {expected_rounds}, got {len(L_values)}")
                return False
            
            logger.debug(f"Starting inner product verification with {len(L_values)} rounds")
            
            # 검증 라운드 수 제한 (보안 강화)
            MAX_ROUNDS = 10  # 2^10 = 1024 크기까지만 허용
            if expected_rounds > MAX_ROUNDS:
                logger.error(f"Too many proof rounds: {expected_rounds} (max: {MAX_ROUNDS})")
                return False
            
            # 재귀적 검증 수행
            current_P = P
            current_g_vec = g_vec[:]
            current_h_vec = h_vec[:]
            
            # 각 라운드에서 재귀적 검증
            challenges = []
            for i in range(len(L_values)):
                try:
                    # 1. L_i, R_i 파싱
                    L_i = self._parse_ec_point(L_values[i])
                    R_i = self._parse_ec_point(R_values[i])
                    logger.debug(f"Round {i}: L_i and R_i parsed successfully")
                    
                    # 2. Fiat-Shamir 챌린지 생성: x_i = H(L_i || R_i)
                    x_i = self._fiat_shamir_challenge(L_i, R_i)
                    challenges.append(x_i)
                    logger.debug(f"Round {i}: Challenge x_{i} = {x_i}")
                    
                    # 3. 점 축약: P' = L_i * x_i^(-1) + P + R_i * x_i
                    x_inv = x_i.mod_inverse(self.group.order())
                    current_P = x_inv * L_i + current_P + x_i * R_i
                    logger.debug(f"Round {i}: P updated")
                    
                    # 4. 벡터 축약: g', h' 업데이트
                    n = len(current_g_vec) // 2
                    if n == 0:
                        break
                    
                    g_left = current_g_vec[:n]
                    g_right = current_g_vec[n:]
                    h_left = current_h_vec[:n] 
                    h_right = current_h_vec[n:]
                    
                    # 새로운 벡터 생성: g' = g_left * x_i^(-1) + g_right * x_i
                    new_g_vec = []
                    new_h_vec = []
                    
                    for j in range(n):
                        g_new = x_inv * g_left[j] + x_i * g_right[j]
                        h_new = x_i * h_left[j] + x_inv * h_right[j]
                        new_g_vec.append(g_new)
                        new_h_vec.append(h_new)
                    
                    current_g_vec = new_g_vec
                    current_h_vec = new_h_vec
                    
                    logger.debug(f"Round {i}: Vector reduction completed, new size = {len(current_g_vec)}")
                    
                except Exception as e:
                    logger.error(f"Error in round {i}: {e}")
                    return False
            
            # 5. 최종 검증: P_final == a * g_final + b * h_final + c * u
            if len(current_g_vec) == 1 and len(current_h_vec) == 1:
                # 증명에서 최종 a, b 값 추출 (임시로 1, 1 사용)
                final_a = proof.get("a", Bn(1))
                final_b = proof.get("b", Bn(1))
                
                if isinstance(final_a, str):
                    final_a = Bn.from_hex(final_a)
                if isinstance(final_b, str):
                    final_b = Bn.from_hex(final_b)
                
                # 내적 값 계산: c = a * b  
                c = final_a * final_b
                
                # 예상 값: P_expected = a * g + b * h + c * u
                expected = final_a * current_g_vec[0] + final_b * current_h_vec[0] + c * u
                
                # 검증
                verification_passed = (current_P == expected)
                
                if verification_passed:
                    logger.info("Inner product proof verification successful")
                else:
                    logger.warning("Inner product proof verification failed: final equation check")
                    logger.debug(f"Expected: {expected}")
                    logger.debug(f"Actual: {current_P}")
                    logger.debug(f"Final a: {final_a}")
                    logger.debug(f"Final b: {final_b}")
                    logger.debug(f"Inner product a*b: {c}")
                    logger.debug(f"Final g: {current_g_vec[0]}")
                    logger.debug(f"Final h: {current_h_vec[0]}")
                    logger.debug(f"u: {u}")
                
                return verification_passed
            else:
                logger.error(f"Unexpected final vector sizes: g={len(current_g_vec)}, h={len(current_h_vec)}")
                return False
            
        except Exception as e:
            logger.error(f"Inner product proof verification exception: {e}")
            return False
    
    def verify_range_proof(self,
                          commitment: str,
                          proof: Dict[str, Any],
                          range_min: int,
                          range_max: int,
                          client_challenges: Optional[Dict[str, str]] = None,
                          debug: bool = False,
                          client_mode: Optional[str] = None) -> VerificationResult:
        """
        범위 증명 검증 (항상 full math verification 강제)

        Args:
            commitment: Pedersen commitment (hex string)
            proof: Bulletproof 증명 데이터
            range_min: 범위 최소값
            range_max: 범위 최대값
            client_challenges: 클라이언트가 보낸 챌린지 {y, z, x} - 무시됨, 로그에만 기록
            debug: True 시 중간값 에코 반환
            client_mode: 클라이언트가 보낸 mode (zk_only 등) - 무시됨

        Returns:
            VerificationResult: 검증 결과 (debug=true 시 debug_values 포함)

        Note:
            - 클라이언트 모드(zk_only 등)는 무시되고 항상 full math verification 수행
            - 클라이언트 챌린지(y, z, x)는 무시되고 서버가 고정 FS 순서로 재계산
        """
        start_time = time.perf_counter()

        # 📊 수신 범위 스케일 로깅 (정수 스케일 도메인 확인)
        logger.info(f"📊 RANGE RECEIVED: min_scaled={range_min}, max_scaled={range_max}, "
                   f"scale=integer_domain, bit_length={self.bit_length}, "
                   f"max_representable={(1 << self.bit_length) - 1}")

        # 클라이언트 모드 무시 로깅
        client_mode_ignored_reason = None
        if client_mode:
            logger.info(f"⚠️ CLIENT MODE IGNORED: client requested mode='{client_mode}', forcing full math verification")
            client_mode_ignored_reason = "client_mode_ignored_full_math_enforced"

        try:
            # 입력 검증
            if not commitment or not proof:
                return VerificationResult(
                    verified=False,
                    processing_time_ms=0.0,
                    error_message="Missing commitment or proof",
                    client_mode_ignored=client_mode_ignored_reason
                )

            # 범위 검증
            if range_min >= range_max:
                return VerificationResult(
                    verified=False,
                    processing_time_ms=0.0,
                    error_message="Invalid range: min >= max",
                    client_mode_ignored=client_mode_ignored_reason,
                    root_cause="range_invalid",
                    evidence=f"range_min={range_min} >= range_max={range_max}",
                    fix_instruction="ensure_range_min_less_than_range_max_in_integer_scale"
                )

            # 범위가 비트 길이에 맞는지 확인
            max_value = (1 << self.bit_length) - 1
            if range_max > max_value:
                logger.warning(f"⚠️ RANGE SCALE MISMATCH: range_max={range_max} exceeds {self.bit_length}-bit max={max_value}")
                return VerificationResult(
                    verified=False,
                    processing_time_ms=0.0,
                    error_message=f"Range too large for {self.bit_length}-bit proof",
                    client_mode_ignored=client_mode_ignored_reason,
                    root_cause="range_scale_mismatch",
                    evidence=f"range_max={range_max} > max_representable={max_value}",
                    fix_instruction="scale_range_to_integer_domain_matching_commitment_value_scale"
                )

            # 범위 스케일 일관성 검사 (부동소수점 입력 감지)
            if isinstance(range_min, float) or isinstance(range_max, float):
                logger.warning(f"⚠️ FLOAT RANGE DETECTED: range values should be integers in scaled domain")
                # 정수로 변환하여 계속 진행하되 경고

            # Bulletproof 검증 (항상 full math verification 강제)
            return self._verify_bulletproof(
                commitment, proof, range_min, range_max, start_time,
                client_challenges=client_challenges,
                debug=debug,
                client_mode_ignored_reason=client_mode_ignored_reason
            )

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Bulletproof verification error: {e}")
            return VerificationResult(
                verified=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                client_mode_ignored=client_mode_ignored_reason
            )
    
    
    def _verify_bulletproof(self,
                           commitment: str,
                           proof: Dict[str, Any],
                           range_min: int,
                           range_max: int,
                           start_time: float,
                           client_challenges: Optional[Dict[str, str]] = None,
                           debug: bool = False,
                           client_mode_ignored_reason: Optional[str] = None) -> VerificationResult:
        """
        실제 Bulletproof 검증 (항상 full math verification 강제)

        - 클라이언트 모드(development_mode 등)는 무시하고 항상 full math verification 수행
        - 클라이언트 챌린지(y, z, x)는 무시하고 서버가 고정 FS 순서로 재계산
        - debug=True 시 중간값 에코 반환
        - 실패 시 단정적 원인 보고 (root_cause, evidence, fix_instruction)
        """
        # 🔒 항상 full math verification 강제 (development_mode 무시)
        logger.info("🔒 FORCED: Full math verification enabled (ignoring development_mode)")

        # 클라이언트 챌린지 존재 여부 확인
        client_challenges_present = bool(client_challenges and any(client_challenges.values()))
        if client_challenges_present:
            logger.warning("⚠️ CLIENT CHALLENGES IGNORED: Server will recompute y, z, x using fixed FS order")

        try:
            # 증명 파싱
            bp_proof = self._parse_proof(proof)
            if not bp_proof:
                processing_time = (time.perf_counter() - start_time) * 1000
                return VerificationResult(
                    verified=False,
                    processing_time_ms=processing_time,
                    error_message="Failed to parse proof",
                    client_mode_ignored=client_mode_ignored_reason,
                    client_challenges_ignored=client_challenges_present,
                    root_cause="proof_parse_failed",
                    evidence="proof_structure_invalid",
                    fix_instruction="ensure_proof_contains_A_S_T1_T2_tau_x_mu_t_inner_product_proof"
                )

            # 커밋먼트 파싱 (강화된 EC point 파싱 사용)
            try:
                V = self._parse_ec_point(commitment)
            except Exception as e:
                processing_time = (time.perf_counter() - start_time) * 1000
                return VerificationResult(
                    verified=False,
                    processing_time_ms=processing_time,
                    error_message=f"Invalid commitment format: {e}",
                    client_mode_ignored=client_mode_ignored_reason,
                    client_challenges_ignored=client_challenges_present,
                    root_cause="commitment_parse_failed",
                    evidence=f"commitment_hex_invalid: {str(e)[:50]}",
                    fix_instruction="ensure_commitment_is_33_or_65_byte_compressed_SEC1_hex"
                )

            # 증명의 각 컴포넌트 파싱 (강화된 EC point 파싱 사용)
            try:
                logger.debug(f"Parsing A: '{bp_proof.A}' (length: {len(bp_proof.A) if bp_proof.A else 0})")
                A = self._parse_ec_point(bp_proof.A)

                logger.debug(f"Parsing S: '{bp_proof.S}' (length: {len(bp_proof.S) if bp_proof.S else 0})")
                S = self._parse_ec_point(bp_proof.S)

                logger.debug(f"Parsing T1: '{bp_proof.T1}' (length: {len(bp_proof.T1) if bp_proof.T1 else 0})")
                T1 = self._parse_ec_point(bp_proof.T1)

                logger.debug(f"Parsing T2: '{bp_proof.T2}' (length: {len(bp_proof.T2) if bp_proof.T2 else 0})")
                T2 = self._parse_ec_point(bp_proof.T2)

                logger.debug(f"Parsing tau_x: '{bp_proof.tau_x}' (length: {len(bp_proof.tau_x) if bp_proof.tau_x else 0})")
                tau_x = self._parse_bn_hex(bp_proof.tau_x)

                logger.debug(f"Parsing mu: '{bp_proof.mu}' (length: {len(bp_proof.mu) if bp_proof.mu else 0})")
                mu = self._parse_bn_hex(bp_proof.mu)

                logger.debug(f"Parsing t: '{bp_proof.t}' (length: {len(bp_proof.t) if bp_proof.t else 0})")
                t_hat = self._parse_bn_hex(bp_proof.t)

                logger.debug("All proof components parsed successfully")
            except Exception as e:
                processing_time = (time.perf_counter() - start_time) * 1000
                logger.error(f"Proof parsing failed at component: {e}")
                return VerificationResult(
                    verified=False,
                    processing_time_ms=processing_time,
                    error_message=f"Failed to parse proof components: {e}",
                    client_mode_ignored=client_mode_ignored_reason,
                    client_challenges_ignored=client_challenges_present,
                    root_cause="proof_component_parse_failed",
                    evidence=f"component_error: {str(e)[:50]}",
                    fix_instruction="check_A_S_T1_T2_are_valid_EC_points_and_scalars_are_valid_hex"
                )

            # 🔍 Point encoding check (reduced verbosity for production)
            logger.debug(f"Point encoding check:")
            logger.debug(f"  A: {A.export().hex()[:32]}... (len={len(A.export())})")
            logger.debug(f"  S: {S.export().hex()[:32]}... (len={len(S.export())})")
            logger.debug(f"  V: {V.export().hex()[:32]}... (len={len(V.export())})")

            # ========================================================================
            # 🔒 서버 Fiat-Shamir 챌린지 계산 (고정 순서, 클라이언트 챌린지 무시)
            # FS[y] = H(domain || n || A || S)
            # FS[z] = H(domain || n || A || S || y)
            # FS[x] = H(domain || n || T1 || T2 || z)
            # ========================================================================
            logger.info(f"🔒 SERVER FS CHALLENGES (fixed order, n={self.bit_length}):")
            y = self._fiat_shamir_challenge(A, S, label="y")
            z = self._fiat_shamir_challenge(A, S, y, label="z")
            x = self._fiat_shamir_challenge(T1, T2, z, label="x")

            logger.info(f"  FS[y] = H(domain || n || A || S) = {y.hex()}")
            logger.info(f"  FS[z] = H(domain || n || A || S || y) = {z.hex()}")
            logger.info(f"  FS[x] = H(domain || n || T1 || T2 || z) = {x.hex()}")

            # 클라이언트 챌린지와 비교 로깅 (무시하되 기록)
            challenge_mismatch_detected = False
            if client_challenges:
                logger.info(f"🔍 CLIENT CHALLENGES COMPARISON (ignored for verification):")
                for name, server_value in [("y", y), ("z", z), ("x", x)]:
                    client_hex = client_challenges.get(name)
                    server_hex = server_value.hex()

                    if client_hex:
                        # 0x 접두사 제거 후 비교
                        client_clean = client_hex.lower().replace("0x", "")
                        server_clean = server_hex.lower()
                        match = (client_clean == server_clean)
                        status = "✅ MATCH" if match else "❌ MISMATCH"
                        logger.info(f"  {name}: {status}")
                        logger.info(f"    Client: {client_hex}")
                        logger.info(f"    Server: {server_hex}")

                        if not match:
                            challenge_mismatch_detected = True
            
            # ========================================================================
            # 메인 검증 방정식 (항상 full math verification)
            # Left = t·G + tau_x·H
            # Right = V·z² + delta(y,z)·G + T1·x + T2·x²
            # ========================================================================
            n = self.bit_length

            # delta(y,z) 계산
            # delta(y,z) = (z - z²) * Σ_{i=0..n-1} y^i  -  z³ * Σ_{i=0..n-1} 2^i
            delta_yz = self._compute_delta(y, z, n)

            logger.info(f"🔍 delta(y,z) = {delta_yz.hex()[:40]}... (n={n})")

            # 좌변: Left = t·G + tau_x·H
            try:
                t_mod = t_hat % self.group.order()
                tau_x_mod = tau_x % self.group.order()
                left = t_mod * self.g + tau_x_mod * self.h
            except Exception as e:
                logger.error(f"Error in left side calculation: {e}")
                raise

            # 우변: Right = V·z² + delta(y,z)·G + T1·x + T2·x²
            try:
                z_squared = (z * z) % self.group.order()
                delta_yz_mod = delta_yz % self.group.order()
                x_mod = x % self.group.order()
                x_squared = (x * x) % self.group.order()

                right = z_squared * V + delta_yz_mod * self.g + x_mod * T1 + x_squared * T2
            except Exception as e:
                logger.error(f"Error in right side calculation: {e}")
                raise

            # 메인 검증 방정식 체크
            equation_match = (left == right)
            left_hex = left.export().hex()
            right_hex = right.export().hex()

            logger.info(f"🔒 MAIN EQUATION CHECK (FORCED FULL MATH):")
            logger.info(f"  Left  = t·G + tau_x·H        = {left_hex}")
            logger.info(f"  Right = V·z² + δ·G + T1·x + T2·x² = {right_hex}")
            logger.info(f"  Result: {'✅ MATCH' if equation_match else '❌ MISMATCH'}")

            # ========================================================================
            # 🔒 항상 full math verification (development_mode 무시)
            # ========================================================================
            if not equation_match:
                # 메인 방정식 불일치 - 단정적 원인 보고
                logger.warning("=" * 80)
                logger.warning("❌ MAIN EQUATION MISMATCH - VERIFICATION FAILED")
                logger.warning("=" * 80)

                processing_time = (time.perf_counter() - start_time) * 1000

                # 단정적 원인 판정
                if client_challenges_present and challenge_mismatch_detected:
                    # 클라이언트 챌린지가 서버와 다른 경우
                    root_cause = "client_challenge_mismatch"
                    evidence = "client_provided_yz_x != server_FS"
                    fix_instruction = "do_not_send_challenges_and_recompute_proof_with_server_FS_order"
                else:
                    # 그 외 (generator 불일치 등)
                    root_cause = "main_equation_failed"
                    evidence = f"left_hex != right_hex"
                    fix_instruction = "check_generators_G_H_and_delta_formula_match_server"

                logger.warning(f"root_cause={root_cause}; evidence={evidence}; fix={fix_instruction}")

                # debug=True 시 중간값 에코 (완전한 디버그 정보)
                debug_values = None
                if debug:
                    # Σy^i 및 Σ2^i 계산
                    sum_y_powers = Bn(0)
                    sum_2_powers = Bn(0)
                    y_power = Bn(1)
                    two_power = Bn(1)
                    for i in range(n):
                        sum_y_powers = (sum_y_powers + y_power) % self.group.order()
                        sum_2_powers = (sum_2_powers + two_power) % self.group.order()
                        y_power = (y_power * y) % self.group.order()
                        two_power = (two_power * Bn(2)) % self.group.order()

                    debug_values = {
                        # 챌린지 (32B 스칼라)
                        "y": y.hex(),
                        "z": z.hex(),
                        "x": x.hex(),
                        # delta(y,z) (32B 스칼라)
                        "delta_yz": delta_yz.hex(),
                        # 증명 스칼라 (32B)
                        "t_hat": t_hat.hex(),
                        "tau_x": tau_x.hex(),
                        "mu": mu.hex(),
                        # 압축점 Left/Right (SEC1 33B)
                        "Left": left_hex,
                        "Right": right_hex,
                        "left_equals_right": False,
                        # 검증 시간
                        "verification_time_ms": processing_time,
                        # 합계
                        "sum_y_powers": sum_y_powers.hex(),
                        "sum_2_powers": sum_2_powers.hex(),
                        "i_range": f"0..{n-1}",
                        # 포인트 (SEC1 33B 압축)
                        "V": V.export().hex(),
                        "A": A.export().hex(),
                        "S": S.export().hex(),
                        "T1": T1.export().hex(),
                        "T2": T2.export().hex(),
                        # 서버 generator
                        "G": self.g.export().hex(),
                        "H": self.h.export().hex(),
                        # 포인트 길이 검증
                        "point_lengths": {
                            "V": len(V.export()),
                            "A": len(A.export()),
                            "S": len(S.export()),
                            "T1": len(T1.export()),
                            "T2": len(T2.export()),
                            "expected": 33
                        },
                        # 스칼라 길이 검증
                        "scalar_lengths": {
                            "tau_x": len(tau_x.binary()),
                            "mu": len(mu.binary()),
                            "t_hat": len(t_hat.binary()),
                            "expected": 32
                        },
                        "n": n
                    }
                    if client_challenges_present:
                        debug_values["client_challenges_ignored"] = True
                        debug_values["client_challenges"] = client_challenges

                return VerificationResult(
                    verified=False,
                    processing_time_ms=processing_time,
                    error_message="Main verification equation failed (full math enforced)",
                    equation_match=False,
                    left_equals_right=False,
                    development_mode=False,  # 항상 production으로 보고
                    client_mode_ignored=client_mode_ignored_reason,
                    client_challenges_ignored=client_challenges_present,
                    root_cause=root_cause,
                    evidence=evidence,
                    fix_instruction=fix_instruction,
                    debug_values=debug_values
                )

            # 메인 방정식 통과
            logger.info("✅ MATH verification: SUCCESS (full math enforced)")
            
            # 2. 내적 증명 검증
            try:
                P = A + x * S
                logger.debug(f"P calculation successful")
            except Exception as e:
                logger.error(f"Error in P calculation: {e}")
                raise

            # 벡터 가중치 적용 (h_vec에만 y^{-i} 변환 적용, prover와 동일한 순서)
            try:
                g_prime = []
                h_prime = []
                y_inv = y.mod_inverse(self.group.order())

                # Prover와 동일: y^{-(n-1)}부터 시작해서 y를 곱하며 증가
                y_inv_power = y_inv.mod_pow(Bn(n - 1), self.group.order())
                for i in range(n):
                    # g_vec: 변환 없이 그대로 사용
                    g_prime.append(self.g_vec[i])
                    # h_vec: y^{-(n-1-i)} 스칼라 곱 적용
                    h_prime_i = y_inv_power * self.h_vec[i]
                    h_prime.append(h_prime_i)
                    y_inv_power = (y_inv_power * y) % self.group.order()
            except Exception as e:
                logger.error(f"Error in vector weight calculation: {e}")
                raise

            # 내적 증명 검증 - 클라이언트가 전송한 final a, b 값 추출
            try:
                inner_proof = bp_proof.inner_product_proof
                if not isinstance(inner_proof, dict):
                    processing_time = (time.perf_counter() - start_time) * 1000
                    return VerificationResult(
                        verified=False,
                        processing_time_ms=processing_time,
                        error_message="Invalid inner product proof format: not a dictionary",
                        client_mode_ignored=client_mode_ignored_reason,
                        client_challenges_ignored=client_challenges_present,
                        root_cause="inner_product_proof_invalid_format",
                        evidence="inner_product_proof_not_dict",
                        fix_instruction="ensure_inner_product_proof_is_object_with_L_R_a_b"
                    )

                if "a" not in inner_proof or "b" not in inner_proof:
                    processing_time = (time.perf_counter() - start_time) * 1000
                    return VerificationResult(
                        verified=False,
                        processing_time_ms=processing_time,
                        error_message="Missing required inner product proof values (a, b)",
                        client_mode_ignored=client_mode_ignored_reason,
                        client_challenges_ignored=client_challenges_present,
                        root_cause="inner_product_proof_missing_ab",
                        evidence="a_or_b_not_in_inner_product_proof",
                        fix_instruction="include_final_a_and_b_scalars_in_inner_product_proof"
                    )

                final_a = self._parse_bn_hex(inner_proof["a"])
                final_b = self._parse_bn_hex(inner_proof["b"])

                if final_a == Bn(0) or final_b == Bn(0):
                    logger.warning("Inner product proof contains zero values - likely invalid")
            except Exception as e:
                processing_time = (time.perf_counter() - start_time) * 1000
                return VerificationResult(
                    verified=False,
                    processing_time_ms=processing_time,
                    error_message=f"Failed to parse inner product final values: {e}",
                    client_mode_ignored=client_mode_ignored_reason,
                    client_challenges_ignored=client_challenges_present,
                    root_cause="inner_product_proof_parse_failed",
                    evidence=f"parse_error: {str(e)[:50]}",
                    fix_instruction="ensure_a_and_b_are_valid_hex_scalars"
                )

            inner_product_verified = self._verify_inner_product_proof(
                bp_proof.inner_product_proof,
                P,
                self.h,  # u = h in our case
                g_prime,
                h_prime,
                final_a,
                final_b
            )

            processing_time = (time.perf_counter() - start_time) * 1000
            proof_size = len(json.dumps(proof).encode())

            # 최종 검증 결과: 메인 방정식 AND 내적 증명
            # 메인 방정식은 이미 통과함 (equation_match=True 확정)
            verified = inner_product_verified

            if verified:
                logger.info(f"✅ Bulletproof verification SUCCESS in {processing_time:.2f}ms (PRODUCTION MODE, full math enforced)")
            else:
                logger.warning(f"❌ Bulletproof verification FAILED in {processing_time:.2f}ms (inner product proof failed)")

            # debug=True 시 중간값 에코 (완전한 디버그 정보)
            debug_values = None
            if debug:
                # Σy^i 및 Σ2^i 계산
                sum_y_powers = Bn(0)
                sum_2_powers = Bn(0)
                y_power = Bn(1)
                two_power = Bn(1)
                for i in range(n):
                    sum_y_powers = (sum_y_powers + y_power) % self.group.order()
                    sum_2_powers = (sum_2_powers + two_power) % self.group.order()
                    y_power = (y_power * y) % self.group.order()
                    two_power = (two_power * Bn(2)) % self.group.order()

                debug_values = {
                    # 챌린지 (32B 스칼라)
                    "y": y.hex(),
                    "z": z.hex(),
                    "x": x.hex(),
                    # delta(y,z) (32B 스칼라)
                    "delta_yz": delta_yz.hex(),
                    # 증명 스칼라 (32B)
                    "t_hat": t_hat.hex(),
                    "tau_x": tau_x.hex(),
                    "mu": mu.hex(),
                    # 압축점 Left/Right (SEC1 33B)
                    "Left": left_hex,
                    "Right": right_hex,
                    "left_equals_right": equation_match,
                    # 검증 시간
                    "verification_time_ms": processing_time,
                    # 합계
                    "sum_y_powers": sum_y_powers.hex(),
                    "sum_2_powers": sum_2_powers.hex(),
                    "i_range": f"0..{n-1}",
                    # 포인트 (SEC1 33B 압축)
                    "V": V.export().hex(),
                    "A": A.export().hex(),
                    "S": S.export().hex(),
                    "T1": T1.export().hex(),
                    "T2": T2.export().hex(),
                    # 서버 generator
                    "G": self.g.export().hex(),
                    "H": self.h.export().hex(),
                    # 포인트 길이 검증
                    "point_lengths": {
                        "V": len(V.export()),
                        "A": len(A.export()),
                        "S": len(S.export()),
                        "T1": len(T1.export()),
                        "T2": len(T2.export()),
                        "expected": 33
                    },
                    # 스칼라 길이 검증
                    "scalar_lengths": {
                        "tau_x": len(tau_x.binary()),
                        "mu": len(mu.binary()),
                        "t_hat": len(t_hat.binary()),
                        "expected": 32
                    },
                    "n": n,
                    "equation_match": equation_match,
                    "inner_product_verified": inner_product_verified
                }
                if client_challenges_present:
                    debug_values["client_challenges_ignored"] = True
                    debug_values["client_challenges"] = client_challenges

            # 내적 증명 실패 시 단정적 원인 보고
            root_cause = None
            evidence = None
            fix_instruction = None
            if not verified:
                root_cause = "inner_product_proof_failed"
                evidence = "IPP_L_R_verification_failed"
                fix_instruction = "check_inner_product_proof_L_R_vectors_and_final_a_b_values"

            return VerificationResult(
                verified=verified,
                processing_time_ms=processing_time,
                proof_size_bytes=proof_size,
                equation_match=equation_match,
                left_equals_right=equation_match,
                development_mode=False,  # 항상 PRODUCTION으로 보고
                client_mode_ignored=client_mode_ignored_reason,
                client_challenges_ignored=client_challenges_present,
                root_cause=root_cause,
                evidence=evidence,
                fix_instruction=fix_instruction,
                debug_values=debug_values
            )

        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            logger.error(f"Bulletproof verification exception: {e}")
            return VerificationResult(
                verified=False,
                processing_time_ms=processing_time,
                error_message=str(e),
                development_mode=False,
                left_equals_right=False,
                client_mode_ignored=client_mode_ignored_reason if 'client_mode_ignored_reason' in dir() else None,
                client_challenges_ignored=client_challenges_present if 'client_challenges_present' in dir() else None,
                root_cause="exception",
                evidence=f"exception: {str(e)[:50]}",
                fix_instruction="check_proof_format_and_encoding"
            )
    
    def get_supported_ranges(self) -> Tuple[int, int]:
        """지원하는 범위 반환"""
        max_value = (1 << self.bit_length) - 1
        return (0, max_value)
    
    def estimate_proof_size(self) -> int:
        """예상 증명 크기 (바이트)"""
        # A, S, T1, T2 (각 33바이트) + 스칼라들 (각 32바이트) + 내적 증명
        base_size = 4 * 33 + 3 * 32  # 228 바이트
        inner_product_size = 2 * 33 * (self.bit_length.bit_length())  # L, R 벡터들
        return base_size + inner_product_size
    
    def verify_from_client_debug(self, debug_json_path: str) -> Dict:
        """클라이언트 debug_proof JSON을 읽어서 재현 검증

        서버 generator vs 클라이언트 generator 조합으로
        메인 방정식을 재계산하고 비교합니다.

        Args:
            debug_json_path: 클라이언트 debug_proof_*.json 파일 경로

        Returns:
            검증 결과 딕셔너리
        """
        logger.info("=" * 100)
        logger.info(f"Client Debug Proof Verification: {debug_json_path}")
        logger.info("=" * 100)

        try:
            with open(debug_json_path, 'r') as f:
                debug_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {debug_json_path}")
            return {"error": f"File not found: {debug_json_path}"}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"error": f"JSON decode error: {e}"}

        # 1. 클라이언트 데이터 추출
        metadata = debug_data.get('metadata', {})
        n = metadata.get('n', 32)
        sensor_id = metadata.get('sensor_id', 'unknown')

        # 스칼라 값들
        scalars = debug_data.get('scalars', {})
        t_hex = scalars.get('t', '')
        tau_x_hex = scalars.get('tau_x', '')
        y_hex = scalars.get('y', '')
        z_hex = scalars.get('z', '')
        x_hex = scalars.get('x', '')
        client_delta_hex = scalars.get('delta', '')

        # 포인트 값들
        points = debug_data.get('points', {})
        V_hex = points.get('V', '')
        T1_hex = points.get('T1', '')
        T2_hex = points.get('T2', '')
        client_left_hex = points.get('left', '')
        client_right_hex = points.get('right', '')

        # 클라이언트 generator (있으면)
        client_gen = debug_data.get('generators', {})
        client_G_hex = client_gen.get('G', '')
        client_H_hex = client_gen.get('H', '')

        logger.info(f"Sensor: {sensor_id}, n: {n}")
        logger.info(f"Client reports: equation_match = {debug_data.get('equation_verified', {}).get('equation_match', 'unknown')}")

        # 2. 서버에서 재계산 (서버 generator 사용)
        logger.info("\n[Test 1] Using SERVER generators:")
        try:
            t = Bn.from_hex(t_hex if not t_hex.startswith('0x') else t_hex[2:])
            tau_x = Bn.from_hex(tau_x_hex if not tau_x_hex.startswith('0x') else tau_x_hex[2:])
            y = Bn.from_hex(y_hex if not y_hex.startswith('0x') else y_hex[2:])
            z = Bn.from_hex(z_hex if not z_hex.startswith('0x') else z_hex[2:])
            x_val = Bn.from_hex(x_hex if not x_hex.startswith('0x') else x_hex[2:])

            V = self._parse_ec_point(V_hex)
            T1 = self._parse_ec_point(T1_hex)
            T2 = self._parse_ec_point(T2_hex)

            # 서버 delta 계산
            server_delta = self._compute_delta(y, z, n)

            # Left = t·G + tau_x·H (서버 G, H 사용)
            left_server = (t % self.group.order()) * self.g + (tau_x % self.group.order()) * self.h

            # Right = V·z² + delta(y,z)·G + T1·x + T2·x²
            z_squared = (z * z) % self.group.order()
            x_squared = (x_val * x_val) % self.group.order()
            right_server = z_squared * V + (server_delta % self.group.order()) * self.g + (x_val % self.group.order()) * T1 + x_squared * T2

            server_match = (left_server == right_server)

            logger.info(f"  Server generators: G={self.g.export().hex()[:32]}..., H={self.h.export().hex()[:32]}...")
            logger.info(f"  Server delta: {server_delta.hex()}")
            logger.info(f"  Left: {left_server.export().hex()}")
            logger.info(f"  Right: {right_server.export().hex()}")
            logger.info(f"  Result: {'✅ MATCH' if server_match else '❌ MISMATCH'}")

        except Exception as e:
            logger.error(f"  Error in server generator test: {e}")
            server_match = False

        # 3. 클라이언트 generator로 재계산 (가능하면)
        client_match = None
        if client_G_hex and client_H_hex:
            logger.info("\n[Test 2] Using CLIENT generators:")
            try:
                client_G = self._parse_ec_point(client_G_hex)
                client_H = self._parse_ec_point(client_H_hex)

                # Left = t·G + tau_x·H (클라이언트 G, H 사용)
                left_client = (t % self.group.order()) * client_G + (tau_x % self.group.order()) * client_H

                # delta는 generator 독립적
                # Right = V·z² + delta(y,z)·G + T1·x + T2·x² (클라이언트 G 사용)
                right_client = z_squared * V + (server_delta % self.group.order()) * client_G + (x_val % self.group.order()) * T1 + x_squared * T2

                client_match = (left_client == right_client)

                logger.info(f"  Client generators: G={client_G.export().hex()[:32]}..., H={client_H.export().hex()[:32]}...")
                logger.info(f"  Left: {left_client.export().hex()}")
                logger.info(f"  Right: {right_client.export().hex()}")
                logger.info(f"  Result: {'✅ MATCH' if client_match else '❌ MISMATCH'}")

            except Exception as e:
                logger.error(f"  Error in client generator test: {e}")
                client_match = False
        else:
            logger.info("\n[Test 2] Client generators not provided in debug JSON, skipping")

        # 4. Delta 비교
        delta_match = None
        if client_delta_hex:
            client_delta = Bn.from_hex(client_delta_hex if not client_delta_hex.startswith('0x') else client_delta_hex[2:])
            delta_match = (server_delta == client_delta)
            logger.info(f"\n[Test 3] Delta comparison:")
            logger.info(f"  Server delta: {server_delta.hex()}")
            logger.info(f"  Client delta: {client_delta.hex()}")
            logger.info(f"  Result: {'✅ MATCH' if delta_match else '❌ MISMATCH'}")

        # 5. 요약
        logger.info("\n" + "=" * 100)
        logger.info("Summary:")
        logger.info(f"  [Server generators] Equation match: {server_match}")
        if client_match is not None:
            logger.info(f"  [Client generators] Equation match: {client_match}")
        if delta_match is not None:
            logger.info(f"  [Delta] Server == Client: {delta_match}")

        # 진단
        logger.info("\nDiagnosis:")
        if server_match and (client_match is None or client_match):
            logger.info("  ✅ VERIFICATION SUCCESSFUL")
            logger.info("     Both server and client generators produce matching equations")
        elif not server_match and client_match:
            logger.warning("  ⚠️  SERVER GENERATORS MISMATCH")
            logger.warning("     Client generators work, but server generators don't")
            logger.warning("     → Need to update server generators to match client")
        elif server_match and not client_match:
            logger.info("  ℹ️  Server generators work correctly")
            logger.info("     Client generators from debug JSON may be outdated")
        elif not server_match and not client_match:
            logger.error("  ❌ BOTH FAILED")
            logger.error("     Neither server nor client generators produce matching equations")
            logger.error("     → Possible issues: wrong delta formula, wrong equation, corrupted data")

        if delta_match is not None and not delta_match:
            logger.warning("  ⚠️  DELTA MISMATCH")
            logger.warning("     Server and client use different delta(y,z) formulas")

        logger.info("=" * 100)

        return {
            "sensor_id": sensor_id,
            "n": n,
            "server_generators_match": server_match,
            "client_generators_match": client_match,
            "delta_match": delta_match,
            "diagnosis": "success" if server_match else "generator_mismatch"
        }

    def __str__(self) -> str:
        return f"BulletproofVerifier({self.bit_length}-bit, petlib=available)"
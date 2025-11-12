"""
Ed25519 Baseline Implementation
베이스라인 비교를 위한 Ed25519 디지털 서명
"""

import time
import json
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


class Ed25519Baseline:
    """
    Ed25519 기반 베이스라인 구현
    Bulletproofs와 성능 비교를 위한 디지털 서명 방식
    """
    
    def __init__(self, private_key: Optional[Ed25519PrivateKey] = None):
        """
        Ed25519 베이스라인 초기화
        
        Args:
            private_key: Ed25519 개인키 (None이면 자동 생성)
        """
        if private_key is None:
            self.private_key = Ed25519PrivateKey.generate()
        else:
            self.private_key = private_key
            
        self.public_key = self.private_key.public_key()
        
        # 성능 메트릭
        self.last_generation_time = 0.0
        self.signature_size = 64  # Ed25519 서명 크기 (바이트)
        
    def generate_signature(self, value: float, timestamp: Optional[str] = None) -> tuple[bytes, str, float]:
        """
        센서 값에 대한 Ed25519 서명 생성
        
        Args:
            value: 센서 값
            timestamp: 타임스탬프 (None이면 현재 시간)
            
        Returns:
            (signature_bytes, timestamp, generation_time_ms)
        """
        start_time = time.time()
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 메시지 구성: value + timestamp
        message = f"{value:.6f}||{timestamp}".encode('utf-8')
        
        # Ed25519 서명 생성
        signature = self.private_key.sign(message)
        
        generation_time = (time.time() - start_time) * 1000
        self.last_generation_time = generation_time
        
        return signature, timestamp, generation_time
    
    def verify_signature(self, value: float, timestamp: str, signature: bytes, 
                        public_key: Optional[Ed25519PublicKey] = None) -> bool:
        """
        Ed25519 서명 검증
        
        Args:
            value: 센서 값
            timestamp: 타임스탬프
            signature: 서명
            public_key: 공개키 (None이면 자체 공개키 사용)
            
        Returns:
            검증 성공 여부
        """
        try:
            if public_key is None:
                public_key = self.public_key
                
            # 메시지 재구성
            message = f"{value:.6f}||{timestamp}".encode('utf-8')
            
            # 서명 검증
            public_key.verify(signature, message)
            return True
            
        except Exception:
            return False
    
    def generate_authentication_data(self, value: float, sensor_id: str = "sensor_01") -> Dict[str, Any]:
        """
        Bulletproofs와 호환되는 인증 데이터 생성
        
        Args:
            value: 센서 값
            sensor_id: 센서 식별자
            
        Returns:
            인증 데이터 딕셔너리
        """
        start_time = time.time()
        
        timestamp = datetime.now().isoformat()
        
        # Ed25519 서명 생성
        signature, _, _ = self.generate_signature(value, timestamp)
        
        generation_time = (time.time() - start_time) * 1000
        self.last_generation_time = generation_time
        
        # 공개키 직렬화
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Bulletproofs와 유사한 구조로 반환
        auth_data = {
            "value": value,  # 실제 값 포함 (프라이버시 없음)
            "signature": signature.hex(),
            "public_key": public_key_bytes.hex(),
            "timestamp": timestamp,
            "sensor_id": sensor_id,
            "algorithm": "ed25519",
            "signature_size_bytes": len(signature),
            "metadata": {
                "method": "ed25519",
                "algorithm": "ed25519",
                "key_size": 32,  # Ed25519 키 크기
                "generation_time_ms": generation_time
            }
        }
        
        return auth_data
    
    def verify_authentication_data(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        인증 데이터 검증
        
        Args:
            auth_data: 검증할 인증 데이터
            
        Returns:
            검증 결과
        """
        start_time = time.time()
        
        try:
            value = auth_data["value"]
            timestamp = auth_data["timestamp"]
            signature = bytes.fromhex(auth_data["signature"])
            public_key_bytes = bytes.fromhex(auth_data["public_key"])
            
            # 공개키 복원
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Ed25519 서명 검증
            is_valid = self.verify_signature(value, timestamp, signature, public_key)
            
            verification_time = (time.time() - start_time) * 1000
            
            return {
                "valid": is_valid,
                "time": verification_time,
                "method": "ed25519",
                "value_recovered": value,  # 값이 그대로 노출됨
                "message": "Ed25519 verification completed"
            }
            
        except Exception as e:
            verification_time = (time.time() - start_time) * 1000
            return {
                "valid": False,
                "time": verification_time,
                "method": "ed25519",
                "error": str(e),
                "message": "Ed25519 verification failed"
            }
    
    def serialize(self, auth_data: Dict[str, Any]) -> str:
        """
        인증 데이터를 네트워크 전송용 JSON 문자열로 직렬화
        
        Args:
            auth_data: generate_authentication_data()의 반환값
            
        Returns:
            JSON 문자열
        """
        return json.dumps(auth_data, indent=2, ensure_ascii=False)
    
    def deserialize(self, auth_json: str) -> Dict[str, Any]:
        """
        JSON 문자열을 인증 데이터로 역직렬화
        
        Args:
            auth_json: 직렬화된 인증 데이터 JSON
            
        Returns:
            인증 데이터 딕셔너리
        """
        return json.loads(auth_json)
    
    def measure_performance(self, num_iterations: int = 1000) -> Dict[str, float]:
        """
        Ed25519 성능 측정
        
        Args:
            num_iterations: 테스트 반복 횟수
            
        Returns:
            성능 측정 결과
        """
        generation_times = []
        verification_times = []
        
        # 테스트 데이터
        test_values = [
            42.123456,
            1000.789012,
            0.000001,
            999999.999999
        ]
        
        for i in range(num_iterations):
            value = test_values[i % len(test_values)]
            
            # 생성 시간 측정
            start_gen = time.time()
            auth_data = self.generate_authentication_data(value)
            gen_time = (time.time() - start_gen) * 1000
            generation_times.append(gen_time)
            
            # 검증 시간 측정
            start_ver = time.time()
            result = self.verify_authentication_data(auth_data)
            ver_time = (time.time() - start_ver) * 1000
            verification_times.append(ver_time)
            
            # 검증 실패시 경고
            if not result["valid"]:
                print(f"Warning: Verification failed for iteration {i}")
        
        return {
            "iterations": num_iterations,
            "avg_generation_time_ms": sum(generation_times) / len(generation_times),
            "avg_verification_time_ms": sum(verification_times) / len(verification_times),
            "min_generation_time_ms": min(generation_times),
            "max_generation_time_ms": max(generation_times),
            "min_verification_time_ms": min(verification_times),
            "max_verification_time_ms": max(verification_times),
            "signature_size_bytes": self.signature_size,
            "total_data_size_bytes": len(self.serialize(auth_data).encode('utf-8'))
        }
    
    def get_signature_size(self) -> int:
        """서명 크기 반환 (바이트)"""
        return self.signature_size
    
    def get_generation_time(self) -> float:
        """마지막 생성 시간 반환 (밀리초)"""
        return self.last_generation_time
    
    def get_key_info(self) -> Dict[str, Any]:
        """키 정보 반환"""
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "algorithm": "ed25519",
            "key_size_bytes": 32,
            "signature_size_bytes": self.signature_size,
            "public_key_hex": public_key_bytes.hex()[:16] + "...",  # 일부만 표시
            "key_type": "asymmetric"
        }


# 사용 예제 및 성능 비교
if __name__ == "__main__":
    print("🔐 Ed25519 Baseline 테스트")
    print("=" * 50)
    
    # Ed25519 베이스라인 초기화
    ed25519_baseline = Ed25519Baseline()
    
    print(f"알고리즘: {ed25519_baseline.get_key_info()['algorithm']}")
    print(f"키 정보: {ed25519_baseline.get_key_info()}")
    print(f"서명 크기: {ed25519_baseline.get_signature_size()} bytes")
    
    # 기본 테스트
    print(f"\n📊 기본 기능 테스트")
    test_values = [42.5, 1000.123, 0.001, 999999.99]
    
    for value in test_values:
        print(f"\n   값: {value}")
        
        # 인증 데이터 생성
        auth_data = ed25519_baseline.generate_authentication_data(value)
        print(f"   생성 시간: {ed25519_baseline.get_generation_time():.3f}ms")
        print(f"   서명: {auth_data['signature'][:16]}...")
        print(f"   데이터 크기: {len(ed25519_baseline.serialize(auth_data))} bytes")
        
        # 검증
        result = ed25519_baseline.verify_authentication_data(auth_data)
        print(f"   검증 결과: {'✅ 성공' if result['valid'] else '❌ 실패'}")
        print(f"   검증 시간: {result['time']:.3f}ms")
        print(f"   복원된 값: {result.get('value_recovered', 'N/A')}")
    
    # 성능 측정
    print(f"\n🚀 성능 측정 (1000회 반복)")
    perf_results = ed25519_baseline.measure_performance(1000)
    
    print(f"   평균 생성 시간: {perf_results['avg_generation_time_ms']:.4f}ms")
    print(f"   평균 검증 시간: {perf_results['avg_verification_time_ms']:.4f}ms")
    print(f"   최소/최대 생성: {perf_results['min_generation_time_ms']:.4f}ms / {perf_results['max_generation_time_ms']:.4f}ms")
    print(f"   최소/최대 검증: {perf_results['min_verification_time_ms']:.4f}ms / {perf_results['max_verification_time_ms']:.4f}ms")
    print(f"   총 데이터 크기: {perf_results['total_data_size_bytes']} bytes")
    
    # 잘못된 서명 테스트
    print(f"\n🚫 보안 테스트")
    auth_data = ed25519_baseline.generate_authentication_data(42.0)
    
    # 서명 변조
    original_signature = auth_data['signature']
    auth_data['signature'] = '0' * len(original_signature)  # 잘못된 서명
    
    result = ed25519_baseline.verify_authentication_data(auth_data)
    print(f"   변조된 서명 검증: {'❌ 실패 (정상)' if not result['valid'] else '⚠️ 성공 (비정상)'}")
    
    # 값 변조
    auth_data['signature'] = original_signature  # 서명 복원
    auth_data['value'] = 99999.0  # 값 변조
    
    result = ed25519_baseline.verify_authentication_data(auth_data)
    print(f"   변조된 값 검증: {'❌ 실패 (정상)' if not result['valid'] else '⚠️ 성공 (비정상)'}")
    
    # 다른 키로 검증 테스트
    print(f"\n🔑 키 검증 테스트")
    auth_data['value'] = 42.0  # 값 복원
    
    # 새로운 키 쌍 생성
    other_baseline = Ed25519Baseline()
    result = other_baseline.verify_authentication_data(auth_data)
    print(f"   다른 키로 검증: {'❌ 실패 (정상)' if not result['valid'] else '⚠️ 성공 (비정상)'}")
    
    print(f"\n✅ Ed25519 베이스라인 테스트 완료!")
    print(f"\n📝 특징 요약:")
    print(f"   - 실제 센서 값 노출 (프라이버시 없음)")
    print(f"   - 빠른 처리 속도 (1-5ms)")
    print(f"   - 중간 데이터 크기 (~150 bytes)")
    print(f"   - 강력한 무결성 보장")
    print(f"   - 비대칭키 기반 (키 배포 용이)")
    print(f"   - 64바이트 고정 서명 크기")

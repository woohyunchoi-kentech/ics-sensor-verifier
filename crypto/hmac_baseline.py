"""
HMAC Baseline Implementation
베이스라인 비교를 위한 HMAC 기반 무결성 검증
"""

import hmac
import hashlib
import secrets
import time
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime


class HMACBaseline:
    """
    HMAC 기반 베이스라인 구현
    Bulletproofs와 성능 비교를 위한 전통적인 HMAC 방식
    """
    
    def __init__(self, secret_key: Optional[bytes] = None, algorithm: str = 'sha256'):
        """
        HMAC 베이스라인 초기화
        
        Args:
            secret_key: 32바이트 비밀키 (None이면 자동 생성)
            algorithm: HMAC 알고리즘 (기본: sha256)
        """
        self.algorithm = algorithm
        self.secret_key = secret_key or secrets.token_bytes(32)
        
        # 해시 함수 설정
        if algorithm == 'sha256':
            self.hash_func = hashlib.sha256
        elif algorithm == 'sha512':
            self.hash_func = hashlib.sha512
        elif algorithm == 'md5':
            self.hash_func = hashlib.md5
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # 성능 메트릭
        self.last_generation_time = 0.0
        self.mac_size = self.hash_func().digest_size
        
    def generate_mac(self, value: float, timestamp: Optional[str] = None) -> Tuple[bytes, str, float]:
        """
        센서 값에 대한 HMAC 생성
        
        Args:
            value: 센서 값
            timestamp: 타임스탬프 (None이면 현재 시간)
            
        Returns:
            (mac_bytes, timestamp, generation_time_ms)
        """
        start_time = time.time()
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 메시지 구성: value + timestamp
        message = f"{value:.6f}||{timestamp}".encode('utf-8')
        
        # HMAC 생성
        mac = hmac.new(
            self.secret_key,
            message,
            self.hash_func
        ).digest()
        
        generation_time = (time.time() - start_time) * 1000
        self.last_generation_time = generation_time
        
        return mac, timestamp, generation_time
    
    def verify_mac(self, value: float, timestamp: str, received_mac: bytes) -> bool:
        """
        HMAC 검증
        
        Args:
            value: 센서 값
            timestamp: 타임스탬프
            received_mac: 수신된 MAC
            
        Returns:
            검증 성공 여부
        """
        try:
            # 예상 MAC 계산
            message = f"{value:.6f}||{timestamp}".encode('utf-8')
            expected_mac = hmac.new(
                self.secret_key,
                message,
                self.hash_func
            ).digest()
            
            # 안전한 비교
            return hmac.compare_digest(expected_mac, received_mac)
            
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
        
        # HMAC 생성
        mac, _, _ = self.generate_mac(value, timestamp)
        
        generation_time = (time.time() - start_time) * 1000
        self.last_generation_time = generation_time
        
        # Bulletproofs와 유사한 구조로 반환
        auth_data = {
            "value": value,  # 실제 값 포함 (프라이버시 없음)
            "mac": mac.hex(),
            "timestamp": timestamp,
            "sensor_id": sensor_id,
            "algorithm": self.algorithm,
            "mac_size_bytes": len(mac),
            "metadata": {
                "method": "hmac",
                "algorithm": self.algorithm,
                "key_size": len(self.secret_key),
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
            received_mac = bytes.fromhex(auth_data["mac"])
            
            # HMAC 검증
            is_valid = self.verify_mac(value, timestamp, received_mac)
            
            verification_time = (time.time() - start_time) * 1000
            
            return {
                "valid": is_valid,
                "time": verification_time,
                "method": "hmac",
                "value_recovered": value,  # 값이 그대로 노출됨
                "message": "HMAC verification completed"
            }
            
        except Exception as e:
            verification_time = (time.time() - start_time) * 1000
            return {
                "valid": False,
                "time": verification_time,
                "method": "hmac",
                "error": str(e),
                "message": "HMAC verification failed"
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
        HMAC 성능 측정
        
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
            "mac_size_bytes": self.mac_size,
            "total_data_size_bytes": len(self.serialize(auth_data).encode('utf-8'))
        }
    
    def get_mac_size(self) -> int:
        """MAC 크기 반환 (바이트)"""
        return self.mac_size
    
    def get_generation_time(self) -> float:
        """마지막 생성 시간 반환 (밀리초)"""
        return self.last_generation_time
    
    def get_key_info(self) -> Dict[str, Any]:
        """키 정보 반환"""
        return {
            "algorithm": self.algorithm,
            "key_size_bytes": len(self.secret_key),
            "mac_size_bytes": self.mac_size,
            "key_hex": self.secret_key.hex()[:16] + "..."  # 일부만 표시
        }


# 사용 예제 및 성능 비교
if __name__ == "__main__":
    print("🔐 HMAC Baseline 테스트")
    print("=" * 50)
    
    # HMAC 베이스라인 초기화
    hmac_baseline = HMACBaseline()
    
    print(f"알고리즘: {hmac_baseline.algorithm}")
    print(f"키 정보: {hmac_baseline.get_key_info()}")
    print(f"MAC 크기: {hmac_baseline.get_mac_size()} bytes")
    
    # 기본 테스트
    print(f"\n📊 기본 기능 테스트")
    test_values = [42.5, 1000.123, 0.001, 999999.99]
    
    for value in test_values:
        print(f"\n   값: {value}")
        
        # 인증 데이터 생성
        auth_data = hmac_baseline.generate_authentication_data(value)
        print(f"   생성 시간: {hmac_baseline.get_generation_time():.3f}ms")
        print(f"   MAC: {auth_data['mac'][:16]}...")
        print(f"   데이터 크기: {len(hmac_baseline.serialize(auth_data))} bytes")
        
        # 검증
        result = hmac_baseline.verify_authentication_data(auth_data)
        print(f"   검증 결과: {'✅ 성공' if result['valid'] else '❌ 실패'}")
        print(f"   검증 시간: {result['time']:.3f}ms")
        print(f"   복원된 값: {result.get('value_recovered', 'N/A')}")
    
    # 성능 측정
    print(f"\n🚀 성능 측정 (1000회 반복)")
    perf_results = hmac_baseline.measure_performance(1000)
    
    print(f"   평균 생성 시간: {perf_results['avg_generation_time_ms']:.4f}ms")
    print(f"   평균 검증 시간: {perf_results['avg_verification_time_ms']:.4f}ms")
    print(f"   최소/최대 생성: {perf_results['min_generation_time_ms']:.4f}ms / {perf_results['max_generation_time_ms']:.4f}ms")
    print(f"   최소/최대 검증: {perf_results['min_verification_time_ms']:.4f}ms / {perf_results['max_verification_time_ms']:.4f}ms")
    print(f"   총 데이터 크기: {perf_results['total_data_size_bytes']} bytes")
    
    # 잘못된 MAC 테스트
    print(f"\n🚫 보안 테스트")
    auth_data = hmac_baseline.generate_authentication_data(42.0)
    
    # MAC 변조
    original_mac = auth_data['mac']
    auth_data['mac'] = '0' * len(original_mac)  # 잘못된 MAC
    
    result = hmac_baseline.verify_authentication_data(auth_data)
    print(f"   변조된 MAC 검증: {'❌ 실패 (정상)' if not result['valid'] else '⚠️ 성공 (비정상)'}")
    
    # 값 변조
    auth_data['mac'] = original_mac  # MAC 복원
    auth_data['value'] = 99999.0  # 값 변조
    
    result = hmac_baseline.verify_authentication_data(auth_data)
    print(f"   변조된 값 검증: {'❌ 실패 (정상)' if not result['valid'] else '⚠️ 성공 (비정상)'}")
    
    # 다른 알고리즘 비교
    print(f"\n⚡ 알고리즘 비교")
    algorithms = ['sha256', 'sha512', 'md5']
    
    for algo in algorithms:
        try:
            baseline = HMACBaseline(algorithm=algo)
            perf = baseline.measure_performance(100)
            
            print(f"   {algo.upper()}:")
            print(f"     생성: {perf['avg_generation_time_ms']:.4f}ms")
            print(f"     검증: {perf['avg_verification_time_ms']:.4f}ms")
            print(f"     MAC 크기: {baseline.get_mac_size()} bytes")
            
        except Exception as e:
            print(f"   {algo.upper()}: ❌ {e}")
    
    print(f"\n✅ HMAC 베이스라인 테스트 완료!")
    print(f"\n📝 특징 요약:")
    print(f"   - 실제 센서 값 노출 (프라이버시 없음)")
    print(f"   - 매우 빠른 처리 속도 (< 1ms)")
    print(f"   - 작은 데이터 크기 (~100 bytes)")
    print(f"   - 강력한 무결성 보장")
    print(f"   - 대칭키 기반 (키 공유 필요)")

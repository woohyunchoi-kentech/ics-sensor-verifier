#!/usr/bin/env python3
"""
HMAC Authentication System
=========================

SHA-256 기반 HMAC 인증 시스템 구현
ICS 센서 데이터 무결성 검증 및 인증을 위한 모듈

Author: Claude Code  
Date: 2025-08-28
"""

import hmac
import hashlib
import json
import time
import secrets
import logging
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class HMACResult:
    """HMAC 연산 결과를 담는 데이터클래스"""
    success: bool
    hmac_value: str
    generation_time_ms: float
    verification_time_ms: float = 0.0
    data_size_bytes: int = 0
    timestamp: datetime = None
    error_message: str = ""

class HMACAuthenticator:
    """SHA-256 기반 HMAC 인증 시스템"""
    
    def __init__(self, key: bytes = None, algorithm: str = 'sha256'):
        """
        HMAC 인증기 초기화
        
        Args:
            key: HMAC 키 (None이면 자동 생성)
            algorithm: 해시 알고리즘 ('sha256', 'sha512' 등)
        """
        self.algorithm = algorithm
        
        # 키 설정 또는 생성
        if key is None:
            # 실험을 위한 고정 키 사용 (실제 운영에서는 보안 위험)
            self.key = b'wadi_hmac_experiment_key_2025' + b'\x00' * 4  # 32바이트로 맞춤
        else:
            self.key = key
            
        # 해시 함수 매핑
        self.hash_functions = {
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
            'sha1': hashlib.sha1,
            'md5': hashlib.md5
        }
        
        if algorithm not in self.hash_functions:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
            
        self.hash_func = self.hash_functions[algorithm]
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 성능 통계
        self.stats = {
            'total_generations': 0,
            'total_verifications': 0,
            'successful_verifications': 0,
            'failed_verifications': 0,
            'total_generation_time': 0.0,
            'total_verification_time': 0.0
        }
    
    def _generate_secure_key(self) -> bytes:
        """
        암호학적으로 안전한 키 생성
        
        Returns:
            32바이트 랜덤 키
        """
        return secrets.token_bytes(32)  # 256-bit key
    
    def generate_hmac(self, data: Any, timestamp: bool = True) -> HMACResult:
        """
        데이터에 대한 HMAC 생성
        
        Args:
            data: HMAC를 생성할 데이터 (딕셔너리, 문자열, 바이트 등)
            timestamp: 타임스탬프 포함 여부
            
        Returns:
            HMAC 생성 결과
        """
        start_time = time.perf_counter()
        
        try:
            # 데이터를 바이트로 변환
            data_bytes = self._serialize_data(data, timestamp)
            data_size = len(data_bytes)
            
            # HMAC 생성
            mac = hmac.new(
                self.key,
                data_bytes,
                digestmod=self.hash_func
            )
            hmac_value = mac.hexdigest()
            
            end_time = time.perf_counter()
            generation_time = (end_time - start_time) * 1000  # ms 단위
            
            # 통계 업데이트
            self.stats['total_generations'] += 1
            self.stats['total_generation_time'] += generation_time
            
            result = HMACResult(
                success=True,
                hmac_value=hmac_value,
                generation_time_ms=generation_time,
                data_size_bytes=data_size,
                timestamp=datetime.now()
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            generation_time = (end_time - start_time) * 1000
            
            self.logger.error(f"HMAC generation failed: {str(e)}")
            
            return HMACResult(
                success=False,
                hmac_value="",
                generation_time_ms=generation_time,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    def verify_hmac(self, data: Any, received_hmac: str, timestamp: bool = True) -> HMACResult:
        """
        HMAC 검증
        
        Args:
            data: 원본 데이터
            received_hmac: 받은 HMAC 값
            timestamp: 타임스탬프 포함 여부
            
        Returns:
            HMAC 검증 결과
        """
        start_time = time.perf_counter()
        
        try:
            # 데이터를 바이트로 변환
            data_bytes = self._serialize_data(data, timestamp)
            data_size = len(data_bytes)
            
            # 예상 HMAC 계산
            expected_mac = hmac.new(
                self.key,
                data_bytes,
                digestmod=self.hash_func
            )
            expected_hmac = expected_mac.hexdigest()
            
            # 시간 상수 비교 (타이밍 공격 방지)
            is_valid = hmac.compare_digest(expected_hmac, received_hmac)
            
            end_time = time.perf_counter()
            verification_time = (end_time - start_time) * 1000  # ms 단위
            
            # 통계 업데이트
            self.stats['total_verifications'] += 1
            self.stats['total_verification_time'] += verification_time
            
            if is_valid:
                self.stats['successful_verifications'] += 1
            else:
                self.stats['failed_verifications'] += 1
            
            result = HMACResult(
                success=is_valid,
                hmac_value=expected_hmac,
                generation_time_ms=0.0,  # Not applicable for verification
                verification_time_ms=verification_time,
                data_size_bytes=data_size,
                timestamp=datetime.now()
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            verification_time = (end_time - start_time) * 1000
            
            self.stats['failed_verifications'] += 1
            self.logger.error(f"HMAC verification failed: {str(e)}")
            
            return HMACResult(
                success=False,
                hmac_value="",
                generation_time_ms=0.0,  # Not applicable for verification
                verification_time_ms=verification_time,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    def _serialize_data(self, data: Any, include_timestamp: bool = True) -> bytes:
        """
        데이터를 시리얼라이즈하여 바이트로 변환
        
        Args:
            data: 시리얼라이즈할 데이터
            include_timestamp: 타임스탬프 포함 여부
            
        Returns:
            시리얼라이즈된 바이트 데이터
        """
        if isinstance(data, bytes):
            serialized_data = data
        elif isinstance(data, str):
            serialized_data = data.encode('utf-8')
        elif isinstance(data, (dict, list)):
            # 딕셔너리나 리스트는 JSON으로 시리얼라이즈
            if include_timestamp and isinstance(data, dict):
                data_copy = data.copy()
                data_copy['_timestamp'] = time.time()
                serialized_data = json.dumps(data_copy, sort_keys=True, separators=(',', ':')).encode('utf-8')
            else:
                serialized_data = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        else:
            # 기타 타입은 문자열로 변환 후 인코딩
            serialized_data = str(data).encode('utf-8')
        
        return serialized_data
    
    def create_authenticated_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        인증된 메시지 생성 (데이터 + HMAC)
        
        Args:
            data: 인증할 데이터
            
        Returns:
            HMAC가 포함된 인증 메시지
        """
        # 타임스탬프를 포함한 데이터로 HMAC 생성 (일관성 보장)
        hmac_result = self.generate_hmac(data, timestamp=False)  # 타임스탬프 자동 추가 비활성화
        
        if hmac_result.success:
            authenticated_msg = {
                'data': data,
                'hmac': hmac_result.hmac_value,
                'algorithm': self.algorithm,
                'timestamp': hmac_result.timestamp.isoformat(),
                'data_size': hmac_result.data_size_bytes
            }
            return authenticated_msg
        else:
            raise ValueError(f"Failed to generate HMAC: {hmac_result.error_message}")
    
    def verify_authenticated_message(self, message: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        인증된 메시지 검증
        
        Args:
            message: 검증할 인증 메시지
            
        Returns:
            (검증 성공 여부, 원본 데이터)
        """
        try:
            data = message['data']
            received_hmac = message['hmac']
            
            # 동일한 방식으로 HMAC 검증 (타임스탬프 비활성화)
            hmac_result = self.verify_hmac(data, received_hmac, timestamp=False)
            
            return hmac_result.success, data
            
        except KeyError as e:
            self.logger.error(f"Invalid message format: missing {str(e)}")
            return False, {}
        except Exception as e:
            self.logger.error(f"Message verification failed: {str(e)}")
            return False, {}
    
    def process_sensor_data_batch(self, sensor_data_list: List[Dict[str, Any]]) -> List[HMACResult]:
        """
        센서 데이터 배치 처리 (여러 센서 데이터에 대한 HMAC 일괄 생성)
        
        Args:
            sensor_data_list: 센서 데이터 리스트
            
        Returns:
            HMAC 결과 리스트
        """
        results = []
        
        for i, sensor_data in enumerate(sensor_data_list):
            # 배치 처리를 위한 메타데이터 추가
            batch_data = {
                'batch_index': i,
                'batch_size': len(sensor_data_list),
                'sensor_data': sensor_data,
                'batch_timestamp': time.time()
            }
            
            result = self.generate_hmac(batch_data)
            results.append(result)
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        성능 통계 반환
        
        Returns:
            성능 통계 딕셔너리
        """
        total_operations = self.stats['total_generations'] + self.stats['total_verifications']
        
        stats = {
            'total_operations': total_operations,
            'hmac_generations': self.stats['total_generations'],
            'hmac_verifications': self.stats['total_verifications'],
            'successful_verifications': self.stats['successful_verifications'],
            'failed_verifications': self.stats['failed_verifications'],
            'success_rate': (self.stats['successful_verifications'] / max(1, self.stats['total_verifications'])) * 100,
            'avg_generation_time_ms': self.stats['total_generation_time'] / max(1, self.stats['total_generations']),
            'avg_verification_time_ms': self.stats['total_verification_time'] / max(1, self.stats['total_verifications']),
            'algorithm': self.algorithm,
            'key_size_bits': len(self.key) * 8
        }
        
        return stats
    
    def reset_stats(self):
        """성능 통계 초기화"""
        self.stats = {
            'total_generations': 0,
            'total_verifications': 0,
            'successful_verifications': 0,
            'failed_verifications': 0,
            'total_generation_time': 0.0,
            'total_verification_time': 0.0
        }
    
    def get_key_info(self) -> Dict[str, Any]:
        """
        키 정보 반환
        
        Returns:
            키 정보 딕셔너리
        """
        return {
            'algorithm': self.algorithm,
            'key_size_bytes': len(self.key),
            'key_size_bits': len(self.key) * 8,
            'key_hex': self.key.hex()[:16] + "...",  # 보안을 위해 일부만 표시
            'hash_function': self.hash_func.__name__
        }
    
    def export_key(self, filepath: str):
        """
        키를 파일로 내보내기 (보안 주의)
        
        Args:
            filepath: 저장할 파일 경로
        """
        key_data = {
            'algorithm': self.algorithm,
            'key_hex': self.key.hex(),
            'created_timestamp': datetime.now().isoformat(),
            'key_size_bits': len(self.key) * 8
        }
        
        with open(filepath, 'w') as f:
            json.dump(key_data, f, indent=2)
        
        self.logger.warning(f"Key exported to {filepath} - Handle with care!")
    
    @classmethod
    def from_key_file(cls, filepath: str) -> 'HMACAuthenticator':
        """
        키 파일로부터 HMAC 인증기 생성
        
        Args:
            filepath: 키 파일 경로
            
        Returns:
            HMACAuthenticator 인스턴스
        """
        with open(filepath, 'r') as f:
            key_data = json.load(f)
        
        key_bytes = bytes.fromhex(key_data['key_hex'])
        algorithm = key_data.get('algorithm', 'sha256')
        
        return cls(key=key_bytes, algorithm=algorithm)

# 고성능 배치 처리를 위한 클래스
class HMACBatchProcessor:
    """HMAC 배치 처리 최적화 클래스"""
    
    def __init__(self, authenticator: HMACAuthenticator):
        self.authenticator = authenticator
        self.batch_results = []
    
    def process_concurrent_batch(self, data_batches: List[List[Dict]], max_workers: int = 4) -> List[List[HMACResult]]:
        """
        동시 처리를 통한 배치 HMAC 연산
        
        Args:
            data_batches: 데이터 배치 리스트
            max_workers: 최대 워커 수
            
        Returns:
            배치별 HMAC 결과 리스트
        """
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 각 배치를 별도 스레드에서 처리
            future_to_batch = {
                executor.submit(self.authenticator.process_sensor_data_batch, batch): i 
                for i, batch in enumerate(data_batches)
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    results.append((batch_idx, batch_results))
                except Exception as e:
                    self.authenticator.logger.error(f"Batch {batch_idx} failed: {str(e)}")
                    results.append((batch_idx, []))
        
        # 순서대로 정렬
        results.sort(key=lambda x: x[0])
        return [result[1] for result in results]

if __name__ == "__main__":
    # 테스트 코드
    print("🔐 HMAC Authenticator Test")
    
    # HMAC 인증기 생성
    authenticator = HMACAuthenticator()
    
    # 테스트 데이터
    test_data = {
        'sensor_id': 'WADI_AIT_001',
        'value': 7.15,
        'unit': 'pH',
        'location': 'Tank_A'
    }
    
    print(f"Key info: {authenticator.get_key_info()}")
    
    # HMAC 생성 테스트
    result = authenticator.generate_hmac(test_data)
    print(f"HMAC Generation - Success: {result.success}, Time: {result.generation_time_ms:.3f}ms")
    print(f"HMAC: {result.hmac_value[:32]}...")
    
    # HMAC 검증 테스트
    verify_result = authenticator.verify_hmac(test_data, result.hmac_value)
    print(f"HMAC Verification - Success: {verify_result.success}, Time: {verify_result.verification_time_ms:.3f}ms")
    
    # 인증 메시지 생성/검증 테스트
    auth_msg = authenticator.create_authenticated_message(test_data)
    is_valid, original_data = authenticator.verify_authenticated_message(auth_msg)
    print(f"Authenticated Message - Valid: {is_valid}")
    
    # 성능 통계
    stats = authenticator.get_performance_stats()
    print(f"Performance Stats: {stats}")
    
    # 배치 처리 테스트
    batch_data = [{'sensor': f'S{i}', 'value': i * 1.5} for i in range(5)]
    batch_results = authenticator.process_sensor_data_batch(batch_data)
    print(f"Batch Processing: {len(batch_results)} results, avg time: {sum(r.generation_time_ms for r in batch_results)/len(batch_results):.3f}ms")
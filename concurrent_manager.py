#!/usr/bin/env python3
"""
동시 CKKS 요청 관리 시스템
다중 센서 동시 암호화/전송 처리, 연결 풀링, 비동기 처리
"""

import asyncio
import aiohttp
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import queue
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
import json

# 기존 CKKS 구현 임포트
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from crypto.ckks_baseline import CKKSBaseline

logger = logging.getLogger(__name__)

@dataclass
class CKKSRequest:
    """CKKS 요청 데이터 구조"""
    sensor_id: str
    value: float
    timestamp: float
    request_id: str

@dataclass
class CKKSResponse:
    """CKKS 응답 데이터 구조"""
    request_id: str
    sensor_id: str
    success: bool
    original_value: float
    decrypted_value: Optional[float]
    encryption_time_ms: float
    response_time_ms: float
    server_processing_time_ms: Optional[float]
    error_message: Optional[str]
    accuracy_error: Optional[float]

class ConcurrentCKKSManager:
    """동시 CKKS 요청 처리 관리자"""
    
    def __init__(self, 
                 server_url: str = "http://192.168.0.11:8085",
                 max_concurrent: int = 50,
                 timeout: float = 10.0):
        """
        초기화
        
        Args:
            server_url: CKKS 서버 URL
            max_concurrent: 최대 동시 요청 수
            timeout: 요청 타임아웃 (초)
        """
        self.server_url = server_url
        self.verify_url = f"{server_url}/api/v1/ckks/verify"
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        
        # CKKS 클라이언트 (스레드별로 독립적으로 생성)
        self.ckks_clients = {}
        self.client_lock = threading.Lock()
        
        # 세션 관리
        self.session = None
        self.session_lock = asyncio.Lock() if asyncio.iscoroutinefunction(self._get_session) else threading.Lock()
        
        # 통계
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_encryption_time': 0.0,
            'total_response_time': 0.0,
        }
        self.stats_lock = threading.Lock()
        
        logger.info(f"동시 CKKS 관리자 초기화: 최대 {max_concurrent}개 동시 요청")
    
    def _get_ckks_client(self) -> CKKSBaseline:
        """현재 스레드용 CKKS 클라이언트 반환"""
        thread_id = threading.get_ident()
        
        with self.client_lock:
            if thread_id not in self.ckks_clients:
                # 새 CKKS 클라이언트 생성
                ckks = CKKSBaseline()
                if not ckks.load_server_public_key_from_api(self.server_url):
                    raise RuntimeError("CKKS 서버 공개키 로드 실패")
                
                self.ckks_clients[thread_id] = ckks
                logger.debug(f"스레드 {thread_id}용 CKKS 클라이언트 생성")
            
            return self.ckks_clients[thread_id]
    
    @asynccontextmanager
    async def _get_session(self):
        """비동기 HTTP 세션 관리"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent * 2,
                limit_per_host=self.max_concurrent,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            logger.info("HTTP 세션 생성됨")
        
        try:
            yield self.session
        finally:
            pass  # 세션은 명시적으로 닫을 때까지 유지
    
    async def close_session(self):
        """HTTP 세션 종료"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("HTTP 세션 종료됨")
    
    def encrypt_single_value(self, sensor_id: str, value: float) -> Tuple[Dict, float]:
        """
        단일 값 암호화
        
        Returns:
            (암호화된 데이터, 암호화 시간)
        """
        start_time = time.time()
        
        try:
            ckks = self._get_ckks_client()
            proof_data = ckks.generate_proof(value)
            
            encryption_time = (time.time() - start_time) * 1000  # ms
            
            return proof_data, encryption_time
            
        except Exception as e:
            logger.error(f"암호화 실패 [{sensor_id}]: {e}")
            raise
    
    async def send_single_request_async(self, request: CKKSRequest) -> CKKSResponse:
        """비동기 단일 요청 전송"""
        start_time = time.time()
        
        try:
            # 암호화 (동기 처리)
            loop = asyncio.get_event_loop()
            proof_data, encryption_time = await loop.run_in_executor(
                None, self.encrypt_single_value, request.sensor_id, request.value
            )
            
            # 서버 요청 데이터 구성
            request_data = {
                "sensor_id": request.sensor_id,
                "timestamp": proof_data['timestamp'],
                "encrypted_data": proof_data['encrypted_data'],
                "context": proof_data.get('context_id', 'lightweight'),
                "algorithm": "CKKS"
            }
            
            # HTTP 요청 전송
            async with self._get_session() as session:
                async with session.post(self.verify_url, json=request_data) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            decrypted_value = result.get('decrypted_value')
                            server_time = result.get('processing_time_ms')
                            
                            # 정확도 계산
                            accuracy_error = None
                            if decrypted_value is not None:
                                accuracy_error = abs(decrypted_value - request.value)
                                if request.value != 0:
                                    accuracy_error = (accuracy_error / abs(request.value)) * 100
                            
                            return CKKSResponse(
                                request_id=request.request_id,
                                sensor_id=request.sensor_id,
                                success=True,
                                original_value=request.value,
                                decrypted_value=decrypted_value,
                                encryption_time_ms=encryption_time,
                                response_time_ms=response_time,
                                server_processing_time_ms=server_time,
                                error_message=None,
                                accuracy_error=accuracy_error
                            )
                        else:
                            error_msg = result.get('error_message', 'Unknown server error')
                            return CKKSResponse(
                                request_id=request.request_id,
                                sensor_id=request.sensor_id,
                                success=False,
                                original_value=request.value,
                                decrypted_value=None,
                                encryption_time_ms=encryption_time,
                                response_time_ms=response_time,
                                server_processing_time_ms=None,
                                error_message=error_msg,
                                accuracy_error=None
                            )
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        return CKKSResponse(
                            request_id=request.request_id,
                            sensor_id=request.sensor_id,
                            success=False,
                            original_value=request.value,
                            decrypted_value=None,
                            encryption_time_ms=encryption_time,
                            response_time_ms=response_time,
                            server_processing_time_ms=None,
                            error_message=error_msg,
                            accuracy_error=None
                        )
        
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return CKKSResponse(
                request_id=request.request_id,
                sensor_id=request.sensor_id,
                success=False,
                original_value=request.value,
                decrypted_value=None,
                encryption_time_ms=0,
                response_time_ms=response_time,
                server_processing_time_ms=None,
                error_message="Request timeout",
                accuracy_error=None
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return CKKSResponse(
                request_id=request.request_id,
                sensor_id=request.sensor_id,
                success=False,
                original_value=request.value,
                decrypted_value=None,
                encryption_time_ms=0,
                response_time_ms=response_time,
                server_processing_time_ms=None,
                error_message=str(e),
                accuracy_error=None
            )
    
    async def send_batch_requests_async(self, requests: List[CKKSRequest]) -> List[CKKSResponse]:
        """비동기 배치 요청 처리"""
        if not requests:
            return []
        
        logger.info(f"비동기 배치 요청 시작: {len(requests)}개")
        
        # 동시 실행 제한
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def limited_request(request):
            async with semaphore:
                return await self.send_single_request_async(request)
        
        # 모든 요청 동시 실행
        tasks = [limited_request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        final_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"요청 {requests[i].request_id} 예외: {response}")
                final_responses.append(CKKSResponse(
                    request_id=requests[i].request_id,
                    sensor_id=requests[i].sensor_id,
                    success=False,
                    original_value=requests[i].value,
                    decrypted_value=None,
                    encryption_time_ms=0,
                    response_time_ms=0,
                    server_processing_time_ms=None,
                    error_message=str(response),
                    accuracy_error=None
                ))
            else:
                final_responses.append(response)
        
        # 통계 업데이트
        self._update_stats(final_responses)
        
        logger.info(f"비동기 배치 완료: {sum(1 for r in final_responses if r.success)}/{len(final_responses)} 성공")
        return final_responses
    
    def send_batch_requests_sync(self, requests: List[CKKSRequest]) -> List[CKKSResponse]:
        """동기식 배치 요청 처리 (ThreadPoolExecutor 사용)"""
        if not requests:
            return []
        
        logger.info(f"동기 배치 요청 시작: {len(requests)}개")
        
        responses = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # 모든 요청을 스레드풀에 제출
            future_to_request = {}
            
            for request in requests:
                future = executor.submit(self._send_single_request_sync, request)
                future_to_request[future] = request
            
            # 결과 수집
            for future in as_completed(future_to_request):
                request = future_to_request[future]
                try:
                    response = future.result()
                    responses.append(response)
                except Exception as e:
                    logger.error(f"요청 {request.request_id} 실패: {e}")
                    responses.append(CKKSResponse(
                        request_id=request.request_id,
                        sensor_id=request.sensor_id,
                        success=False,
                        original_value=request.value,
                        decrypted_value=None,
                        encryption_time_ms=0,
                        response_time_ms=0,
                        server_processing_time_ms=None,
                        error_message=str(e),
                        accuracy_error=None
                    ))
        
        # 통계 업데이트
        self._update_stats(responses)
        
        logger.info(f"동기 배치 완료: {sum(1 for r in responses if r.success)}/{len(responses)} 성공")
        return responses
    
    def _send_single_request_sync(self, request: CKKSRequest) -> CKKSResponse:
        """동기식 단일 요청 (ThreadPoolExecutor용)"""
        import requests
        
        start_time = time.time()
        
        try:
            # 암호화
            proof_data, encryption_time = self.encrypt_single_value(
                request.sensor_id, request.value
            )
            
            # 요청 데이터 구성
            request_data = {
                "sensor_id": request.sensor_id,
                "timestamp": proof_data['timestamp'],
                "encrypted_data": proof_data['encrypted_data'],
                "context": proof_data.get('context_id', 'lightweight'),
                "algorithm": "CKKS"
            }
            
            # HTTP 요청
            response = requests.post(
                self.verify_url,
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    decrypted_value = result.get('decrypted_value')
                    server_time = result.get('processing_time_ms')
                    
                    # 정확도 계산
                    accuracy_error = None
                    if decrypted_value is not None:
                        accuracy_error = abs(decrypted_value - request.value)
                        if request.value != 0:
                            accuracy_error = (accuracy_error / abs(request.value)) * 100
                    
                    return CKKSResponse(
                        request_id=request.request_id,
                        sensor_id=request.sensor_id,
                        success=True,
                        original_value=request.value,
                        decrypted_value=decrypted_value,
                        encryption_time_ms=encryption_time,
                        response_time_ms=response_time,
                        server_processing_time_ms=server_time,
                        error_message=None,
                        accuracy_error=accuracy_error
                    )
                else:
                    return CKKSResponse(
                        request_id=request.request_id,
                        sensor_id=request.sensor_id,
                        success=False,
                        original_value=request.value,
                        decrypted_value=None,
                        encryption_time_ms=encryption_time,
                        response_time_ms=response_time,
                        server_processing_time_ms=None,
                        error_message=result.get('error_message', 'Server error'),
                        accuracy_error=None
                    )
            else:
                return CKKSResponse(
                    request_id=request.request_id,
                    sensor_id=request.sensor_id,
                    success=False,
                    original_value=request.value,
                    decrypted_value=None,
                    encryption_time_ms=encryption_time,
                    response_time_ms=response_time,
                    server_processing_time_ms=None,
                    error_message=f"HTTP {response.status_code}",
                    accuracy_error=None
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return CKKSResponse(
                request_id=request.request_id,
                sensor_id=request.sensor_id,
                success=False,
                original_value=request.value,
                decrypted_value=None,
                encryption_time_ms=0,
                response_time_ms=response_time,
                server_processing_time_ms=None,
                error_message=str(e),
                accuracy_error=None
            )
    
    def _update_stats(self, responses: List[CKKSResponse]):
        """통계 업데이트"""
        with self.stats_lock:
            self.stats['total_requests'] += len(responses)
            
            for response in responses:
                if response.success:
                    self.stats['successful_requests'] += 1
                    self.stats['total_encryption_time'] += response.encryption_time_ms
                    self.stats['total_response_time'] += response.response_time_ms
                else:
                    self.stats['failed_requests'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        with self.stats_lock:
            stats = self.stats.copy()
        
        if stats['successful_requests'] > 0:
            stats['avg_encryption_time'] = stats['total_encryption_time'] / stats['successful_requests']
            stats['avg_response_time'] = stats['total_response_time'] / stats['successful_requests']
            stats['success_rate'] = (stats['successful_requests'] / stats['total_requests']) * 100
        else:
            stats['avg_encryption_time'] = 0
            stats['avg_response_time'] = 0
            stats['success_rate'] = 0
        
        return stats
    
    def reset_stats(self):
        """통계 초기화"""
        with self.stats_lock:
            self.stats = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_encryption_time': 0.0,
                'total_response_time': 0.0,
            }
        logger.info("통계 초기화됨")

# 편의 함수들
def create_ckks_request(sensor_id: str, value: float, request_id: str = None) -> CKKSRequest:
    """CKKS 요청 생성 헬퍼 함수"""
    if request_id is None:
        request_id = f"{sensor_id}_{int(time.time() * 1000)}"
    
    return CKKSRequest(
        sensor_id=sensor_id,
        value=value,
        timestamp=time.time(),
        request_id=request_id
    )

async def run_async_batch_test(manager: ConcurrentCKKSManager, 
                              requests: List[CKKSRequest]) -> List[CKKSResponse]:
    """비동기 배치 테스트 실행"""
    try:
        return await manager.send_batch_requests_async(requests)
    finally:
        await manager.close_session()

if __name__ == "__main__":
    # 테스트 코드
    import random
    
    # 관리자 생성
    manager = ConcurrentCKKSManager(max_concurrent=10)
    
    # 테스트 요청 생성
    test_requests = []
    for i in range(20):
        sensor_id = f"TEST-SENSOR-{i%5 + 1:02d}"
        value = random.uniform(0.1, 10.0)
        request = create_ckks_request(sensor_id, value)
        test_requests.append(request)
    
    print(f"=== 동시 요청 관리자 테스트 ===")
    print(f"테스트 요청 수: {len(test_requests)}")
    
    # 동기 배치 테스트
    print("\n1. 동기 배치 테스트")
    start_time = time.time()
    
    try:
        sync_responses = manager.send_batch_requests_sync(test_requests)
        sync_duration = time.time() - start_time
        
        success_count = sum(1 for r in sync_responses if r.success)
        print(f"동기 결과: {success_count}/{len(sync_responses)} 성공, {sync_duration:.2f}초")
        
        # 통계 출력
        stats = manager.get_stats()
        print(f"통계: {stats}")
        
    except Exception as e:
        print(f"동기 테스트 실패: {e}")
    
    # 비동기 배치 테스트
    print("\n2. 비동기 배치 테스트")
    manager.reset_stats()
    
    async def async_test():
        start_time = time.time()
        try:
            async_responses = await manager.send_batch_requests_async(test_requests)
            async_duration = time.time() - start_time
            
            success_count = sum(1 for r in async_responses if r.success)
            print(f"비동기 결과: {success_count}/{len(async_responses)} 성공, {async_duration:.2f}초")
            
            # 통계 출력
            stats = manager.get_stats()
            print(f"통계: {stats}")
            
        finally:
            await manager.close_session()
    
    # 비동기 실행
    try:
        asyncio.run(async_test())
    except Exception as e:
        print(f"비동기 테스트 실패: {e}")
    
    print("동시 요청 관리자 테스트 완료")
#!/usr/bin/env python3
"""
HMAC Client for WADI Experiment
==============================

WADI 센서 데이터를 HMAC으로 인증하여 서버로 전송하는 클라이언트

Author: Claude Code
Date: 2025-08-28
"""

import socket
import json
import time
import threading
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
import asyncio
import aiohttp
from dataclasses import dataclass

from hmac_authenticator import HMACAuthenticator, HMACResult
from wadi_data_loader import WADIDataLoader

@dataclass
class ClientResult:
    """클라이언트 실험 결과"""
    timestamp: datetime
    sensor_count: int
    frequency: int
    hmac_generation_time_ms: float
    hmac_verification_time_ms: float
    network_rtt_ms: float
    success: bool
    data_size_bytes: int
    error_message: str = ""

class HMACClient:
    """HMAC 기반 센서 데이터 전송 클라이언트"""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 8086, key: bytes = None):
        """
        HMAC 클라이언트 초기화
        
        Args:
            server_host: 서버 호스트
            server_port: 서버 포트
            key: HMAC 키
        """
        self.server_host = server_host
        self.server_port = server_port
        self.authenticator = HMACAuthenticator(key=key)
        
        # 데이터 로더 초기화
        self.data_loader = WADIDataLoader()
        self.data_loader.load_data()
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 결과 저장
        self.results = []
        
        # 네트워크 설정
        self.socket_timeout = 10.0
        self.max_retries = 3
    
    async def send_authenticated_data_http(self, data: Dict[str, Any]) -> ClientResult:
        """
        HTTP를 통한 인증된 데이터 전송
        
        Args:
            data: 전송할 센서 데이터
            
        Returns:
            클라이언트 결과
        """
        start_time = time.perf_counter()
        
        try:
            # HMAC 생성
            hmac_start = time.perf_counter()
            authenticated_msg = self.authenticator.create_authenticated_message(data)
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 데이터 크기 계산
            data_json = json.dumps(authenticated_msg)
            data_size = len(data_json.encode('utf-8'))
            
            # HTTP 요청
            network_start = time.perf_counter()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.socket_timeout)) as session:
                async with session.post(
                    f"http://{self.server_host}:{self.server_port}/hmac/verify",
                    json=authenticated_msg,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    response_data = await response.json()
                    
            network_end = time.perf_counter()
            network_rtt = (network_end - network_start) * 1000
            
            # 서버 응답 처리
            server_verified = response_data.get('verified', False)
            hmac_verification_time = response_data.get('verification_time_ms', 0.0)
            
            end_time = time.perf_counter()
            
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=hmac_verification_time,
                network_rtt_ms=network_rtt,
                success=server_verified,
                data_size_bytes=data_size
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            
            self.logger.error(f"HTTP transmission failed: {str(e)}")
            
            return ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=0.0,
                hmac_verification_time_ms=0.0,
                network_rtt_ms=(end_time - start_time) * 1000,
                success=False,
                data_size_bytes=0,
                error_message=str(e)
            )
    
    def send_authenticated_data_socket(self, data: Dict[str, Any]) -> ClientResult:
        """
        Socket을 통한 인증된 데이터 전송
        
        Args:
            data: 전송할 센서 데이터
            
        Returns:
            클라이언트 결과
        """
        start_time = time.perf_counter()
        
        try:
            # HMAC 생성
            hmac_start = time.perf_counter()
            authenticated_msg = self.authenticator.create_authenticated_message(data)
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 데이터 직렬화
            data_json = json.dumps(authenticated_msg)
            data_bytes = data_json.encode('utf-8')
            data_size = len(data_bytes)
            
            # 소켓 연결 및 전송
            network_start = time.perf_counter()
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.socket_timeout)
                sock.connect((self.server_host, self.server_port))
                
                # 데이터 길이 먼저 전송 (4바이트)
                length = len(data_bytes)
                sock.sendall(length.to_bytes(4, byteorder='big'))
                
                # 데이터 전송
                sock.sendall(data_bytes)
                
                # 응답 수신 (길이 먼저)
                response_length_bytes = sock.recv(4)
                if len(response_length_bytes) < 4:
                    raise ConnectionError("Incomplete length received")
                
                response_length = int.from_bytes(response_length_bytes, byteorder='big')
                
                # 응답 데이터 수신
                response_data = b''
                while len(response_data) < response_length:
                    chunk = sock.recv(response_length - len(response_data))
                    if not chunk:
                        raise ConnectionError("Connection closed during response")
                    response_data += chunk
                
                response_json = response_data.decode('utf-8')
                response = json.loads(response_json)
            
            network_end = time.perf_counter()
            network_rtt = (network_end - network_start) * 1000
            
            # 서버 응답 처리
            server_verified = response.get('verified', False)
            hmac_verification_time = response.get('verification_time_ms', 0.0)
            
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=hmac_verification_time,
                network_rtt_ms=network_rtt,
                success=server_verified,
                data_size_bytes=data_size
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            
            self.logger.error(f"Socket transmission failed: {str(e)}")
            
            return ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=0.0,
                hmac_verification_time_ms=0.0,
                network_rtt_ms=(end_time - start_time) * 1000,
                success=False,
                data_size_bytes=0,
                error_message=str(e)
            )
    
    async def run_streaming_experiment(self, sensor_count: int, frequency: int, duration: int = 30) -> List[ClientResult]:
        """
        스트리밍 실험 실행
        
        Args:
            sensor_count: 센서 개수
            frequency: 전송 빈도 (Hz)
            duration: 실험 지속 시간 (초)
            
        Returns:
            실험 결과 리스트
        """
        self.logger.info(f"Starting streaming experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
        # 센서 선택
        selected_sensors = self.data_loader.select_sensors(sensor_count)
        
        # 스트리밍 데이터 생성
        streaming_data = self.data_loader.get_streaming_data(selected_sensors, frequency, duration)
        
        results = []
        interval = 1.0 / frequency  # 전송 간격
        
        start_experiment_time = time.time()
        
        for i, data_point in enumerate(streaming_data):
            # 실제 주파수에 맞춰 대기
            expected_time = start_experiment_time + (i * interval)
            current_time = time.time()
            
            if current_time < expected_time:
                await asyncio.sleep(expected_time - current_time)
            
            # 메타데이터 추가
            transmission_data = {
                'sensor_count': sensor_count,
                'frequency': frequency,
                'sequence': i,
                'experiment_timestamp': datetime.now().isoformat(),
                'sensor_values': data_point['sensor_values']
            }
            
            # 데이터 전송 (HTTP 사용)
            result = await self.send_authenticated_data_http(transmission_data)
            results.append(result)
            
            # 진행 상황 로깅 (매 100번째마다)
            if (i + 1) % 100 == 0:
                success_rate = sum(1 for r in results if r.success) / len(results) * 100
                avg_rtt = sum(r.network_rtt_ms for r in results) / len(results)
                self.logger.info(f"Progress: {i+1}/{len(streaming_data)}, Success: {success_rate:.1f}%, Avg RTT: {avg_rtt:.1f}ms")
        
        self.logger.info(f"Experiment completed: {len(results)} transmissions")
        return results
    
    def run_batch_experiment(self, sensor_count: int, frequency: int, duration: int = 30) -> List[ClientResult]:
        """
        배치 실험 실행 (동기 버전)
        
        Args:
            sensor_count: 센서 개수
            frequency: 전송 빈도 (Hz)
            duration: 실험 지속 시간 (초)
            
        Returns:
            실험 결과 리스트
        """
        self.logger.info(f"Starting batch experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
        # 센서 선택
        selected_sensors = self.data_loader.select_sensors(sensor_count)
        
        # 스트리밍 데이터 생성
        streaming_data = self.data_loader.get_streaming_data(selected_sensors, frequency, duration)
        
        results = []
        interval = 1.0 / frequency
        
        start_experiment_time = time.time()
        
        for i, data_point in enumerate(streaming_data):
            # 실제 주파수에 맞춰 대기
            expected_time = start_experiment_time + (i * interval)
            current_time = time.time()
            
            if current_time < expected_time:
                time.sleep(expected_time - current_time)
            
            # 메타데이터 추가
            transmission_data = {
                'sensor_count': sensor_count,
                'frequency': frequency,
                'sequence': i,
                'experiment_timestamp': datetime.now().isoformat(),
                'sensor_values': data_point['sensor_values']
            }
            
            # 데이터 전송 (Socket 사용)
            result = self.send_authenticated_data_socket(transmission_data)
            results.append(result)
            
            # 진행 상황 로깅
            if (i + 1) % (frequency * 5) == 0:  # 5초마다
                success_rate = sum(1 for r in results if r.success) / len(results) * 100
                avg_rtt = sum(r.network_rtt_ms for r in results) / len(results)
                self.logger.info(f"Progress: {i+1}/{len(streaming_data)}, Success: {success_rate:.1f}%, Avg RTT: {avg_rtt:.1f}ms")
        
        self.logger.info(f"Batch experiment completed: {len(results)} transmissions")
        return results
    
    def test_connection(self) -> bool:
        """
        서버 연결 테스트
        
        Returns:
            연결 성공 여부
        """
        try:
            test_data = {
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'sensor_values': {'test_sensor': 1.0}
            }
            
            result = self.send_authenticated_data_socket(test_data)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_experiment_summary(self, results: List[ClientResult]) -> Dict[str, Any]:
        """
        실험 결과 요약
        
        Args:
            results: 실험 결과 리스트
            
        Returns:
            실험 요약 딕셔너리
        """
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        summary = {
            'total_transmissions': len(results),
            'successful_transmissions': len(successful_results),
            'failed_transmissions': len(failed_results),
            'success_rate': len(successful_results) / len(results) * 100,
            
            # 타이밍 통계
            'avg_hmac_generation_time_ms': sum(r.hmac_generation_time_ms for r in successful_results) / max(1, len(successful_results)),
            'avg_hmac_verification_time_ms': sum(r.hmac_verification_time_ms for r in successful_results) / max(1, len(successful_results)),
            'avg_network_rtt_ms': sum(r.network_rtt_ms for r in successful_results) / max(1, len(successful_results)),
            
            # 데이터 통계
            'avg_data_size_bytes': sum(r.data_size_bytes for r in successful_results) / max(1, len(successful_results)),
            'total_data_transferred_bytes': sum(r.data_size_bytes for r in results),
            
            # 실험 설정
            'sensor_count': results[0].sensor_count if results else 0,
            'frequency': results[0].frequency if results else 0,
            'experiment_duration_seconds': len(results) / results[0].frequency if results and results[0].frequency > 0 else 0,
            
            # 에러 정보
            'error_messages': list(set(r.error_message for r in failed_results if r.error_message))
        }
        
        return summary
    
    def save_results(self, results: List[ClientResult], filepath: str):
        """
        실험 결과를 파일로 저장
        
        Args:
            results: 실험 결과 리스트
            filepath: 저장할 파일 경로
        """
        # 결과를 직렬화 가능한 형태로 변환
        serializable_results = []
        for result in results:
            serializable_results.append({
                'timestamp': result.timestamp.isoformat(),
                'sensor_count': result.sensor_count,
                'frequency': result.frequency,
                'hmac_generation_time_ms': result.hmac_generation_time_ms,
                'hmac_verification_time_ms': result.hmac_verification_time_ms,
                'network_rtt_ms': result.network_rtt_ms,
                'success': result.success,
                'data_size_bytes': result.data_size_bytes,
                'error_message': result.error_message
            })
        
        # 요약 정보 추가
        summary = self.get_experiment_summary(results)
        
        output_data = {
            'experiment_summary': summary,
            'detailed_results': serializable_results,
            'hmac_stats': self.authenticator.get_performance_stats(),
            'experiment_metadata': {
                'client_host': self.server_host,
                'client_port': self.server_port,
                'hmac_algorithm': self.authenticator.algorithm,
                'total_sensors_available': len(self.data_loader.sensor_list),
                'export_timestamp': datetime.now().isoformat()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Results saved to {filepath}")

if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    
    async def test_client():
        client = HMACClient()
        
        # 연결 테스트
        if not client.test_connection():
            print("❌ Server connection failed")
            return
        
        print("✅ Server connection successful")
        
        # 간단한 실험 실행
        results = await client.run_streaming_experiment(
            sensor_count=1, 
            frequency=2, 
            duration=10
        )
        
        # 결과 출력
        summary = client.get_experiment_summary(results)
        print(f"📊 Experiment Summary:")
        print(f"  Success Rate: {summary['success_rate']:.2f}%")
        print(f"  Avg HMAC Generation: {summary['avg_hmac_generation_time_ms']:.3f}ms")
        print(f"  Avg Network RTT: {summary['avg_network_rtt_ms']:.3f}ms")
    
    # 비동기 테스트 실행
    # asyncio.run(test_client())
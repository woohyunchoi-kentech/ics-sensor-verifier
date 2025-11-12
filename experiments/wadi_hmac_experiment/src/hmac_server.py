#!/usr/bin/env python3
"""
HMAC Server for WADI Experiment
==============================

WADI 센서 데이터의 HMAC 검증을 수행하는 서버

Author: Claude Code
Date: 2025-08-28
"""

import socket
import json
import time
import threading
import logging
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from aiohttp import web, WSMsgType
import aiohttp_cors
from concurrent.futures import ThreadPoolExecutor

from hmac_authenticator import HMACAuthenticator

class HMACServer:
    """HMAC 검증 서버"""
    
    def __init__(self, host: str = "localhost", port: int = 8086, key: bytes = None):
        """
        HMAC 서버 초기화
        
        Args:
            host: 서버 호스트
            port: 서버 포트  
            key: HMAC 키 (클라이언트와 동일해야 함)
        """
        self.host = host
        self.port = port
        self.authenticator = HMACAuthenticator(key=key)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 서버 상태
        self.running = False
        self.total_requests = 0
        self.successful_verifications = 0
        self.failed_verifications = 0
        
        # 성능 모니터링
        self.request_times = []
        self.verification_times = []
        
        # HTTP 앱 설정
        self.app = web.Application()
        self._setup_routes()
        
        # CORS 설정
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 모든 라우트에 CORS 적용
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def _setup_routes(self):
        """HTTP 라우트 설정"""
        self.app.router.add_post('/hmac/verify', self.handle_hmac_verification)
        self.app.router.add_get('/hmac/stats', self.handle_get_stats)
        self.app.router.add_get('/hmac/health', self.handle_health_check)
        self.app.router.add_post('/hmac/reset', self.handle_reset_stats)
    
    async def handle_hmac_verification(self, request):
        """
        HMAC 검증 요청 처리
        
        Args:
            request: HTTP 요청 객체
            
        Returns:
            검증 결과 응답
        """
        start_time = time.perf_counter()
        self.total_requests += 1
        
        try:
            # 요청 데이터 파싱
            data = await request.json()
            
            # HMAC 검증
            verification_start = time.perf_counter()
            is_valid, original_data = self.authenticator.verify_authenticated_message(data)
            verification_end = time.perf_counter()
            
            verification_time_ms = (verification_end - verification_start) * 1000
            self.verification_times.append(verification_time_ms)
            
            if is_valid:
                self.successful_verifications += 1
            else:
                self.failed_verifications += 1
            
            end_time = time.perf_counter()
            total_time_ms = (end_time - start_time) * 1000
            self.request_times.append(total_time_ms)
            
            # 응답 생성
            response_data = {
                'verified': is_valid,
                'verification_time_ms': verification_time_ms,
                'total_time_ms': total_time_ms,
                'timestamp': datetime.now().isoformat(),
                'request_id': self.total_requests
            }
            
            # 검증 성공 시 원본 데이터 정보 추가
            if is_valid and original_data:
                response_data['sensor_count'] = len(original_data.get('sensor_values', {}))
                response_data['data_sequence'] = original_data.get('sequence', 0)
            
            return web.json_response(response_data)
            
        except json.JSONDecodeError:
            self.failed_verifications += 1
            return web.json_response({
                'verified': False,
                'error': 'Invalid JSON format',
                'timestamp': datetime.now().isoformat()
            }, status=400)
            
        except Exception as e:
            self.failed_verifications += 1
            self.logger.error(f"Verification error: {str(e)}")
            
            return web.json_response({
                'verified': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def handle_get_stats(self, request):
        """서버 통계 정보 반환"""
        stats = self.get_server_stats()
        return web.json_response(stats)
    
    async def handle_health_check(self, request):
        """서버 상태 체크"""
        return web.json_response({
            'status': 'healthy',
            'running': self.running,
            'timestamp': datetime.now().isoformat(),
            'total_requests': self.total_requests
        })
    
    async def handle_reset_stats(self, request):
        """통계 초기화"""
        self.reset_stats()
        return web.json_response({
            'message': 'Stats reset successfully',
            'timestamp': datetime.now().isoformat()
        })
    
    def handle_socket_connection(self, client_socket, address):
        """
        Socket 연결 처리 (legacy 지원)
        
        Args:
            client_socket: 클라이언트 소켓
            address: 클라이언트 주소
        """
        start_time = time.perf_counter()
        self.total_requests += 1
        
        try:
            # 데이터 길이 수신 (4바이트)
            length_bytes = client_socket.recv(4)
            if len(length_bytes) < 4:
                raise ConnectionError("Incomplete length received")
            
            data_length = int.from_bytes(length_bytes, byteorder='big')
            
            # 데이터 수신
            received_data = b''
            while len(received_data) < data_length:
                chunk = client_socket.recv(data_length - len(received_data))
                if not chunk:
                    raise ConnectionError("Connection closed during data reception")
                received_data += chunk
            
            # JSON 파싱
            data_json = received_data.decode('utf-8')
            data = json.loads(data_json)
            
            # HMAC 검증
            verification_start = time.perf_counter()
            is_valid, original_data = self.authenticator.verify_authenticated_message(data)
            verification_end = time.perf_counter()
            
            verification_time_ms = (verification_end - verification_start) * 1000
            self.verification_times.append(verification_time_ms)
            
            if is_valid:
                self.successful_verifications += 1
            else:
                self.failed_verifications += 1
            
            end_time = time.perf_counter()
            total_time_ms = (end_time - start_time) * 1000
            self.request_times.append(total_time_ms)
            
            # 응답 생성
            response_data = {
                'verified': is_valid,
                'verification_time_ms': verification_time_ms,
                'total_time_ms': total_time_ms,
                'timestamp': datetime.now().isoformat(),
                'request_id': self.total_requests
            }
            
            # 응답 전송
            response_json = json.dumps(response_data)
            response_bytes = response_json.encode('utf-8')
            
            # 응답 길이 먼저 전송
            client_socket.sendall(len(response_bytes).to_bytes(4, byteorder='big'))
            # 응답 데이터 전송
            client_socket.sendall(response_bytes)
            
        except Exception as e:
            self.failed_verifications += 1
            self.logger.error(f"Socket handling error: {str(e)}")
            
            try:
                error_response = {
                    'verified': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                response_json = json.dumps(error_response)
                response_bytes = response_json.encode('utf-8')
                
                client_socket.sendall(len(response_bytes).to_bytes(4, byteorder='big'))
                client_socket.sendall(response_bytes)
            except:
                pass  # 클라이언트 연결이 끊어진 경우
        
        finally:
            client_socket.close()
    
    def start_socket_server(self):
        """Socket 서버 시작 (별도 스레드에서)"""
        def socket_server():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind((self.host, self.port + 1))  # HTTP 포트 + 1
                server_socket.listen(5)
                
                self.logger.info(f"Socket server listening on {self.host}:{self.port + 1}")
                
                while self.running:
                    try:
                        server_socket.settimeout(1.0)  # 1초마다 running 상태 체크
                        client_socket, address = server_socket.accept()
                        
                        # 각 연결을 별도 스레드에서 처리
                        client_thread = threading.Thread(
                            target=self.handle_socket_connection,
                            args=(client_socket, address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                        
                    except socket.timeout:
                        continue  # 타임아웃은 정상, running 상태 체크 후 계속
                    except Exception as e:
                        if self.running:
                            self.logger.error(f"Socket server error: {str(e)}")
        
        socket_thread = threading.Thread(target=socket_server)
        socket_thread.daemon = True
        socket_thread.start()
    
    async def start_http_server(self):
        """HTTP 서버 시작"""
        self.running = True
        
        # Socket 서버도 함께 시작
        self.start_socket_server()
        
        # HTTP 서버 시작
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"HMAC Server started on http://{self.host}:{self.port}")
        self.logger.info(f"Socket server started on {self.host}:{self.port + 1}")
        self.logger.info("Available endpoints:")
        self.logger.info(f"  POST http://{self.host}:{self.port}/hmac/verify - HMAC verification")
        self.logger.info(f"  GET  http://{self.host}:{self.port}/hmac/stats - Server statistics")
        self.logger.info(f"  GET  http://{self.host}:{self.port}/hmac/health - Health check")
        
        try:
            # 서버 실행 유지
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Server shutdown requested")
        finally:
            await runner.cleanup()
            self.running = False
    
    def stop_server(self):
        """서버 중지"""
        self.running = False
        self.logger.info("Server stopping...")
    
    def get_server_stats(self) -> Dict[str, Any]:
        """
        서버 통계 정보 반환
        
        Returns:
            서버 통계 딕셔너리
        """
        stats = {
            'server_info': {
                'host': self.host,
                'port': self.port,
                'running': self.running,
                'start_time': datetime.now().isoformat()
            },
            
            'request_stats': {
                'total_requests': self.total_requests,
                'successful_verifications': self.successful_verifications,
                'failed_verifications': self.failed_verifications,
                'success_rate': (self.successful_verifications / max(1, self.total_requests)) * 100
            },
            
            'performance_stats': {
                'avg_request_time_ms': sum(self.request_times) / max(1, len(self.request_times)),
                'avg_verification_time_ms': sum(self.verification_times) / max(1, len(self.verification_times)),
                'min_request_time_ms': min(self.request_times) if self.request_times else 0,
                'max_request_time_ms': max(self.request_times) if self.request_times else 0
            },
            
            'hmac_stats': self.authenticator.get_performance_stats(),
            
            'system_info': {
                'timestamp': datetime.now().isoformat(),
                'recent_requests': len([t for t in self.request_times[-100:] if t]),  # 최근 100개
                'memory_usage_mb': self._get_memory_usage()
            }
        }
        
        return stats
    
    def _get_memory_usage(self) -> float:
        """메모리 사용량 반환 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def reset_stats(self):
        """통계 초기화"""
        self.total_requests = 0
        self.successful_verifications = 0
        self.failed_verifications = 0
        self.request_times.clear()
        self.verification_times.clear()
        self.authenticator.reset_stats()
        
        self.logger.info("Server statistics reset")
    
    def export_stats(self, filepath: str):
        """
        통계를 파일로 내보내기
        
        Args:
            filepath: 저장할 파일 경로
        """
        stats = self.get_server_stats()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Stats exported to {filepath}")

# 서버 실행을 위한 헬퍼 함수들
async def run_server(host: str = "localhost", port: int = 8086):
    """
    서버 실행 헬퍼 함수
    
    Args:
        host: 서버 호스트
        port: 서버 포트
    """
    server = HMACServer(host=host, port=port)
    
    try:
        await server.start_http_server()
    except KeyboardInterrupt:
        server.stop_server()

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HMAC Server for WADI Experiment')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8086, help='Server port')
    parser.add_argument('--log-level', default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    
    print(f"🚀 Starting HMAC Server on {args.host}:{args.port}")
    print("Press Ctrl+C to stop the server")
    
    try:
        asyncio.run(run_server(host=args.host, port=args.port))
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    main()
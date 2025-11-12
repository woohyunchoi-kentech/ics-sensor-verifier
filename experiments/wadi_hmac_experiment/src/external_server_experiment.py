#!/usr/bin/env python3
"""
WADI HMAC 외부 서버 실험
=======================

외부 ICS Server Verifier를 사용한 WADI HMAC 실험
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from experiment_runner import WADIHMACExperiment, ExperimentConfig
from hmac_client import HMACClient, ClientResult

class ExternalServerClient(HMACClient):
    """외부 ICS Server Verifier용 클라이언트"""
    
    def __init__(self, server_host: str = "192.168.0.11", server_port: int = 8085, key: bytes = None):
        super().__init__(server_host, server_port, key)
        self.verify_endpoint = f"http://{server_host}:{server_port}/api/v1/verify/hmac"
        self.health_endpoint = f"http://{server_host}:{server_port}/health"
    
    async def send_authenticated_data_http(self, data: Dict[str, Any]) -> ClientResult:
        """
        외부 서버 API에 맞춘 HTTP 전송
        """
        start_time = time.perf_counter()
        
        try:
            # HMAC 생성
            hmac_start = time.perf_counter()
            authenticated_msg = self.authenticator.create_authenticated_message(data)
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 센서 값 추출 (첫 번째 센서 값 사용)
            sensor_values = data.get('sensor_values', {})
            if sensor_values:
                first_sensor_value = list(sensor_values.values())[0]
                sensor_id = list(sensor_values.keys())[0] if sensor_values else "unknown"
            else:
                first_sensor_value = 0.0
                sensor_id = "test_sensor"
            
            # 외부 서버 API 형식에 맞춤
            request_payload = {
                "sensor_value": first_sensor_value,
                "timestamp": int(time.time() * 1000),  # 밀리초 타임스탬프
                "received_mac": authenticated_msg["hmac"],
                "sensor_id": str(sensor_id)
            }
            
            data_json = json.dumps(request_payload)
            data_size = len(data_json.encode('utf-8'))
            
            # HTTP 요청
            network_start = time.perf_counter()
            
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.post(
                    self.verify_endpoint,
                    json=request_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                    else:
                        response_text = await response.text()
                        raise Exception(f"Server error {response.status}: {response_text}")
                    
            network_end = time.perf_counter()
            network_rtt = (network_end - network_start) * 1000
            
            # 서버 응답 처리
            server_verified = response_data.get('verified', False)
            processing_time = response_data.get('processing_time_ms', 0.0)
            
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=processing_time,  # 외부 서버의 처리 시간 사용
                network_rtt_ms=network_rtt,
                success=server_verified,
                data_size_bytes=data_size
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            self.logger.error(f"External server transmission failed: {str(e)}")
            
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
    
    async def test_connection(self) -> bool:
        """외부 서버 연결 테스트"""
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.health_endpoint) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

class ExternalServerExperiment(WADIHMACExperiment):
    """외부 서버용 실험 클래스"""
    
    async def setup_experiment(self):
        """외부 서버를 위한 실험 환경 설정"""
        self.logger.info(f"Setting up external server WADI HMAC experiment: {self.experiment_id}")
        self.logger.info(f"Target server: {self.config.server_host}:{self.config.server_port}")
        
        # 외부 서버용 클라이언트 초기화
        self.client = ExternalServerClient(
            server_host=self.config.server_host,
            server_port=self.config.server_port
        )
        
        # 연결 테스트
        if not await self.client.test_connection():
            raise RuntimeError(f"Failed to connect to external server {self.config.server_host}:{self.config.server_port}")
        
        # 성능 모니터는 로컬에서만 실행
        from performance_monitor import PerformanceMonitor
        self.monitor = PerformanceMonitor(monitoring_interval=1.0)
        self.monitor.start_monitoring()
        
        self.logger.info("External server experiment setup completed")
    
    async def _test_connection(self) -> bool:
        """외부 서버 연결 테스트"""
        return await self.client.test_connection()
    
    async def cleanup(self):
        """외부 서버 실험 정리"""
        self.logger.info("🧹 Cleaning up external server experiment")
        
        # 성능 모니터 중지
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.logger.info("✅ Cleanup completed")

async def main():
    """외부 서버 실험 메인 함수"""
    print("🌐 WADI HMAC 외부 서버 실험 시스템")
    print("=" * 50)
    
    # 실험 설정
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10, 50, 100],  # 원래 명세
        frequencies=[1, 2, 10, 100],     # 원래 명세 
        duration_seconds=1000,           # 각 조건당 1000초
        server_host="192.168.0.11",     # 외부 서버
        server_port=8085,               # 외부 서버 포트
        results_dir="../results"
    )
    
    print(f"🎯 실험 설정:")
    print(f"  • 대상 서버: {config.server_host}:{config.server_port}")
    print(f"  • 데이터셋: {config.dataset_name}")
    print(f"  • 센서 개수: {config.sensor_counts}")
    print(f"  • 전송 주파수: {config.frequencies} Hz")
    print(f"  • 각 조건 실행 시간: {config.duration_seconds} 초")
    
    total_time_minutes = len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 60
    print(f"  • 예상 총 실험 시간: {total_time_minutes:.1f} 분 ({total_time_minutes/60:.1f} 시간)")
    
    # 사용자 확인
    proceed = input(f"\n🚀 외부 서버 {config.server_host}:{config.server_port}에서 실험을 시작하시겠습니까? (y/N): ").strip().lower()
    if proceed != 'y':
        print("❌ 실험 취소됨")
        return
    
    # 실험 실행
    experiment = ExternalServerExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 실험 완료! 결과 저장 위치: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 실험 중단됨")
        await experiment.cleanup()
        
    except Exception as e:
        print(f"\n❌ 실험 실패: {str(e)}")
        await experiment.cleanup()
        raise

if __name__ == "__main__":
    asyncio.run(main())
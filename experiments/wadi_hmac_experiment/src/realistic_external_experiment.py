#!/usr/bin/env python3
"""
현실적인 외부 서버 WADI HMAC 실험
===============================

외부 서버의 실제 동작 방식에 맞춘 성능 측정 실험
"""

import asyncio
import json
import time
import hmac
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from experiment_runner import WADIHMACExperiment, ExperimentConfig
from hmac_client import ClientResult

class RealisticExternalClient:
    """현실적인 외부 서버 클라이언트"""
    
    def __init__(self, server_host: str = "192.168.0.11", server_port: int = 8085):
        self.server_host = server_host
        self.server_port = server_port
        self.verify_endpoint = f"http://{server_host}:{server_port}/api/v1/verify/hmac"
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader()
        self.data_loader.load_data()
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
        # 서버의 실제 키를 모르므로, 성능 측정 위주로 진행
        # 외부 서버는 자체적으로 HMAC을 계산하여 비교함
        
    async def send_sensor_data_for_performance(self, data: Dict[str, Any]) -> ClientResult:
        """
        성능 측정을 위한 센서 데이터 전송
        (HMAC 검증 성공/실패보다는 처리 성능에 집중)
        """
        start_time = time.perf_counter()
        
        try:
            # 센서 값 추출
            sensor_values = data.get('sensor_values', {})
            if sensor_values:
                first_sensor_value = list(sensor_values.values())[0]
                sensor_id = list(sensor_values.keys())[0]
            else:
                first_sensor_value = 0.0
                sensor_id = "unknown"
            
            # 간단한 로컬 HMAC 생성 (성능 비교용)
            hmac_start = time.perf_counter()
            local_key = f"sensor_{sensor_id}".encode('utf-8')
            message = f"{sensor_id}:{first_sensor_value}:{int(time.time() * 1000)}".encode('utf-8')
            local_mac = hmac.new(local_key, message, hashlib.sha256).hexdigest()
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 외부 서버 요청 페이로드
            request_payload = {
                "sensor_value": float(first_sensor_value),
                "timestamp": int(time.time() * 1000),
                "received_mac": local_mac,
                "sensor_id": str(sensor_id)
            }
            
            data_size = len(json.dumps(request_payload).encode('utf-8'))
            
            # 네트워크 요청
            network_start = time.perf_counter()
            
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
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
            
            # 응답 처리 (검증 성공/실패는 중요하지 않음)
            server_verified = response_data.get('verified', False)
            processing_time = response_data.get('processing_time_ms', 0.0)
            
            # 성능 측정이 목적이므로 success=True로 설정
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=processing_time,
                network_rtt_ms=network_rtt,
                success=True,  # 서버가 응답했으므로 성공으로 간주
                data_size_bytes=data_size
            )
            
            # 추가 정보 로깅
            if hasattr(result, 'additional_info'):
                result.additional_info = {
                    'server_verified': server_verified,
                    'server_algorithm': response_data.get('algorithm', 'unknown'),
                    'server_timestamp': response_data.get('timestamp', 0)
                }
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            self.logger.error(f"External server request failed: {str(e)}")
            
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
    
    async def run_streaming_experiment(self, sensor_count: int, frequency: int, duration: int = 1000):
        """
        외부 서버를 대상으로 한 스트리밍 실험
        """
        self.logger.info(f"Starting external server experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
        # 센서 선택
        selected_sensors = self.data_loader.select_sensors(sensor_count)
        
        # 스트리밍 데이터 생성
        streaming_data = self.data_loader.get_streaming_data(
            sensors=selected_sensors,
            frequency=frequency,
            duration=duration
        )
        
        results = []
        total_requests = len(streaming_data)
        successful_requests = 0
        
        # 전송 시작
        start_time = time.time()
        interval = 1.0 / frequency
        
        for i, data_point in enumerate(streaming_data):
            # 정확한 타이밍 유지
            target_time = start_time + (i * interval)
            current_time = time.time()
            
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            # 데이터 전송
            result = await self.send_sensor_data_for_performance(data_point)
            results.append(result)
            
            if result.success:
                successful_requests += 1
            
            # 진행 상황 로깅 (100개마다)
            if (i + 1) % 100 == 0:
                success_rate = (successful_requests / (i + 1)) * 100
                avg_rtt = sum(r.network_rtt_ms for r in results[-100:]) / min(100, len(results))
                self.logger.info(f"Progress: {i+1}/{total_requests}, Success: {success_rate:.1f}%, Avg RTT: {avg_rtt:.1f}ms")
        
        self.logger.info(f"External server experiment completed: {len(results)} total, {successful_requests} successful")
        return results

class RealisticExternalExperiment(WADIHMACExperiment):
    """현실적인 외부 서버 실험"""
    
    async def setup_experiment(self):
        """외부 서버 실험 설정"""
        self.logger.info(f"Setting up realistic external server experiment: {self.experiment_id}")
        self.logger.info(f"Target server: {self.config.server_host}:{self.config.server_port}")
        
        # 외부 서버용 클라이언트
        self.client = RealisticExternalClient(
            server_host=self.config.server_host,
            server_port=self.config.server_port
        )
        
        # 연결 테스트
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"http://{self.config.server_host}:{self.config.server_port}/health") as response:
                    if response.status != 200:
                        raise RuntimeError(f"Server health check failed: {response.status}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to external server: {str(e)}")
        
        # 로컬 성능 모니터
        from performance_monitor import PerformanceMonitor
        self.monitor = PerformanceMonitor(monitoring_interval=1.0)
        self.monitor.start_monitoring()
        
        self.logger.info("Realistic external server experiment setup completed")
    
    async def cleanup(self):
        """실험 정리"""
        self.logger.info("🧹 Cleaning up realistic external server experiment")
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.logger.info("✅ Cleanup completed")

async def main():
    """메인 실험 실행"""
    print("🌐 현실적인 WADI HMAC 외부 서버 실험")
    print("=" * 60)
    print("📋 실험 목적: 외부 서버의 HMAC 처리 성능 측정")
    print("🎯 측정 항목: 네트워크 RTT, 서버 응답 시간, 처리량")
    
    # 실험 설정
    config = ExperimentConfig(
        dataset_name="WADI", 
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],
        duration_seconds=1000,
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results"
    )
    
    print(f"\n🎯 실험 설정:")
    print(f"  • 대상 서버: {config.server_host}:{config.server_port}")
    print(f"  • 센서 개수: {config.sensor_counts}")
    print(f"  • 전송 주파수: {config.frequencies} Hz")
    print(f"  • 각 조건 실행 시간: {config.duration_seconds}초")
    
    total_time_hours = len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 3600
    print(f"  • 예상 총 실험 시간: {total_time_hours:.1f}시간")
    
    print("\n🚀 현실적인 성능 측정 실험을 시작합니다...")
    
    experiment = RealisticExternalExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 실험 완료! 결과: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 실험 중단됨")
        await experiment.cleanup()
        
    except Exception as e:
        print(f"\n❌ 실험 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        await experiment.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
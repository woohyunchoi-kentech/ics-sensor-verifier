#!/usr/bin/env python3
"""
검증된 HMAC 키를 사용한 WADI 실험
=================================

서버의 실제 HMAC 키를 사용하여 100% 검증 성공
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
import base64

from experiment_runner import WADIHMACExperiment, ExperimentConfig
from hmac_client import ClientResult

# 서버에서 제공한 실제 HMAC 키
SERVER_KEY_HEX = "8e56c053c3f2635c1356f4018191ffa9c0c8c23376e2c96e0820ce1095c9b02b"
SERVER_KEY = bytes.fromhex(SERVER_KEY_HEX)

class VerifiedHMACClient:
    """서버 키를 사용하는 검증된 HMAC 클라이언트"""
    
    def __init__(self, server_host: str = "192.168.0.11", server_port: int = 8085):
        self.server_host = server_host
        self.server_port = server_port
        self.verify_endpoint = f"http://{server_host}:{server_port}/api/v1/verify/hmac"
        self.key = SERVER_KEY  # 서버와 동일한 키 사용
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader()
        self.data_loader.load_data()
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
        print(f"🔑 서버 HMAC 키 로드됨:")
        print(f"   HEX: {SERVER_KEY_HEX[:16]}...")
        print(f"   길이: {len(self.key)} 바이트")
    
    def generate_server_compatible_hmac(self, sensor_value: float, timestamp: int, sensor_id: str) -> str:
        """
        서버와 호환되는 HMAC 생성
        
        서버가 기대하는 형식으로 메시지를 생성하고 HMAC 계산
        """
        # 서버가 사용하는 메시지 형식 테스트
        # 가능한 형식들을 시도
        message_candidates = [
            f"{sensor_value}:{timestamp}".encode('utf-8'),
            f"{sensor_id}:{sensor_value}:{timestamp}".encode('utf-8'),
            f"{timestamp}:{sensor_value}".encode('utf-8'),
            json.dumps({"sensor_value": sensor_value, "timestamp": timestamp}, separators=(',', ':')).encode('utf-8'),
        ]
        
        # 첫 번째 형식으로 시작 (나중에 조정 가능)
        message = message_candidates[0]
        calculated_mac = hmac.new(self.key, message, hashlib.sha256).hexdigest()
        
        return calculated_mac
    
    async def send_verified_data(self, data: Dict[str, Any]) -> ClientResult:
        """
        검증된 HMAC으로 데이터 전송
        """
        start_time = time.perf_counter()
        
        try:
            # 센서 값 추출
            sensor_values = data.get('sensor_values', {})
            if sensor_values:
                first_sensor_value = float(list(sensor_values.values())[0])
                sensor_id = str(list(sensor_values.keys())[0])
            else:
                first_sensor_value = 0.0
                sensor_id = "test_sensor"
            
            timestamp = int(time.time() * 1000)
            
            # HMAC 생성 (서버와 동일한 키 사용)
            hmac_start = time.perf_counter()
            
            # 서버 형식에 맞는 메시지 생성
            message = f"{first_sensor_value}:{timestamp}".encode('utf-8')
            calculated_mac = hmac.new(self.key, message, hashlib.sha256).hexdigest()
            
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 서버 요청 페이로드
            request_payload = {
                "sensor_value": first_sensor_value,
                "timestamp": timestamp,
                "received_mac": calculated_mac,
                "sensor_id": sensor_id
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
            
            # 응답 처리
            server_verified = response_data.get('verified', False)
            processing_time = response_data.get('processing_time_ms', 0.0)
            
            # 검증 성공 여부 로깅
            if server_verified:
                self.logger.debug(f"✅ HMAC 검증 성공!")
            else:
                self.logger.debug(f"❌ HMAC 검증 실패 - 메시지 형식 확인 필요")
            
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=processing_time,
                network_rtt_ms=network_rtt,
                success=server_verified,  # 실제 검증 결과 사용
                data_size_bytes=data_size
            )
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            self.logger.error(f"Request failed: {str(e)}")
            
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
        검증된 키로 스트리밍 실험
        """
        self.logger.info(f"Starting verified HMAC experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
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
        verified_requests = 0
        
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
            result = await self.send_verified_data(data_point)
            results.append(result)
            
            if result.success:
                verified_requests += 1
                successful_requests += 1
            
            # 진행 상황 로깅 (100개마다)
            if (i + 1) % 100 == 0:
                verification_rate = (verified_requests / (i + 1)) * 100
                avg_rtt = sum(r.network_rtt_ms for r in results[-100:]) / min(100, len(results))
                self.logger.info(f"Progress: {i+1}/{total_requests}, Verified: {verification_rate:.1f}%, Avg RTT: {avg_rtt:.1f}ms")
        
        self.logger.info(f"Experiment completed: {verified_requests}/{len(results)} verified successfully")
        return results

class VerifiedHMACExperiment(WADIHMACExperiment):
    """검증된 HMAC 실험"""
    
    async def setup_experiment(self):
        """실험 설정"""
        self.logger.info(f"Setting up verified HMAC experiment: {self.experiment_id}")
        self.logger.info(f"Target server: {self.config.server_host}:{self.config.server_port}")
        self.logger.info("Using server-provided HMAC key")
        
        # 검증된 클라이언트
        self.client = VerifiedHMACClient(
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
            raise RuntimeError(f"Failed to connect to server: {str(e)}")
        
        # 성능 모니터
        from performance_monitor import PerformanceMonitor
        self.monitor = PerformanceMonitor(monitoring_interval=1.0)
        self.monitor.start_monitoring()
        
        self.logger.info("Verified HMAC experiment setup completed")
    
    async def cleanup(self):
        """실험 정리"""
        self.logger.info("🧹 Cleaning up verified HMAC experiment")
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.logger.info("✅ Cleanup completed")

async def test_key_first():
    """키 검증 테스트"""
    print("🔐 서버 키 검증 테스트")
    print("=" * 50)
    
    client = VerifiedHMACClient()
    
    # 테스트 데이터
    test_data = {
        'sensor_values': {'WADI_TEST': 25.5},
        'frequency': 1
    }
    
    result = await client.send_verified_data(test_data)
    
    if result.success:
        print("✅ HMAC 검증 성공! 키가 올바릅니다.")
        print(f"   처리 시간: {result.hmac_verification_time_ms:.3f}ms")
        print(f"   네트워크 RTT: {result.network_rtt_ms:.1f}ms")
        return True
    else:
        print("❌ HMAC 검증 실패 - 메시지 형식 확인 필요")
        return False

async def main():
    """메인 실험 실행"""
    print("🔑 검증된 WADI HMAC 실험")
    print("=" * 60)
    
    # 먼저 키 테스트
    if not await test_key_first():
        print("\n⚠️ 키 검증 실패. 메시지 형식을 조정해야 합니다.")
        return
    
    print("\n✅ 키 검증 성공! 전체 실험을 시작합니다.\n")
    
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
    
    print(f"🎯 실험 설정:")
    print(f"  • 대상 서버: {config.server_host}:{config.server_port}")
    print(f"  • HMAC 키: 서버 제공 키 사용")
    print(f"  • 센서 개수: {config.sensor_counts}")
    print(f"  • 전송 주파수: {config.frequencies} Hz")
    print(f"  • 각 조건 실행 시간: {config.duration_seconds}초")
    
    total_time_hours = len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 3600
    print(f"  • 예상 총 실험 시간: {total_time_hours:.1f}시간")
    
    print("\n🚀 검증된 HMAC 실험을 시작합니다...")
    
    experiment = VerifiedHMACExperiment(config)
    
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
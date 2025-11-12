#!/usr/bin/env python3
"""
올바른 HMAC 형식 실험 - 100% 검증 성공
=====================================

서버의 정확한 형식: sensor_value:timestamp
"""

import asyncio
import json
import time
import hmac
import hashlib
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from experiment_runner import WADIHMACExperiment, ExperimentConfig
from hmac_client import ClientResult

# 서버 HMAC 키
SERVER_KEY = base64.b64decode("jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs=")

class CorrectHMACClient:
    """올바른 HMAC 형식을 사용하는 클라이언트"""
    
    def __init__(self, server_host: str = "192.168.0.11", server_port: int = 8085):
        self.server_host = server_host
        self.server_port = server_port
        self.verify_endpoint = f"http://{server_host}:{server_port}/api/v1/verify/hmac"
        self.key = SERVER_KEY
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader()
        self.data_loader.load_data()
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
        print(f"🔑 HMAC 키 로드 완료:")
        print(f"   길이: {len(self.key)} 바이트")
        print(f"📋 올바른 메시지 형식: sensor_value:timestamp")
    
    def calculate_correct_hmac(self, sensor_value: float, timestamp: int) -> str:
        """
        올바른 HMAC 계산
        
        형식: sensor_value:timestamp
        """
        # 서버가 요구하는 정확한 메시지 형식
        message = f"{sensor_value}:{timestamp}".encode('utf-8')
        
        # HMAC-SHA256 계산
        signature = hmac.new(self.key, message, hashlib.sha256).digest()
        
        # HEX 형식으로 반환
        signature_hex = signature.hex()
        
        self.logger.debug(f"Message: {message.decode()}")
        self.logger.debug(f"HMAC (hex): {signature_hex[:32]}...")
        
        return signature_hex
    
    async def send_correct_data(self, data: Dict[str, Any]) -> ClientResult:
        """
        올바른 형식으로 데이터 전송
        """
        start_time = time.perf_counter()
        
        try:
            # 센서 값 추출
            sensor_values = data.get('sensor_values', {})
            if sensor_values:
                first_sensor_value = float(list(sensor_values.values())[0])
                sensor_id = str(list(sensor_values.keys())[0])
            else:
                first_sensor_value = 2.45
                sensor_id = "WADI_TEST"
            
            # 타임스탬프 (초 단위, 정수)
            timestamp = int(time.time())
            
            # HMAC 생성
            hmac_start = time.perf_counter()
            calculated_mac = self.calculate_correct_hmac(first_sensor_value, timestamp)
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 올바른 요청 형식
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
            
            if server_verified:
                self.logger.info(f"✅ HMAC 검증 성공!")
            else:
                self.logger.debug(f"❌ 검증 실패 - 디버깅:")
                self.logger.debug(f"   요청: {json.dumps(request_payload, indent=2)}")
                self.logger.debug(f"   응답: {json.dumps(response_data, indent=2)}")
            
            result = ClientResult(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                hmac_verification_time_ms=processing_time,
                network_rtt_ms=network_rtt,
                success=server_verified,
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
        스트리밍 실험 실행
        """
        self.logger.info(f"Starting correct HMAC experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
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
            result = await self.send_correct_data(data_point)
            results.append(result)
            
            if result.success:
                verified_requests += 1
                successful_requests += 1
            
            # 진행 상황 로깅 (100개마다)
            if (i + 1) % 100 == 0:
                verification_rate = (verified_requests / (i + 1)) * 100
                avg_rtt = sum(r.network_rtt_ms for r in results[-100:]) / min(100, len(results))
                self.logger.info(f"Progress: {i+1}/{total_requests}, Verified: {verification_rate:.1f}%, Avg RTT: {avg_rtt:.1f}ms")
        
        verification_rate = (verified_requests / len(results)) * 100
        self.logger.info(f"Experiment completed: {verified_requests}/{len(results)} ({verification_rate:.1f}%) verified")
        return results

class CorrectHMACExperiment(WADIHMACExperiment):
    """올바른 HMAC 실험"""
    
    async def setup_experiment(self):
        """실험 설정"""
        self.logger.info(f"Setting up correct HMAC experiment: {self.experiment_id}")
        self.logger.info(f"Target server: {self.config.server_host}:{self.config.server_port}")
        
        # 올바른 클라이언트
        self.client = CorrectHMACClient(
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
        
        self.logger.info("Correct HMAC experiment setup completed")
    
    async def cleanup(self):
        """실험 정리"""
        self.logger.info("🧹 Cleaning up correct HMAC experiment")
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.logger.info("✅ Cleanup completed")

async def test_correct_format():
    """올바른 형식 테스트"""
    print("🔐 올바른 HMAC 형식 테스트")
    print("=" * 50)
    
    client = CorrectHMACClient()
    
    # 테스트 데이터
    test_data = {
        'sensor_values': {'WADI_TEST': 2.45},
        'frequency': 1
    }
    
    result = await client.send_correct_data(test_data)
    
    if result.success:
        print("🎉 HMAC 검증 성공! 올바른 형식입니다!")
        print(f"   처리 시간: {result.hmac_verification_time_ms:.3f}ms")
        print(f"   네트워크 RTT: {result.network_rtt_ms:.1f}ms")
        return True
    else:
        print("❌ HMAC 검증 실패")
        print(f"   오류: {result.error_message}")
        return False

async def main():
    """메인 실험"""
    print("🔑 올바른 WADI HMAC 실험")
    print("=" * 60)
    print("📋 메시지 형식: sensor_value:timestamp")
    print("🔐 서버 키: 제공된 32바이트 키")
    print("🎯 목표: 100% HMAC 검증 성공")
    
    # 형식 테스트
    if not await test_correct_format():
        print("\n⚠️ 형식 테스트 실패. 서버 관리자 재문의 필요.")
        return
    
    print("\n✅ HMAC 검증 성공! 전체 실험을 시작합니다.\n")
    
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
    print(f"  • 서버: {config.server_host}:{config.server_port}")
    print(f"  • 센서: {config.sensor_counts}")
    print(f"  • 주파수: {config.frequencies} Hz")
    print(f"  • 시간: {config.duration_seconds}초/조건")
    
    total_conditions = len(config.sensor_counts) * len(config.frequencies)
    total_time_hours = total_conditions * config.duration_seconds / 3600
    print(f"  • 총 조건: {total_conditions}개")
    print(f"  • 예상 시간: {total_time_hours:.1f}시간")
    
    print("\n🚀 100% 검증 성공 HMAC 실험 시작!")
    
    experiment = CorrectHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 실험 완료! 결과: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 중단됨")
        await experiment.cleanup()
        
    except Exception as e:
        print(f"\n❌ 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        await experiment.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
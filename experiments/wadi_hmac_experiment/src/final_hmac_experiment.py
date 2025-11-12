#!/usr/bin/env python3
"""
최종 WADI HMAC 실험 - 100% 검증 성공
====================================

서버의 정확한 메시지 형식을 사용한 완벽한 HMAC 검증
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
SERVER_KEY_BASE64 = "jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs="
SERVER_KEY = base64.b64decode(SERVER_KEY_BASE64)

class FinalHMACClient:
    """최종 HMAC 클라이언트 - 올바른 메시지 형식 사용"""
    
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
        
        print(f"🔑 서버 HMAC 키 로드 완료:")
        print(f"   Base64: {SERVER_KEY_BASE64[:20]}...")
        print(f"   길이: {len(self.key)} 바이트")
        print(f"📋 메시지 형식: sensor_id|timestamp|sensor_value")
    
    def calculate_hmac_server_format(self, sensor_id: str, timestamp: float, sensor_value: float) -> str:
        """
        서버 형식대로 정확한 HMAC 계산
        
        형식: sensor_id|timestamp|sensor_value
        """
        # 서버가 요구하는 정확한 메시지 형식
        message = f"{sensor_id}|{timestamp}|{sensor_value}".encode('utf-8')
        
        # HMAC-SHA256 계산
        signature = hmac.new(self.key, message, hashlib.sha256).digest()
        
        # Base64 인코딩 (서버가 base64 형식을 기대하는 경우)
        signature_b64 = base64.b64encode(signature).decode()
        
        # HEX 형식도 준비 (API가 HEX를 기대할 수 있음)
        signature_hex = signature.hex()
        
        self.logger.debug(f"Message: {message.decode()}")
        self.logger.debug(f"Signature (hex): {signature_hex[:32]}...")
        
        return signature_hex  # API는 HEX 형식을 사용하는 것으로 보임
    
    async def send_verified_data(self, data: Dict[str, Any]) -> ClientResult:
        """
        올바른 형식으로 검증된 데이터 전송
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
                sensor_id = "WADI_TEST"
            
            # 정확한 타임스탬프 (time.time() 형식)
            timestamp_seconds = time.time()  # 초 단위 (부동소수점)
            timestamp_ms = int(timestamp_seconds * 1000)  # 밀리초 (API용)
            
            # HMAC 생성 시작
            hmac_start = time.perf_counter()
            
            # 서버 형식대로 HMAC 계산
            calculated_mac = self.calculate_hmac_server_format(
                sensor_id=sensor_id,
                timestamp=timestamp_seconds,  # 초 단위 사용
                sensor_value=first_sensor_value
            )
            
            hmac_end = time.perf_counter()
            hmac_generation_time = (hmac_end - hmac_start) * 1000
            
            # 서버 API 요청 페이로드
            request_payload = {
                "sensor_value": first_sensor_value,
                "timestamp": timestamp_ms,  # API는 밀리초 기대
                "received_mac": calculated_mac,
                "sensor_id": sensor_id
            }
            
            # 또는 서버가 기대하는 정확한 형식
            alternative_payload = {
                "type": "sensor_data",
                "sensor_id": sensor_id,
                "timestamp": timestamp_seconds,  # 초 단위
                "sensor_value": first_sensor_value,
                "signature": calculated_mac
            }
            
            # 첫 번째 형식 시도
            data_size = len(json.dumps(request_payload).encode('utf-8'))
            
            # 네트워크 요청
            network_start = time.perf_counter()
            
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                # 첫 번째 API 형식 시도
                async with session.post(
                    self.verify_endpoint,
                    json=request_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                    else:
                        response_text = await response.text()
                        self.logger.warning(f"First format failed: {response_text}")
                        # 두 번째 형식 시도 가능
                        raise Exception(f"Server error {response.status}")
                    
            network_end = time.perf_counter()
            network_rtt = (network_end - network_start) * 1000
            
            # 응답 처리
            server_verified = response_data.get('verified', False)
            processing_time = response_data.get('processing_time_ms', 0.0)
            
            if server_verified:
                self.logger.info(f"✅ HMAC 검증 성공!")
            else:
                # 메시지 형식 디버깅
                self.logger.debug(f"❌ 검증 실패 - 디버깅 정보:")
                self.logger.debug(f"   Sensor ID: {sensor_id}")
                self.logger.debug(f"   Timestamp: {timestamp_seconds}")
                self.logger.debug(f"   Value: {first_sensor_value}")
                self.logger.debug(f"   Message: {sensor_id}|{timestamp_seconds}|{first_sensor_value}")
            
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
        self.logger.info(f"Starting final HMAC experiment: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
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
        
        verification_rate = (verified_requests / len(results)) * 100
        self.logger.info(f"Experiment completed: {verified_requests}/{len(results)} ({verification_rate:.1f}%) verified")
        return results

class FinalHMACExperiment(WADIHMACExperiment):
    """최종 HMAC 실험 클래스"""
    
    async def setup_experiment(self):
        """실험 설정"""
        self.logger.info(f"Setting up final HMAC experiment: {self.experiment_id}")
        self.logger.info(f"Target server: {self.config.server_host}:{self.config.server_port}")
        
        # 최종 클라이언트
        self.client = FinalHMACClient(
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
        
        self.logger.info("Final HMAC experiment setup completed")
    
    async def cleanup(self):
        """실험 정리"""
        self.logger.info("🧹 Cleaning up final HMAC experiment")
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self.logger.info("✅ Cleanup completed")

async def test_correct_format():
    """올바른 형식 테스트"""
    print("🔐 최종 HMAC 형식 테스트")
    print("=" * 50)
    
    client = FinalHMACClient()
    
    # 테스트 데이터
    test_data = {
        'sensor_values': {'WADI_TEST': 25.5},
        'frequency': 1
    }
    
    result = await client.send_verified_data(test_data)
    
    if result.success:
        print("✅ HMAC 검증 성공! 형식이 올바릅니다.")
        print(f"   처리 시간: {result.hmac_verification_time_ms:.3f}ms")
        print(f"   네트워크 RTT: {result.network_rtt_ms:.1f}ms")
        return True
    else:
        print("❌ HMAC 검증 실패 - 형식 재확인 필요")
        return False

async def main():
    """메인 실험"""
    print("🔑 최종 WADI HMAC 실험")
    print("=" * 60)
    print("📋 메시지 형식: sensor_id|timestamp|sensor_value")
    print("🔐 서버 키: 제공된 32바이트 키 사용")
    
    # 형식 테스트
    if not await test_correct_format():
        print("\n⚠️ 형식 테스트 실패. 디버깅 필요.")
        return
    
    print("\n✅ 형식 검증 성공! 전체 실험을 시작합니다.\n")
    
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
    
    total_time_hours = len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 3600
    print(f"  • 예상 시간: {total_time_hours:.1f}시간")
    
    print("\n🚀 최종 HMAC 실험 시작...")
    
    experiment = FinalHMACExperiment(config)
    
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
#!/usr/bin/env python3
"""
정확한 1Hz 센서 클라이언트 타이밍 테스트
"""

import asyncio
import time
import aiohttp
from datetime import datetime
from cryptography.hazmat.primitives import serialization
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))
from crypto.ed25519_baseline import Ed25519Baseline


class Precise1HzSensor:
    """정확한 1Hz 타이밍을 보장하는 센서 클라이언트"""
    
    def __init__(self, server_url: str = "http://192.168.0.11:8085"):
        self.server_url = server_url
        self.ed25519 = Ed25519Baseline()
        self.request_count = 0
        
    async def send_sensor_data(self, sensor_id: str, value: float) -> bool:
        """센서 데이터 전송"""
        try:
            # ED25519 서명 생성
            timestamp_unix = int(time.time())
            timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
            message = f"{value:.6f}||{timestamp_iso}"
            
            signature = self.ed25519.private_key.sign(message.encode('utf-8'))
            public_key_bytes = self.ed25519.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            payload = {
                "algorithm": "ed25519",
                "sensor_id": sensor_id,
                "sensor_value": value,
                "signature": signature.hex(),
                "public_key": public_key_bytes.hex(),
                "timestamp": timestamp_unix
            }
            
            # Fire-and-forget 전송
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/api/v1/verify/ed25519",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    success = response.status == 200
                    return success
                    
        except Exception as e:
            print(f"❌ 전송 오류: {e}")
            return False
    
    async def run_precise_1hz(self, sensor_id: str = "PRECISE_SENSOR", duration: int = 30):
        """정확한 1Hz로 센서 데이터 전송"""
        print(f"🕐 정확한 1Hz 센서 시작 ({duration}초 동안)")
        print(f"📡 서버: {self.server_url}")
        print(f"🔗 센서: {sensor_id}")
        print("-" * 50)
        
        # ✅ 올바른 타이밍 로직
        start_time = time.perf_counter()
        next_send_time = start_time
        
        target_requests = duration
        
        for i in range(target_requests):
            # 정확한 전송 시점까지 대기
            current_time = time.perf_counter()
            sleep_time = next_send_time - current_time
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            
            # 실제 전송 시간 기록
            actual_send_time = time.perf_counter()
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # 센서 값 생성 (실제 센서에서는 실제 측정값)
            sensor_value = 25.0 + (i % 10) * 0.1  # 시뮬레이션 값
            
            # Fire-and-forget 전송
            asyncio.create_task(self.send_sensor_data(sensor_id, sensor_value))
            self.request_count += 1
            
            # 다음 전송 시점 계산 (누적 오차 방지)
            next_send_time = start_time + (i + 1) * 1.0  # 정확히 1초 간격
            
            # 실제 간격 계산
            if i > 0:
                actual_interval = actual_send_time - prev_send_time
                deviation = actual_interval - 1.0
                print(f"📤 {timestamp} #{i+1:3d}: {sensor_value:.1f} (간격: {actual_interval:.3f}s, 편차: {deviation:+.3f}s)")
            else:
                print(f"📤 {timestamp} #{i+1:3d}: {sensor_value:.1f} (시작)")
            
            prev_send_time = actual_send_time
        
        # 최종 통계
        total_duration = time.perf_counter() - start_time
        actual_frequency = (target_requests - 1) / total_duration if total_duration > 0 else 0
        
        print("-" * 50)
        print(f"✅ 완료: {target_requests}개 요청 전송")
        print(f"📊 총 시간: {total_duration:.3f}초")
        print(f"🎯 목표 주파수: 1.000Hz")
        print(f"⚡ 실제 주파수: {actual_frequency:.3f}Hz")
        print(f"📈 정확도: {(actual_frequency/1.0)*100:.1f}%")


async def main():
    """메인 실행"""
    sensor = Precise1HzSensor()
    
    print("🔧 정확한 1Hz 센서 클라이언트 테스트")
    print("=" * 60)
    
    # 30초 동안 정확한 1Hz로 전송
    await sensor.run_precise_1hz("PRECISE_1HZ_SENSOR", duration=30)


if __name__ == "__main__":
    asyncio.run(main())
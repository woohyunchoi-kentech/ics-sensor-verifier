#!/usr/bin/env python3
"""
진짜 정확한 1Hz 센서 클라이언트 (동기 방식)
"""

import time
import requests
from datetime import datetime
from cryptography.hazmat.primitives import serialization
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))
from crypto.ed25519_baseline import Ed25519Baseline


class TrueFixed1HzSensor:
    """진짜 정확한 1Hz 타이밍을 보장하는 센서 클라이언트 (동기 방식)"""
    
    def __init__(self, server_url: str = "http://192.168.0.11:8085"):
        self.server_url = server_url
        self.ed25519 = Ed25519Baseline()
        self.session = requests.Session()  # 연결 재사용
        
    def send_sensor_data_sync(self, sensor_id: str, value: float) -> bool:
        """동기 방식으로 센서 데이터 즉시 전송"""
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
            
            # 즉시 동기 전송 (버퍼링 없음)
            response = self.session.post(
                f"{self.server_url}/api/v1/verify/ed25519",
                json=payload,
                timeout=2.0  # 짧은 타임아웃
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ 전송 오류: {e}")
            return False
    
    def run_true_1hz(self, sensor_id: str = "FIXED_SENSOR", duration: int = 20):
        """진짜 정확한 1Hz로 센서 데이터 전송 (동기)"""
        print(f"🕐 진짜 정확한 1Hz 센서 시작 ({duration}초 동안)")
        print(f"📡 서버: {self.server_url}")
        print(f"🔗 센서: {sensor_id}")
        print(f"🔧 방식: 동기 전송 (즉시)")
        print("-" * 60)
        
        # 절대 시점 기준 타이밍
        start_time = time.perf_counter()
        
        for i in range(duration):
            # 정확한 전송 시점 계산
            target_time = start_time + i * 1.0
            current_time = time.perf_counter()
            
            # 다음 전송 시간까지 대기
            sleep_time = target_time - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)  # 동기 sleep
            
            # 실제 전송 시간 기록
            actual_send_time = time.perf_counter()
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # 센서 값 생성
            sensor_value = 30.0 + (i % 5) * 0.2
            
            # 즉시 동기 전송
            success = self.send_sensor_data_sync(sensor_id, sensor_value)
            status = "✅" if success else "❌"
            
            # 실제 간격 계산
            if i > 0:
                actual_interval = actual_send_time - prev_send_time
                deviation = actual_interval - 1.0
                print(f"{status} {timestamp} #{i+1:2d}: {sensor_value:.1f} (간격: {actual_interval:.3f}s, 편차: {deviation:+.3f}s)")
            else:
                print(f"{status} {timestamp} #{i+1:2d}: {sensor_value:.1f} (시작)")
            
            prev_send_time = actual_send_time
        
        # 최종 통계
        total_duration = time.perf_counter() - start_time
        actual_frequency = (duration - 1) / total_duration if total_duration > 0 else 0
        
        print("-" * 60)
        print(f"✅ 완료: {duration}개 요청 전송")
        print(f"📊 총 시간: {total_duration:.3f}초")
        print(f"🎯 목표 주파수: 1.000Hz")
        print(f"⚡ 실제 주파수: {actual_frequency:.3f}Hz")
        print(f"📈 정확도: {(actual_frequency/1.0)*100:.1f}%")


def main():
    """메인 실행"""
    sensor = TrueFixed1HzSensor()
    
    print("🔧 진짜 정확한 1Hz 센서 클라이언트 (동기)")
    print("=" * 70)
    
    # 20초 동안 정확한 1Hz로 전송
    sensor.run_true_1hz("TRUE_1HZ_SENSOR", duration=20)


if __name__ == "__main__":
    main()
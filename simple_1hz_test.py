#!/usr/bin/env python3
"""
간단하고 정확한 1Hz 센서 클라이언트 (고정 간격)
"""

import time
import requests
from datetime import datetime
import threading
from cryptography.hazmat.primitives import serialization
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))
from crypto.ed25519_baseline import Ed25519Baseline


class Simple1HzSensor:
    """간단한 1Hz 센서 (고정 간격)"""
    
    def __init__(self, server_url: str = "http://192.168.0.11:8085"):
        self.server_url = server_url
        self.ed25519 = Ed25519Baseline()
        self.session = requests.Session()
        self.running = False
        self.count = 0
        
    def send_data(self, sensor_id: str, value: float) -> bool:
        """데이터 전송"""
        try:
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
            
            response = self.session.post(
                f"{self.server_url}/api/v1/verify/ed25519",
                json=payload,
                timeout=1.0
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            return False
    
    def timer_callback(self):
        """정확히 1초마다 호출되는 콜백"""
        self.count += 1
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # 센서 값 생성
        value = 35.0 + (self.count % 3) * 0.5
        
        # 즉시 전송
        success = self.send_data("SIMPLE_1HZ", value)
        status = "✅" if success else "❌"
        
        print(f"{status} {timestamp} #{self.count:2d}: {value:.1f}")
        
        if self.count < 15:  # 15개만 전송
            # 정확히 1초 후 다시 실행
            timer = threading.Timer(1.0, self.timer_callback)
            timer.start()
        else:
            print("✅ 완료: 15개 전송")
    
    def start(self):
        """시작"""
        print("🕐 간단한 1Hz 센서 시작 (고정 간격)")
        print(f"📡 서버: {self.server_url}")
        print("-" * 50)
        
        self.running = True
        self.count = 0
        
        # 첫 번째 전송
        self.timer_callback()


def main():
    """메인"""
    sensor = Simple1HzSensor()
    sensor.start()
    
    # 20초 대기 (15개 전송 완료 대기)
    time.sleep(20)


if __name__ == "__main__":
    main()
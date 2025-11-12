#!/usr/bin/env python3
"""
서버 키를 사용한 WADI HMAC 실험
================================

서버의 실제 HMAC 키를 사용하여 100% 검증 성공률 달성
"""

import asyncio
import hmac
import hashlib
import json
import time
from datetime import datetime

async def test_with_server_key():
    """서버 키로 HMAC 테스트"""
    
    # 서버 관리자로부터 받은 키를 여기에 입력
    SERVER_KEY = b"여기에_서버_관리자가_제공한_41바이트_키_입력"  # 41바이트
    
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    # 테스트 데이터
    sensor_value = 25.5
    timestamp = int(time.time() * 1000)
    sensor_id = "WADI_SENSOR_001"
    
    # 서버와 동일한 방식으로 HMAC 생성
    # 서버가 어떤 메시지 형식을 사용하는지 확인 필요
    message_formats = [
        f"{sensor_value}:{timestamp}",
        f"{sensor_id}:{sensor_value}:{timestamp}",
        json.dumps({"sensor_value": sensor_value, "timestamp": timestamp})
    ]
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for msg_format in message_formats:
            # HMAC 계산
            message = msg_format.encode('utf-8')
            calculated_mac = hmac.new(SERVER_KEY, message, hashlib.sha256).hexdigest()
            
            # 서버에 전송
            payload = {
                "sensor_value": sensor_value,
                "timestamp": timestamp,
                "received_mac": calculated_mac,
                "sensor_id": sensor_id
            }
            
            print(f"\n🔐 테스트 메시지 형식: {msg_format[:50]}")
            print(f"   계산된 MAC: {calculated_mac[:32]}...")
            
            async with session.post(server_url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    verified = result.get('verified', False)
                    
                    if verified:
                        print(f"✅ 성공! 올바른 키와 메시지 형식!")
                        print(f"   처리 시간: {result.get('processing_time_ms')}ms")
                        return True
                    else:
                        print(f"❌ 검증 실패")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_with_server_key())
    if success:
        print("\n🎉 서버 키 검증 성공! 이제 전체 실험을 실행할 수 있습니다.")
    else:
        print("\n❌ 키 또는 메시지 형식이 일치하지 않습니다.")
#!/usr/bin/env python3
"""
서버 HMAC 메시지 형식 테스트
"""

import asyncio
import aiohttp
import hmac
import hashlib
import json
import time

# 서버 키
SERVER_KEY = bytes.fromhex("8e56c053c3f2635c1356f4018191ffa9c0c8c23376e2c96e0820ce1095c9b02b")

async def test_message_formats():
    """다양한 메시지 형식 테스트"""
    
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    # 테스트 데이터
    sensor_value = 25.5
    timestamp = int(time.time() * 1000)
    sensor_id = "WADI_TEST_001"
    
    # 가능한 메시지 형식들
    test_formats = [
        # 형식 1: value:timestamp
        (f"{sensor_value}:{timestamp}", "value:timestamp"),
        
        # 형식 2: sensor_id:value:timestamp  
        (f"{sensor_id}:{sensor_value}:{timestamp}", "sensor_id:value:timestamp"),
        
        # 형식 3: timestamp:value
        (f"{timestamp}:{sensor_value}", "timestamp:value"),
        
        # 형식 4: JSON 문자열
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp}), "JSON"),
        
        # 형식 5: JSON (정렬된 키)
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp}, sort_keys=True), "JSON (sorted)"),
        
        # 형식 6: value만
        (str(sensor_value), "value only"),
        
        # 형식 7: timestamp만
        (str(timestamp), "timestamp only"),
        
        # 형식 8: sensor_id:value
        (f"{sensor_id}:{sensor_value}", "sensor_id:value"),
        
        # 형식 9: URL 인코딩 형식
        (f"sensor_value={sensor_value}&timestamp={timestamp}", "URL encoded"),
        
        # 형식 10: 공백 구분
        (f"{sensor_value} {timestamp}", "space separated"),
        
        # 형식 11: 정수 타임스탬프 (초 단위)
        (f"{sensor_value}:{timestamp//1000}", "value:timestamp_seconds"),
        
        # 형식 12: 쉼표 구분
        (f"{sensor_value},{timestamp}", "comma separated"),
    ]
    
    print("🔍 서버 HMAC 메시지 형식 테스트")
    print("=" * 60)
    print(f"🔑 키 길이: {len(SERVER_KEY)} 바이트")
    print(f"📊 테스트 데이터:")
    print(f"   sensor_value: {sensor_value}")
    print(f"   timestamp: {timestamp}")
    print(f"   sensor_id: {sensor_id}")
    print()
    
    async with aiohttp.ClientSession() as session:
        for i, (message_str, description) in enumerate(test_formats, 1):
            print(f"\n테스트 {i}: {description}")
            print(f"   메시지: {message_str[:50]}...")
            
            # HMAC 계산
            message_bytes = message_str.encode('utf-8')
            calculated_mac = hmac.new(SERVER_KEY, message_bytes, hashlib.sha256).hexdigest()
            print(f"   MAC: {calculated_mac[:32]}...")
            
            # 서버에 전송
            payload = {
                "sensor_value": sensor_value,
                "timestamp": timestamp,
                "received_mac": calculated_mac,
                "sensor_id": sensor_id
            }
            
            try:
                async with session.post(server_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        verified = result.get('verified', False)
                        
                        if verified:
                            print(f"   ✅ 성공! 올바른 메시지 형식입니다!")
                            print(f"   처리 시간: {result.get('processing_time_ms'):.3f}ms")
                            print(f"\n🎉 정답: {description}")
                            print(f"   메시지 형식: {message_str}")
                            return message_str, description
                        else:
                            print(f"   ❌ 검증 실패")
                    else:
                        print(f"   ❌ 서버 오류: {response.status}")
                        
            except Exception as e:
                print(f"   ❌ 요청 실패: {e}")
    
    print("\n😞 올바른 메시지 형식을 찾지 못했습니다.")
    print("서버 관리자에게 정확한 메시지 형식을 문의하세요.")
    
    return None, None

if __name__ == "__main__":
    message_format, description = asyncio.run(test_message_formats())
    
    if message_format:
        print(f"\n✅ 서버가 사용하는 메시지 형식: {description}")
        print(f"📝 실제 형식: {message_format}")
    else:
        print("\n❌ 메시지 형식을 찾지 못했습니다.")
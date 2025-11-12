#!/usr/bin/env python3
"""
서버 HMAC 메시지 형식 발견
========================

서버가 실제 사용하는 메시지 형식을 체계적으로 찾아냄
"""

import asyncio
import aiohttp
import hmac
import hashlib
import base64
import time
import json

# 서버 키
SERVER_KEY = base64.b64decode("jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs=")

async def test_message_formats():
    """체계적인 메시지 형식 테스트"""
    
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    # 테스트 데이터
    sensor_value = 2.45  # 사용자가 제공한 예시값
    timestamp_ms = int(time.time() * 1000)
    timestamp_s = int(time.time())
    
    print(f"🔍 서버 HMAC 메시지 형식 체계적 발견")
    print(f"=" * 60)
    print(f"🔑 키: {len(SERVER_KEY)} 바이트")
    print(f"📊 테스트 데이터:")
    print(f"   sensor_value: {sensor_value}")
    print(f"   timestamp_ms: {timestamp_ms}")
    print(f"   timestamp_s: {timestamp_s}")
    
    # 가능한 메시지 형식들을 체계적으로 테스트
    message_formats = [
        # 사용자가 언급한 형식들
        (f"{sensor_value}:{timestamp_s}", "value:timestamp_seconds"),
        (f"{sensor_value}:{timestamp_ms}", "value:timestamp_ms"),
        
        # 일반적인 형식들
        (f"{timestamp_s}:{sensor_value}", "timestamp_s:value"),
        (f"{timestamp_ms}:{sensor_value}", "timestamp_ms:value"),
        
        # JSON 기반
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp_s}), "JSON_seconds"),
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp_ms}), "JSON_ms"),
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp_s}, separators=(',', ':')), "JSON_compact_s"),
        (json.dumps({"sensor_value": sensor_value, "timestamp": timestamp_ms}, separators=(',', ':')), "JSON_compact_ms"),
        
        # 다른 구분자들
        (f"{sensor_value}|{timestamp_s}", "value|timestamp_s"),
        (f"{sensor_value}|{timestamp_ms}", "value|timestamp_ms"),
        (f"{sensor_value},{timestamp_s}", "value,timestamp_s"),
        (f"{sensor_value},{timestamp_ms}", "value,timestamp_ms"),
        (f"{sensor_value} {timestamp_s}", "value timestamp_s"),
        (f"{sensor_value} {timestamp_ms}", "value timestamp_ms"),
        
        # 값만 또는 타임스탬프만
        (str(sensor_value), "value_only"),
        (str(timestamp_s), "timestamp_s_only"),
        (str(timestamp_ms), "timestamp_ms_only"),
        
        # 순서 바꾼 것들
        (f"{timestamp_s}|{sensor_value}", "timestamp_s|value"),
        (f"{timestamp_ms}|{sensor_value}", "timestamp_ms|value"),
    ]
    
    async with aiohttp.ClientSession() as session:
        success_count = 0
        
        for i, (message_str, description) in enumerate(message_formats, 1):
            print(f"\n테스트 {i:2d}: {description}")
            print(f"    메시지: '{message_str}'")
            
            try:
                # HMAC 계산
                message_bytes = message_str.encode('utf-8')
                calculated_mac = hmac.new(SERVER_KEY, message_bytes, hashlib.sha256).hexdigest()
                
                # 서버 요청
                payload = {
                    "sensor_value": sensor_value,
                    "timestamp": timestamp_ms,  # API는 밀리초 기대
                    "received_mac": calculated_mac
                }
                
                async with session.post(server_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        verified = result.get('verified', False)
                        
                        if verified:
                            print(f"    ✅ 성공! 올바른 메시지 형식 발견!")
                            print(f"    📝 메시지 형식: '{message_str}'")
                            print(f"    🔐 HMAC: {calculated_mac[:32]}...")
                            print(f"    📋 응답: {json.dumps(result, indent=4)}")
                            success_count += 1
                            
                            # 성공한 경우를 별도로 표시하고 계속 진행
                            print(f"    🎉 성공한 형식: {description}")
                        else:
                            print(f"    ❌ 검증 실패")
                            if result.get('error_message'):
                                print(f"       오류: {result['error_message']}")
                    else:
                        error_text = await response.text()
                        print(f"    ❌ HTTP {response.status}: {error_text[:100]}...")
                        
            except Exception as e:
                print(f"    ❌ 요청 실패: {str(e)}")
    
    print(f"\n📊 테스트 완료: {success_count}개 성공 형식 발견")
    
    if success_count == 0:
        print(f"\n🔍 추가 디버깅을 위한 상세 정보:")
        print(f"   서버 키 (hex): {SERVER_KEY.hex()}")
        print(f"   서버 키 (base64): {base64.b64encode(SERVER_KEY).decode()}")
        
        # 기본 연결 테스트
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://192.168.0.11:8085/health") as response:
                    health = await response.json()
                    print(f"   서버 상태: {health}")
        except:
            print(f"   서버 연결 실패")

if __name__ == "__main__":
    asyncio.run(test_message_formats())
#!/usr/bin/env python3
"""
서버 제공 정확한 형식으로 HMAC 테스트
===================================

서버 관리자가 제공한 정확한 스펙으로 테스트
"""

import asyncio
import aiohttp
import hmac
import hashlib
import json

async def test_server_specification():
    """서버 제공 스펙으로 테스트"""
    
    # 서버 제공 정확한 정보
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    key = b"default-insecure-key-change-in-production"  # 41바이트
    
    # 테스트 데이터 (서버 제공 예시)
    sensor_id = "HAI_P_001"
    timestamp = 1756367160
    sensor_value = 2.45
    
    print(f"🔐 서버 정확한 스펙 테스트")
    print(f"=" * 50)
    print(f"🔑 키: {key.decode()} ({len(key)} 바이트)")
    print(f"📊 테스트 데이터:")
    print(f"   sensor_id: {sensor_id}")
    print(f"   timestamp: {timestamp}")
    print(f"   sensor_value: {sensor_value}")
    
    # HMAC 계산 (서버 제공 방식)
    message = f"{sensor_id}|{timestamp}|{sensor_value:.6f}"
    print(f"📝 메시지: '{message}'")
    
    mac = hmac.new(key, message.encode('utf-8'), hashlib.sha256)
    hex_mac = mac.hexdigest()
    print(f"🔐 계산된 HMAC: {hex_mac}")
    print(f"🎯 예상 HMAC:   ee8d5e21e08524c6b50813f9d8e4df900df198641a0d169a85cab79938992bca")
    print(f"✅ HMAC 일치: {hex_mac == 'ee8d5e21e08524c6b50813f9d8e4df900df198641a0d169a85cab79938992bca'}")
    
    # 서버 요청
    payload = {
        "sensor_value": sensor_value,
        "timestamp": timestamp,
        "received_mac": hex_mac,
        "sensor_id": sensor_id
    }
    
    print(f"\n📋 요청 페이로드:")
    print(json.dumps(payload, indent=2))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(server_url, json=payload, timeout=10) as response:
                print(f"\n🌐 서버 응답:")
                print(f"   상태: HTTP {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"   내용: {json.dumps(result, indent=2)}")
                    
                    if result.get('verified', False):
                        print(f"\n🎉 HMAC 검증 성공!")
                        print(f"   처리 시간: {result.get('processing_time_ms', 0):.3f}ms")
                        return True
                    else:
                        print(f"\n❌ HMAC 검증 실패")
                        return False
                else:
                    error_text = await response.text()
                    print(f"   오류: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ 요청 실패: {str(e)}")
        return False

async def test_with_wadi_sensor():
    """WADI 센서 ID로 테스트"""
    
    # WADI 형식 센서 ID로 테스트
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    key = b"default-insecure-key-change-in-production"
    
    # WADI 스타일 센서 ID
    sensor_id = "WADI_001"  # 또는 실제 WADI 센서 ID
    timestamp = int(1756367200)  # 현재 시간
    sensor_value = 25.5
    
    print(f"\n🌊 WADI 센서로 테스트")
    print(f"-" * 30)
    print(f"📊 WADI 테스트 데이터:")
    print(f"   sensor_id: {sensor_id}")
    print(f"   timestamp: {timestamp}")
    print(f"   sensor_value: {sensor_value}")
    
    # HMAC 계산
    message = f"{sensor_id}|{timestamp}|{sensor_value:.6f}"
    print(f"📝 메시지: '{message}'")
    
    mac = hmac.new(key, message.encode('utf-8'), hashlib.sha256)
    hex_mac = mac.hexdigest()
    print(f"🔐 HMAC: {hex_mac}")
    
    # 서버 요청
    payload = {
        "sensor_value": sensor_value,
        "timestamp": timestamp,
        "received_mac": hex_mac,
        "sensor_id": sensor_id
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(server_url, json=payload, timeout=10) as response:
                print(f"🌐 응답: HTTP {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    verified = result.get('verified', False)
                    
                    if verified:
                        print(f"✅ WADI 센서 검증 성공!")
                        print(f"   처리 시간: {result.get('processing_time_ms', 0):.3f}ms")
                        return True
                    else:
                        print(f"❌ WADI 센서 검증 실패")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ 오류: {error_text[:100]}")
                    return False
                    
    except Exception as e:
        print(f"❌ 요청 실패: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 서버 스펙 검증 테스트 시작")
    
    # 1. 서버 제공 예시로 테스트
    success1 = asyncio.run(test_server_specification())
    
    # 2. WADI 센서로 테스트
    success2 = asyncio.run(test_with_wadi_sensor())
    
    if success1 and success2:
        print(f"\n🎉 모든 테스트 성공! WADI 실험 준비 완료!")
    elif success1:
        print(f"\n✅ 서버 스펙 확인됨. WADI 실험 진행 가능!")
    else:
        print(f"\n❌ 테스트 실패. 스펙 재확인 필요.")
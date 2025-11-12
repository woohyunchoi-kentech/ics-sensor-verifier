#!/usr/bin/env python3
"""
외부 서버 연결 테스트
"""

import asyncio
import json
import time
import aiohttp
from hmac_authenticator import HMACAuthenticator

async def test_external_server():
    """외부 서버 테스트"""
    server_host = "192.168.0.11"
    server_port = 8085
    
    print(f"🌐 외부 서버 테스트: {server_host}:{server_port}")
    
    # 서버 상태 확인
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(f"http://{server_host}:{server_port}/") as response:
                if response.status == 200:
                    server_info = await response.json()
                    print("✅ 서버 연결 성공!")
                    print(f"📋 서버 정보: {server_info['service']} v{server_info['version']}")
                    print(f"🔧 지원 알고리즘: {server_info['supported_algorithms']}")
                else:
                    print(f"❌ 서버 연결 실패: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ 서버 연결 오류: {str(e)}")
        return False
    
    # HMAC 테스트
    print("\n🔒 HMAC 검증 테스트...")
    try:
        authenticator = HMACAuthenticator()
        
        test_data = {
            'sensor_id': 'WADI_TEST_001',
            'value': 7.15,
            'unit': 'pH',
            'timestamp': '2025-08-28T15:30:00'
        }
        
        # 인증 메시지 생성
        authenticated_msg = authenticator.create_authenticated_message(test_data)
        
        # 외부 서버 API 형식에 맞춤
        request_payload = {
            "sensor_value": test_data['value'],
            "timestamp": int(time.time() * 1000),  # 밀리초 타임스탬프
            "received_mac": authenticated_msg["hmac"],
            "sensor_id": test_data['sensor_id']
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                f"http://{server_host}:{server_port}/api/v1/verify/hmac",
                json=request_payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ HMAC 검증 성공!")
                    print(f"📊 검증 결과: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ HMAC 검증 실패: HTTP {response.status}")
                    print(f"📄 응답: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ HMAC 테스트 오류: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_external_server())
    if success:
        print("\n🎉 외부 서버 테스트 완료! 실험 준비됨")
    else:
        print("\n💥 외부 서버 테스트 실패")
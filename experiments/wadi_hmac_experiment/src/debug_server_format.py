#!/usr/bin/env python3
"""
서버 요청 형식 디버깅
"""

import asyncio
import aiohttp
import json
import time
import hmac
import hashlib
import base64

# 서버 키
SERVER_KEY = base64.b64decode("jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs=")

async def debug_server_requests():
    """다양한 API 형식과 요청 방식 테스트"""
    
    server_host = "192.168.0.11"
    server_port = 8085
    
    # 테스트 데이터
    sensor_id = "WADI_TEST"
    timestamp_seconds = time.time()
    sensor_value = 25.5
    
    print("🔍 서버 요청 형식 디버깅")
    print("=" * 60)
    print(f"🔑 키 길이: {len(SERVER_KEY)} 바이트")
    print(f"📊 테스트 데이터:")
    print(f"   sensor_id: {sensor_id}")
    print(f"   timestamp: {timestamp_seconds}")
    print(f"   sensor_value: {sensor_value}")
    
    # 1. 올바른 메시지 형식으로 HMAC 계산
    message = f"{sensor_id}|{timestamp_seconds}|{sensor_value}".encode('utf-8')
    signature = hmac.new(SERVER_KEY, message, hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode()
    signature_hex = signature.hex()
    
    print(f"\n📝 생성된 HMAC:")
    print(f"   메시지: {message.decode()}")
    print(f"   Base64: {signature_b64[:32]}...")
    print(f"   HEX: {signature_hex[:32]}...")
    
    # 2. 다양한 API 엔드포인트 테스트
    endpoints_to_test = [
        ("/api/v1/verify/hmac", "현재 사용 중인 HMAC API"),
        ("/api/v1/verify", "일반 검증 API"),
        ("/verify", "단순 검증 엔드포인트"),
        ("/hmac", "HMAC 전용 엔드포인트"),
        ("/api/sensor", "센서 데이터 API"),
    ]
    
    # 3. 다양한 요청 형식 테스트
    request_formats = [
        # 형식 1: 현재 API 형식 (HEX)
        {
            "name": "Current API (HEX)",
            "data": {
                "sensor_value": sensor_value,
                "timestamp": int(timestamp_seconds * 1000),  # 밀리초
                "received_mac": signature_hex,
                "sensor_id": sensor_id
            }
        },
        # 형식 2: Base64 시그니처
        {
            "name": "Current API (Base64)",
            "data": {
                "sensor_value": sensor_value,
                "timestamp": int(timestamp_seconds * 1000),
                "received_mac": signature_b64,
                "sensor_id": sensor_id
            }
        },
        # 형식 3: 서버가 제시한 형식
        {
            "name": "Server Format",
            "data": {
                "type": "sensor_data",
                "sensor_id": sensor_id,
                "timestamp": timestamp_seconds,  # 초 단위
                "sensor_value": sensor_value,
                "signature": signature_b64
            }
        },
        # 형식 4: 서버 형식 (HEX)
        {
            "name": "Server Format (HEX)",
            "data": {
                "type": "sensor_data", 
                "sensor_id": sensor_id,
                "timestamp": timestamp_seconds,
                "sensor_value": sensor_value,
                "signature": signature_hex
            }
        },
        # 형식 5: 간단한 형식
        {
            "name": "Simple Format",
            "data": {
                "sensor_id": sensor_id,
                "timestamp": timestamp_seconds,
                "value": sensor_value,
                "hmac": signature_hex
            }
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint, description in endpoints_to_test:
            url = f"http://{server_host}:{server_port}{endpoint}"
            print(f"\n🌐 테스트 엔드포인트: {endpoint}")
            print(f"   설명: {description}")
            
            for req_format in request_formats:
                print(f"\n   📋 {req_format['name']}")
                
                try:
                    async with session.post(url, json=req_format['data']) as response:
                        status = response.status
                        
                        if status == 200:
                            result = await response.json()
                            verified = result.get('verified', result.get('valid', False))
                            
                            if verified:
                                print(f"   ✅ 성공! 올바른 형식입니다!")
                                print(f"      URL: {url}")
                                print(f"      요청: {json.dumps(req_format['data'], indent=2)}")
                                print(f"      응답: {json.dumps(result, indent=2)}")
                                return url, req_format['data']
                            else:
                                print(f"   ❌ 검증 실패")
                                if 'error_message' in result:
                                    print(f"      오류: {result['error_message']}")
                        else:
                            response_text = await response.text()
                            if status == 404:
                                print(f"   ❓ 엔드포인트 없음 (404)")
                            else:
                                print(f"   ❌ HTTP {status}: {response_text[:100]}")
                            
                except Exception as e:
                    print(f"   ❌ 요청 실패: {str(e)}")
            
            # 엔드포인트별 구분선
            print("   " + "-" * 50)
    
    print("\n😞 성공적인 형식을 찾지 못했습니다.")
    return None, None

async def test_socket_connection():
    """TCP 소켓 연결 테스트"""
    print("\n🔌 TCP 소켓 연결 테스트")
    print("=" * 40)
    
    server_host = "192.168.0.11"
    server_port = 8085
    
    try:
        import socket
        
        # 소켓 연결 테스트
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((server_host, server_port))
            print(f"✅ TCP 연결 성공: {server_host}:{server_port}")
            
            # 간단한 데이터 전송 테스트
            test_message = b"Hello Server"
            sock.send(test_message)
            
            # 응답 대기 (타임아웃 설정)
            try:
                response = sock.recv(1024)
                print(f"📨 서버 응답: {response}")
            except socket.timeout:
                print("⏰ 서버 응답 대기 타임아웃")
                
    except Exception as e:
        print(f"❌ TCP 연결 실패: {str(e)}")

if __name__ == "__main__":
    success_url, success_data = asyncio.run(debug_server_requests())
    
    if success_url:
        print(f"\n🎉 성공한 형식 발견!")
        print(f"URL: {success_url}")
        print(f"데이터: {json.dumps(success_data, indent=2)}")
    else:
        print(f"\n🔌 HTTP API 실패. TCP 소켓 테스트 중...")
        asyncio.run(test_socket_connection())
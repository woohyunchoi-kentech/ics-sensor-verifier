#!/usr/bin/env python3
"""
다양한 키와 메시지 형식 조합 테스트
=================================

가능한 모든 키와 메시지 형식 조합을 테스트
"""

import asyncio
import aiohttp
import hmac
import hashlib
import base64
import time
import json

async def test_all_combinations():
    """모든 키와 메시지 형식 조합 테스트"""
    
    server_url = "http://192.168.0.11:8085/api/v1/verify/hmac"
    
    # 가능한 키들
    possible_keys = [
        # 제공된 Base64 키
        base64.b64decode("jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs="),
        
        # 이전 코드에서 사용된 HEX 키
        bytes.fromhex("8e56c053c3f2635c1356f4018191ffa9c0c8c23376e2c96e0820ce1095c9b02b"),
        
        # 기본 문자열 키들
        b'wadi_hmac_experiment_key_2025',
        
        # 서버 기본 키일 가능성
        b'server_hmac_key',
        b'hmac_key',
        b'wadi_key',
        b'test_key',
        
        # 32바이트 키들
        b'wadi_hmac_server_key_2025_secret',  # 32바이트
        
        # SHA256으로 생성된 키
        hashlib.sha256(b'wadi_hmac_key').digest(),
        hashlib.sha256(b'server_key').digest(),
    ]
    
    # 테스트 데이터
    sensor_value = 2.45
    timestamp_ms = int(time.time() * 1000)
    timestamp_s = int(time.time())
    
    # 핵심 메시지 형식들만 테스트
    message_formats = [
        (f"{sensor_value}:{timestamp_s}", "value:timestamp_s"),
        (f"{sensor_value}:{timestamp_ms}", "value:timestamp_ms"),
        (f"{timestamp_s}:{sensor_value}", "timestamp_s:value"),
        (f"{timestamp_ms}:{sensor_value}", "timestamp_ms:value"),
        (str(sensor_value), "value_only"),
        (str(timestamp_s), "timestamp_s_only"),
    ]
    
    print(f"🔍 키와 메시지 형식 조합 테스트")
    print(f"=" * 60)
    print(f"📊 테스트할 키: {len(possible_keys)}개")
    print(f"📊 테스트할 형식: {len(message_formats)}개")
    print(f"📊 총 조합: {len(possible_keys) * len(message_formats)}개")
    
    success_count = 0
    
    async with aiohttp.ClientSession() as session:
        for key_idx, key in enumerate(possible_keys):
            print(f"\n🔑 키 {key_idx+1}: {len(key)} 바이트")
            if len(key) <= 32:
                key_preview = key.hex() if isinstance(key, bytes) else str(key)
                print(f"    미리보기: {key_preview[:32]}...")
            
            for fmt_idx, (message_str, description) in enumerate(message_formats):
                try:
                    # HMAC 계산
                    message_bytes = message_str.encode('utf-8')
                    calculated_mac = hmac.new(key, message_bytes, hashlib.sha256).hexdigest()
                    
                    # 서버 요청
                    payload = {
                        "sensor_value": sensor_value,
                        "timestamp": timestamp_ms,
                        "received_mac": calculated_mac
                    }
                    
                    async with session.post(server_url, json=payload, timeout=5) as response:
                        if response.status == 200:
                            result = await response.json()
                            verified = result.get('verified', False)
                            
                            if verified:
                                print(f"    ✅ 성공! 키 {key_idx+1}, 형식: {description}")
                                print(f"       메시지: '{message_str}'")
                                print(f"       키: {key.hex() if len(key) <= 32 else str(key)}")
                                print(f"       HMAC: {calculated_mac}")
                                success_count += 1
                                
                                # 성공한 조합을 파일에 저장
                                with open("successful_combination.txt", "w") as f:
                                    f.write(f"Key: {key.hex()}\n")
                                    f.write(f"Message format: {description}\n")
                                    f.write(f"Message: {message_str}\n")
                                    f.write(f"HMAC: {calculated_mac}\n")
                                
                                return key, message_str, description  # 첫 번째 성공 시 종료
                            else:
                                # 간결한 실패 로그
                                if fmt_idx == 0:  # 첫 번째 형식에서만 표시
                                    print(f"    ❌ 키 {key_idx+1} 실패")
                        else:
                            if fmt_idx == 0:  # 첫 번째 형식에서만 표시
                                print(f"    ❌ 키 {key_idx+1} HTTP 오류: {response.status}")
                            
                except Exception as e:
                    if fmt_idx == 0:  # 첫 번째 형식에서만 표시
                        print(f"    ❌ 키 {key_idx+1} 예외: {str(e)[:50]}")
    
    print(f"\n📊 테스트 완료: {success_count}개 성공 조합")
    
    if success_count == 0:
        print(f"\n💡 가능한 원인:")
        print(f"   1. 서버가 다른 키를 사용하고 있음")
        print(f"   2. 메시지 형식이 완전히 다름")
        print(f"   3. API 엔드포인트가 다름")
        print(f"   4. 추가 파라미터가 필요함")
        
        # 다른 API 엔드포인트 시도
        print(f"\n🔄 다른 엔드포인트 시도...")
        endpoints = [
            "/api/v1/verify",
            "/verify/hmac", 
            "/hmac/verify",
            "/api/hmac",
        ]
        
        test_key = possible_keys[0]  # 첫 번째 키로 테스트
        test_message = f"{sensor_value}:{timestamp_s}"
        test_mac = hmac.new(test_key, test_message.encode(), hashlib.sha256).hexdigest()
        
        for endpoint in endpoints:
            test_url = f"http://192.168.0.11:8085{endpoint}"
            try:
                payload = {
                    "sensor_value": sensor_value,
                    "timestamp": timestamp_ms,
                    "received_mac": test_mac
                }
                
                async with session.post(test_url, json=payload, timeout=5) as response:
                    if response.status != 404:
                        print(f"   엔드포인트 {endpoint}: HTTP {response.status}")
                        if response.status == 200:
                            result = await response.json()
                            print(f"      응답: {result}")
                    
            except Exception as e:
                print(f"   엔드포인트 {endpoint}: 오류 {str(e)[:30]}")

if __name__ == "__main__":
    result = asyncio.run(test_all_combinations())
    if result:
        key, message, description = result
        print(f"\n🎉 성공한 조합 발견!")
        print(f"키: {key.hex()}")
        print(f"메시지 형식: {description}")
        print(f"메시지: {message}")
    else:
        print(f"\n😞 성공한 조합을 찾지 못했습니다.")
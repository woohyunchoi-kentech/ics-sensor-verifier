#!/usr/bin/env python3
"""
CKKS 서버 연결 테스트
==================
"""

import asyncio
import aiohttp
import json
import time

CKKS_SERVER_URL = "http://192.168.0.11:8085/api/v1/ckks/verify"

async def test_ckks_server():
    """CKKS 서버 연결 및 기본 동작 테스트"""
    
    print("🔍 CKKS 서버 연결 테스트 시작")
    print(f"📡 서버 URL: {CKKS_SERVER_URL}")
    
    try:
        # 테스트 데이터 준비
        test_data = {
            "sensor_id": "TEST-SENSOR-01",
            "value": 42.5,
            "timestamp": time.time(),
            "operation": "encrypt"
        }
        
        print(f"📤 테스트 요청 데이터: {test_data}")
        
        async with aiohttp.ClientSession() as session:
            start_time = time.perf_counter()
            
            async with session.post(
                CKKS_SERVER_URL,
                json=test_data,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                print(f"📥 서버 응답:")
                print(f"  - 상태 코드: {response.status}")
                print(f"  - 응답 시간: {response_time:.3f}ms")
                
                if response.status == 200:
                    try:
                        result = await response.json()
                        print(f"  - 응답 내용: {result}")
                        print("✅ CKKS 서버 연결 성공!")
                        return True
                    except:
                        text_result = await response.text()
                        print(f"  - 응답 텍스트: {text_result[:200]}...")
                        print("⚠️ JSON 파싱 실패, 하지만 서버 연결은 성공")
                        return True
                else:
                    error_text = await response.text()
                    print(f"  - 오류 내용: {error_text[:200]}...")
                    print("❌ CKKS 서버 오류 응답")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ CKKS 서버 연결 타임아웃 (30초)")
        return False
    except Exception as e:
        print(f"❌ CKKS 서버 연결 오류: {e}")
        return False

async def main():
    success = await test_ckks_server()
    if success:
        print("\n🎉 CKKS 서버가 정상 작동 중입니다!")
        print("✅ 실제 HAI CKKS 실험을 진행할 수 있습니다.")
    else:
        print("\n💥 CKKS 서버에 문제가 있습니다.")
        print("❌ 서버 상태를 확인하고 다시 시도해주세요.")

if __name__ == "__main__":
    asyncio.run(main())
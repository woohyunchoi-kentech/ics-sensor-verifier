#!/usr/bin/env python3
"""
빠른 HAI ED25519 테스트 (1개 조건만)
"""

import asyncio
import time
import json
import aiohttp
import pandas as pd
from pathlib import Path
from datetime import datetime
from test_keys_ed25519 import get_fixed_private_key, get_fixed_public_key_hex

class QuickED25519Test:
    def __init__(self):
        self.server_url = "http://192.168.0.11:8085"
        
    async def test_single_condition(self):
        """1개 센서, 1Hz, 100개 요청 테스트"""
        print("🚀 빠른 ED25519 테스트 시작")
        print(f"서버: {self.server_url}")
        print(f"고정 키: {get_fixed_public_key_hex()[:32]}...")
        
        # 서버 연결 테스트
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/") as response:
                    if response.status == 200:
                        print("✅ 서버 연결 성공")
                    else:
                        print(f"❌ 서버 연결 실패: {response.status}")
                        return
        except Exception as e:
            print(f"❌ 서버 연결 오류: {e}")
            return
        
        # 100개 요청 전송
        results = []
        for i in range(100):
            try:
                # 테스트 데이터
                sensor_id = f"HAI_TEST_SENSOR_{i%10}"
                sensor_value = float(i * 0.5)
                timestamp_unix = int(time.time())
                
                # ED25519 서명 생성
                timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
                message = f"{sensor_value:.6f}||{timestamp_iso}"
                signature = get_fixed_private_key().sign(message.encode('utf-8'))
                
                payload = {
                    "algorithm": "ed25519",
                    "sensor_id": sensor_id,
                    "sensor_value": sensor_value,
                    "signature": signature.hex(),
                    "public_key": get_fixed_public_key_hex(),
                    "timestamp": timestamp_unix
                }
                
                # 서버 전송
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.server_url}/api/v1/verify/ed25519",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            verified = result.get('verified', False)
                            proc_time = result.get('processing_time_ms', 0)
                            
                            results.append({
                                'request_id': i+1,
                                'sensor_id': sensor_id,
                                'sensor_value': sensor_value,
                                'verified': verified,
                                'processing_time_ms': proc_time,
                                'success': True
                            })
                            
                            if (i+1) % 10 == 0:
                                status = '✅' if verified else '❌'
                                print(f"{status} 요청 {i+1}/100: {sensor_value:.1f} → 검증:{verified} ({proc_time:.2f}ms)")
                        else:
                            print(f"❌ 요청 {i+1} 실패: {response.status}")
                            
            except Exception as e:
                print(f"❌ 요청 {i+1} 오류: {e}")
            
            # 1Hz (1초 간격)
            await asyncio.sleep(1.0)
        
        # 결과 출력
        success_count = len([r for r in results if r['success']])
        verified_count = len([r for r in results if r['verified']])
        avg_time = sum(r['processing_time_ms'] for r in results) / len(results) if results else 0
        
        print("\n📊 빠른 테스트 결과:")
        print(f"   성공 요청: {success_count}/100")
        print(f"   검증 성공: {verified_count}/100")
        print(f"   평균 처리 시간: {avg_time:.2f}ms")
        print("✅ 빠른 테스트 완료")
        
        return results

async def main():
    test = QuickED25519Test()
    await test.test_single_condition()

if __name__ == "__main__":
    asyncio.run(main())
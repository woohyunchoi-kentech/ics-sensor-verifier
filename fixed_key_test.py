#!/usr/bin/env python3
"""
고정 키쌍으로 ED25519 서버 테스트
"""

import asyncio
import time
import aiohttp
from datetime import datetime
from test_keys_ed25519 import get_fixed_private_key, get_fixed_public_key_hex

async def test_with_fixed_keys():
    """고정 키쌍으로 서버 테스트"""
    print("🔑 고정 키쌍으로 ED25519 서버 테스트")
    print(f"Public Key: {get_fixed_public_key_hex()}")
    print("-" * 60)
    
    session = aiohttp.ClientSession()
    
    try:
        for i in range(10):
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # ED25519 서명 생성 (고정 키 사용)
            timestamp_unix = int(time.time())
            timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
            sensor_value = float(i * 1.5)
            
            # 서버와 동일한 메시지 형식
            message = f"{sensor_value:.6f}||{timestamp_iso}".encode('utf-8')
            
            # 고정 개인키로 서명 생성
            signature = get_fixed_private_key().sign(message)
            
            payload = {
                'algorithm': 'ed25519',
                'sensor_id': 'FIXED_KEY_TEST', 
                'sensor_value': sensor_value,
                'signature': signature.hex(),
                'public_key': get_fixed_public_key_hex(),
                'timestamp': timestamp_unix
            }
            
            # 서버에 전송
            async with session.post(
                'http://192.168.0.11:8085/api/v1/verify/ed25519',
                json=payload,
                timeout=aiohttp.ClientTimeout(total=2)
            ) as response:
                result = await response.json() if response.status == 200 else None
                status = '✅' if response.status == 200 else '❌'
                
                if response.status == 200 and result:
                    verified = '✅' if result.get('verified', False) else '❌'
                    proc_time = result.get('processing_time_ms', 0)
                    print(f'{status} {timestamp} #{i+1:2d}: {sensor_value:.1f} → 응답:{response.status} 검증:{verified} ({proc_time:.2f}ms)')
                else:
                    error_text = await response.text()
                    print(f'{status} {timestamp} #{i+1:2d}: {sensor_value:.1f} → 오류:{response.status} {error_text}')
            
            # 1초 간격
            await asyncio.sleep(1.0)
        
        print("✅ 고정 키 테스트 완료")
        
    finally:
        await session.close()

asyncio.run(test_with_fixed_keys())
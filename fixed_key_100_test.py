#!/usr/bin/env python3
"""
고정 키쌍으로 ED25519 서버 100개 테스트
"""

import asyncio
import time
import aiohttp
from datetime import datetime
from test_keys_ed25519 import get_fixed_private_key, get_fixed_public_key_hex

async def test_100_with_fixed_keys():
    """고정 키쌍으로 서버 100개 테스트"""
    print("🔑 고정 키쌍으로 ED25519 서버 100개 테스트")
    print(f"📡 서버: http://192.168.0.11:8085")
    print(f"🔑 Public Key: {get_fixed_public_key_hex()}")
    print("-" * 80)
    
    session = aiohttp.ClientSession()
    success_count = 0
    verification_count = 0
    start_time = time.time()
    
    try:
        for i in range(100):
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            # ED25519 서명 생성 (고정 키 사용)
            timestamp_unix = int(time.time())
            timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
            sensor_value = float(i * 0.25)  # 0.0, 0.25, 0.5, 0.75, ...
            
            # 서버와 동일한 메시지 형식
            message = f"{sensor_value:.6f}||{timestamp_iso}".encode('utf-8')
            
            # 고정 개인키로 서명 생성
            signature = get_fixed_private_key().sign(message)
            
            payload = {
                'algorithm': 'ed25519',
                'sensor_id': 'FIXED_KEY_100_TEST', 
                'sensor_value': sensor_value,
                'signature': signature.hex(),
                'public_key': get_fixed_public_key_hex(),
                'timestamp': timestamp_unix
            }
            
            # 서버에 전송
            try:
                async with session.post(
                    'http://192.168.0.11:8085/api/v1/verify/ed25519',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        success_count += 1
                        result = await response.json()
                        if result.get('verified', False):
                            verification_count += 1
                        
                        # 10개마다 또는 처음 10개 출력
                        if (i + 1) % 10 == 0 or i < 10:
                            verified = '✅' if result.get('verified', False) else '❌'
                            proc_time = result.get('processing_time_ms', 0)
                            print(f'✅ {timestamp} #{i+1:3d}: {sensor_value:6.2f} → 검증:{verified} ({proc_time:.2f}ms)')
                    else:
                        error_text = await response.text()
                        print(f'❌ {timestamp} #{i+1:3d}: {sensor_value:6.2f} → 오류:{response.status}')
            
            except Exception as e:
                print(f'❌ {timestamp} #{i+1:3d}: {sensor_value:6.2f} → 네트워크 오류: {e}')
            
            # 정확히 1초 간격
            await asyncio.sleep(1.0)
        
        # 최종 통계
        end_time = time.time()
        duration = end_time - start_time
        
        print("-" * 80)
        print("📊 100개 테스트 결과:")
        print(f"   총 요청: 100개")
        print(f"   성공 응답: {success_count}/100 ({success_count}%)")
        print(f"   검증 성공: {verification_count}/100 ({verification_count}%)")
        print(f"   실행 시간: {duration:.1f}초")
        print(f"   실제 주파수: {99/(duration):.3f}Hz" if duration > 0 else "   실제 주파수: N/A")
        print("✅ 100개 고정 키 테스트 완료")
        
    finally:
        await session.close()

asyncio.run(test_100_with_fixed_keys())
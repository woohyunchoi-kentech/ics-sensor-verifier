#!/usr/bin/env python3
"""
Bulletproofs 음수값 처리 테스트
음수 센서 값을 포함한 범위 증명 생성 및 서버 검증
"""

import json
import asyncio
import aiohttp
from crypto.bulletproofs_baseline import BulletproofsBaseline

async def test_bulletproofs_with_negative():
    """음수값을 포함한 Bulletproofs 테스트"""
    
    # 테스트 케이스: 다양한 센서 값 (음수 포함)
    test_values = [
        -50.123,  # 음수 온도
        -5.678,   # 음수 값
        0.0,      # 영점
        1.234,    # 양수 값
        25.456,   # 양수 온도
        -75.999,  # 극단적 음수
    ]
    
    # Bulletproofs 생성기 초기화
    generator = BulletproofsBaseline(bit_length=32)
    
    # 서버 설정
    server_url = "http://192.168.0.11:8085/api/v1/verify/bulletproofs"
    
    print("=" * 60)
    print("🔬 Bulletproofs 음수값 처리 테스트")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        for value in test_values:
            print(f"\n📊 테스트 값: {value}")
            
            try:
                # 증명 생성 (음수 범위 지원)
                proof_data = generator.generate_proof(
                    sensor_value=value,
                    algorithm="Bulletproofs",
                    min_val=-100.0,  # 최소값 설정
                    max_val=100.0     # 최대값 설정
                )
                
                print(f"✅ 증명 생성 성공")
                print(f"  - 스케일된 값: {proof_data['scaled_value']}")
                print(f"  - 정규화 범위: [{proof_data['range_min']}, {proof_data['range_max']}]")
                print(f"  - 원본 범위: [{proof_data['original_min']}, {proof_data['original_max']}]")
                print(f"  - 생성 시간: {proof_data['generation_time_ms']:.2f}ms")
                
                # 서버로 전송할 데이터 준비
                request_data = {
                    "sensor_id": "TEST_SENSOR",
                    "sensor_value": value,  # 원본 값
                    "commitment": proof_data["commitment"],
                    "proof": proof_data["proof"],
                    "range_min": proof_data["range_min"],
                    "range_max": proof_data["range_max"],
                    "algorithm": "Bulletproofs"
                }
                
                # 서버에 검증 요청
                try:
                    async with session.post(
                        server_url,
                        json=request_data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        result = await response.json()
                        
                        if response.status == 200:
                            if result.get("verified"):
                                print(f"✅ 서버 검증 성공!")
                                print(f"  - 검증 시간: {result.get('verification_time_ms', 0):.2f}ms")
                            else:
                                print(f"❌ 서버 검증 실패: {result.get('error', 'Unknown error')}")
                        else:
                            print(f"❌ 서버 오류 ({response.status}): {result}")
                            
                except aiohttp.ClientError as e:
                    print(f"⚠️ 서버 연결 실패: {e}")
                    print("   서버가 실행 중인지 확인하세요 (192.168.0.11:8085)")
                    
            except Exception as e:
                print(f"❌ 증명 생성 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

async def test_edge_cases():
    """경계값 테스트"""
    
    print("\n" + "=" * 60)
    print("🔍 경계값 테스트")
    print("=" * 60)
    
    generator = BulletproofsBaseline(bit_length=32)
    
    # 경계값 테스트 케이스
    edge_cases = [
        ("최소값", -100.0),
        ("최소값 근처", -99.999),
        ("영점", 0.0),
        ("최대값 근처", 99.999),
        ("최대값", 100.0),
    ]
    
    for name, value in edge_cases:
        try:
            proof_data = generator.generate_proof(
                sensor_value=value,
                min_val=-100.0,
                max_val=100.0
            )
            print(f"✅ {name} ({value}): 성공 - 스케일된 값: {proof_data['scaled_value']}")
        except Exception as e:
            print(f"❌ {name} ({value}): 실패 - {e}")

if __name__ == "__main__":
    print("🚀 Bulletproofs 음수값 처리 테스트 시작\n")
    
    # 메인 테스트 실행
    asyncio.run(test_bulletproofs_with_negative())
    
    # 경계값 테스트 실행
    asyncio.run(test_edge_cases())
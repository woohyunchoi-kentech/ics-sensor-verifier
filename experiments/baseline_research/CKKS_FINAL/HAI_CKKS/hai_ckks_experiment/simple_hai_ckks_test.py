#!/usr/bin/env python3
"""
단순한 HAI CKKS 실험
==================
서버 로그 확인을 위한 작은 규모 실험
"""

import sys
import os
from pathlib import Path

# 상위 디렉토리의 모듈들을 import 가능하게 설정
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from crypto.ckks_baseline import CKKSBaseline
from hai_data_loader import HAIDataLoader
import requests
import json
import time
import asyncio

async def simple_hai_ckks_test():
    """간단한 HAI CKKS 테스트 (10개 요청)"""
    
    print("🚀 간단한 HAI CKKS 실험")
    print("=" * 30)
    
    # HAI 데이터 로드
    print("📂 HAI 데이터 로딩...")
    hai_loader = HAIDataLoader()
    sensors = hai_loader.get_sensor_list(1)  # 1개 센서만
    print(f"✅ 센서: {sensors[0]}")
    
    # CKKS 클라이언트 생성
    print("🔐 CKKS 클라이언트 초기화...")
    ckks = CKKSBaseline()
    success = ckks.load_server_public_key_from_api("http://192.168.0.11:8085")
    if not success:
        print("❌ CKKS 초기화 실패")
        return
    print("✅ CKKS 클라이언트 준비 완료")
    
    # 10개 요청 전송
    print("📤 10개 요청 전송 중...")
    verify_url = "http://192.168.0.11:8085/api/v1/ckks/verify"
    
    results = []
    
    for i in range(10):
        print(f"  요청 {i+1}/10...")
        
        # 실제 HAI 데이터 사용
        value = hai_loader.get_sensor_value(sensors[0], i)
        
        # CKKS 암호화
        start_time = time.time()
        proof_data = ckks.generate_proof(value)
        
        # 서버 요청
        response = requests.post(
            verify_url,
            json=proof_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            result_data = response.json()
            success = result_data.get('success', False)
            decrypted_value = result_data.get('decrypted_value', 0)
            
            results.append({
                'request_id': i+1,
                'original_value': value,
                'decrypted_value': decrypted_value,
                'success': success,
                'total_time_ms': total_time,
                'encryption_time_ms': proof_data.get('generation_time_ms', 0),
                'server_time_ms': result_data.get('processing_time_ms', 0)
            })
            
            print(f"    ✅ 성공: {value:.3f} → {decrypted_value:.3f} ({total_time:.1f}ms)")
        else:
            print(f"    ❌ 실패: {response.status_code}")
            results.append({
                'request_id': i+1,
                'original_value': value,
                'success': False,
                'total_time_ms': total_time,
                'error': response.text[:100]
            })
        
        # 서버 부하 방지를 위해 0.5초 대기
        await asyncio.sleep(0.5)
    
    # 결과 요약
    print("\n📊 실험 결과 요약:")
    successful = [r for r in results if r.get('success', False)]
    print(f"  • 총 요청: 10개")
    print(f"  • 성공: {len(successful)}개 ({len(successful)/10*100:.1f}%)")
    
    if successful:
        avg_total = sum(r['total_time_ms'] for r in successful) / len(successful)
        avg_encryption = sum(r['encryption_time_ms'] for r in successful) / len(successful)
        avg_server = sum(r['server_time_ms'] for r in successful) / len(successful)
        
        print(f"  • 평균 총 시간: {avg_total:.1f}ms")
        print(f"  • 평균 암호화: {avg_encryption:.1f}ms") 
        print(f"  • 평균 서버처리: {avg_server:.1f}ms")
    
    print("\n🎯 이제 서버 로그를 확인해보세요!")

if __name__ == "__main__":
    asyncio.run(simple_hai_ckks_test())
#!/usr/bin/env python3
"""
Simple Server Test
간단한 서버 연결 및 응답 테스트
"""

import requests
import json

def test_server():
    print("🌐 서버 테스트")
    print("=" * 50)
    
    # 간단한 테스트 데이터
    test_data = {
        "commitment": "02" + "1" * 62,
        "proof": {
            "A": "02" + "2" * 62,
            "S": "02" + "3" * 62,
            "T1": "02" + "4" * 62,
            "T2": "02" + "5" * 62,
            "tau_x": "123456",
            "mu": "123456",
            "t": "123456",
            "inner_product_proof": {
                "L": ["02" + "a" * 62] * 5,
                "R": ["02" + "b" * 62] * 5,
                "a": "123456",
                "b": "123456"
            }
        },
        "range_min": 0,
        "range_max": 2**32 - 1
    }
    
    try:
        print("📡 서버로 요청 전송...")
        response = requests.post(
            'http://192.168.0.11:8085/api/v1/verify/bulletproof',
            json=test_data,
            timeout=10
        )
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🔍 응답 내용:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            verified = result.get('verified', False)
            error_msg = result.get('error_message', '')
            
            print(f"\n🎯 검증 결과: {verified}")
            if error_msg:
                print(f"❌ 오류 메시지: {error_msg}")
                
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            print(f"내용: {response.text}")
            
    except Exception as e:
        print(f"❌ 연결 오류: {e}")

if __name__ == "__main__":
    test_server()
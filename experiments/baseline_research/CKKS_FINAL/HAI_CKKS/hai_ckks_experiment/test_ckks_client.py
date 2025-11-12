#!/usr/bin/env python3
"""
CKKS 클라이언트 직접 테스트
========================
실제 서버에 CKKS 요청을 보내서 로그 확인
"""

import sys
import os
from pathlib import Path

# 상위 디렉토리의 모듈들을 import 가능하게 설정
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from crypto.ckks_baseline import CKKSBaseline
import requests
import json

def test_ckks_simple():
    """단순한 CKKS 테스트"""
    
    print("🔍 CKKS 클라이언트 직접 테스트")
    print("=" * 40)
    
    try:
        # CKKS 클라이언트 생성
        ckks = CKKSBaseline()
        
        # 서버 공개키 로드
        print("📡 서버 공개키 로드 중...")
        success = ckks.load_server_public_key_from_api("http://192.168.0.11:8085")
        
        if not success:
            print("❌ 서버 공개키 로드 실패")
            return False
            
        print("✅ 서버 공개키 로드 성공")
        
        # 테스트 값 암호화
        test_value = 42.5
        print(f"🔐 테스트 값 암호화: {test_value}")
        
        # CKKS 증명 생성
        proof_data = ckks.generate_proof(test_value)
        print("✅ CKKS 증명 생성 완료")
        print(f"  - 암호화 시간: {proof_data.get('generation_time_ms', 0):.3f}ms")
        print(f"  - 데이터 크기: {proof_data.get('encrypted_size_bytes', 0)} bytes")
        
        # 서버로 검증 요청
        print("📤 서버로 검증 요청 전송...")
        verify_url = "http://192.168.0.11:8085/api/v1/ckks/verify"
        
        response = requests.post(
            verify_url,
            json=proof_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📥 서버 응답:")
        print(f"  - 상태 코드: {response.status_code}")
        print(f"  - 응답 시간: ?ms")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  - 검증 결과: {json.dumps(result, indent=2)}")
            print("🎉 CKKS 검증 성공!")
            return True
        else:
            error_text = response.text
            print(f"  - 오류 내용: {error_text}")
            print("❌ CKKS 검증 실패")
            return False
            
    except Exception as e:
        print(f"❌ CKKS 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ckks_simple()
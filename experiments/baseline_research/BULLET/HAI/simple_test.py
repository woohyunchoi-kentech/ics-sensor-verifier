#!/usr/bin/env python3
"""간단한 HAI Bulletproof 테스트"""

import sys
import pandas as pd
import requests
import time
from datetime import datetime

# 프로젝트 경로 추가
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

def test_hai_data_loading():
    """HAI 데이터 로딩 테스트"""
    print("🔍 HAI 데이터 로딩 테스트")
    
    try:
        data_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/hai/haiend-23.05/end-test1.csv"
        df = pd.read_csv(data_path)
        
        print(f"✅ 데이터 로드 성공: {len(df)} 행, {len(df.columns)} 컬럼")
        print(f"📊 센서 컬럼 (처음 10개): {list(df.columns[1:11])}")
        
        # 첫 번째 센서 데이터 샘플
        first_sensor = df.columns[1]
        sample_values = df[first_sensor].dropna().head(5).tolist()
        print(f"📊 {first_sensor} 샘플 값: {sample_values}")
        
        return True
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return False

def test_server_connection():
    """서버 연결 테스트"""
    print("\\n🔍 서버 연결 테스트")
    
    try:
        response = requests.get("http://192.168.0.11:8085/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공")
            return True
        else:
            print(f"⚠️ 서버 응답 이상: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_simple_bulletproof():
    """간단한 Bulletproof 테스트"""
    print("\\n🔍 Bulletproof 생성 테스트")
    
    try:
        from petlib.ec import EcGroup
        from petlib.bn import Bn
        from hashlib import sha256
        import secrets
        
        # Bulletproof 생성기 초기화
        group = EcGroup(714)
        order = group.order()
        g = group.generator()
        
        # H 생성
        g_bytes = g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % order
        h = h_scalar * g
        
        print("✅ Bulletproof 생성기 초기화 성공")
        
        # 간단한 증명 생성
        value = 42
        gamma = Bn.from_decimal(str(secrets.randbelow(int(str(order)))))
        V = Bn(value) * g + gamma * h
        
        print(f"✅ 커밋먼트 생성 성공: {V.export().hex()[:32]}...")
        
        return True
    except Exception as e:
        print(f"❌ Bulletproof 생성 실패: {e}")
        return False

def main():
    """메인 테스트"""
    print("="*60)
    print("🧪 HAI Bulletproof 간단 테스트")
    print("="*60)
    
    # 테스트 실행
    test1 = test_hai_data_loading()
    test2 = test_server_connection()
    test3 = test_simple_bulletproof()
    
    print("\\n📋 테스트 결과:")
    print(f"  • HAI 데이터 로딩: {'✅' if test1 else '❌'}")
    print(f"  • 서버 연결: {'✅' if test2 else '❌'}")
    print(f"  • Bulletproof 생성: {'✅' if test3 else '❌'}")
    
    if all([test1, test2, test3]):
        print("\\n🎉 모든 테스트 통과! 실험 준비 완료!")
        return True
    else:
        print("\\n❌ 일부 테스트 실패. 설정을 확인해주세요.")
        return False

if __name__ == "__main__":
    main()
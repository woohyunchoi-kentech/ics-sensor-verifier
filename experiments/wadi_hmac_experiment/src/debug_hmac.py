#!/usr/bin/env python3
"""HMAC 디버깅 스크립트"""

from hmac_authenticator import HMACAuthenticator

# HMAC 인증기 생성
authenticator = HMACAuthenticator()

# 테스트 데이터
test_data = {
    'sensor_id': 'WADI_AIT_001',
    'value': 7.15,
    'unit': 'pH',
    'location': 'Tank_A'
}

print("🔐 HMAC Debug Test")
print(f"Key: {authenticator.key.hex()}")

# 인증 메시지 생성
auth_msg = authenticator.create_authenticated_message(test_data)
print(f"\n📦 Authenticated message created:")
print(f"  Data: {auth_msg['data']}")
print(f"  HMAC: {auth_msg['hmac']}")
print(f"  Algorithm: {auth_msg['algorithm']}")

# 검증 테스트
is_valid, original_data = authenticator.verify_authenticated_message(auth_msg)
print(f"\n✅ Verification result: {is_valid}")

if is_valid:
    print("🎉 HMAC verification successful!")
else:
    print("❌ HMAC verification failed")
    
    # 직접 HMAC 계산해서 비교
    direct_hmac = authenticator.generate_hmac(auth_msg['data'])
    print(f"\n🔍 Debug info:")
    print(f"  Expected HMAC: {auth_msg['hmac']}")
    print(f"  Calculated HMAC: {direct_hmac.hmac_value}")
    print(f"  Match: {auth_msg['hmac'] == direct_hmac.hmac_value}")
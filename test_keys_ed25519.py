#!/usr/bin/env python3
"""
ED25519 테스트용 고정 키쌍 생성
"""

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# 고정 시드로 키 생성 (테스트용)
FIXED_SEED = b'test_ed25519_key_for_sensor_server_12345'[:32].ljust(32, b'\x00')

def generate_fixed_keypair():
    """고정된 시드로 ED25519 키쌍 생성"""
    # 시드에서 개인키 생성
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(FIXED_SEED)
    public_key = private_key.public_key()
    
    # 바이트로 직렬화
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return {
        'private_key_hex': private_key_bytes.hex(),
        'public_key_hex': public_key_bytes.hex(),
        'private_key_obj': private_key,
        'public_key_obj': public_key
    }

# 고정 키쌍 생성
FIXED_KEYPAIR = generate_fixed_keypair()

print("🔑 고정 ED25519 키쌍 생성 완료")
print(f"Private Key: {FIXED_KEYPAIR['private_key_hex']}")
print(f"Public Key:  {FIXED_KEYPAIR['public_key_hex']}")
print()

# 테스트용 함수들
def get_fixed_private_key():
    """고정 개인키 반환"""
    return FIXED_KEYPAIR['private_key_obj']

def get_fixed_public_key():
    """고정 공개키 반환"""
    return FIXED_KEYPAIR['public_key_obj']

def get_fixed_public_key_hex():
    """고정 공개키 hex 반환"""
    return FIXED_KEYPAIR['public_key_hex']

def get_fixed_private_key_hex():
    """고정 개인키 hex 반환"""
    return FIXED_KEYPAIR['private_key_hex']

# 검증 테스트
if __name__ == "__main__":
    import time
    from datetime import datetime
    
    # 테스트 데이터
    test_value = 42.5
    timestamp_unix = int(time.time())
    timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
    
    # 클라이언트 측 메시지 형식
    message = f"{test_value:.6f}||{timestamp_iso}".encode('utf-8')
    
    # 서명 생성
    signature = get_fixed_private_key().sign(message)
    
    # 서명 검증
    try:
        get_fixed_public_key().verify(signature, message)
        print("✅ 키쌍 검증 성공")
    except:
        print("❌ 키쌍 검증 실패")
    
    print(f"테스트 메시지: {message.decode()}")
    print(f"서명 길이: {len(signature)} bytes")
    print(f"서명 hex: {signature.hex()[:32]}...")
import tenseal as ts
import base64
import requests
import time
import json
import psutil
import os
from typing import Dict, Any, Tuple, Optional

class CKKSBaseline:
    def __init__(self):
        self.context = None
    
    def load_server_public_key(self, key_file_path):
        """서버 공개키로 컨텍스트 생성"""
        try:
            # 바이너리 파일 읽기
            with open(key_file_path, 'rb') as f:
                public_key_bytes = f.read()
            
            # 서버 공개키로 컨텍스트 생성
            self.context = ts.context_from(public_key_bytes)
            print(f"✅ 서버 공개키 로드: {len(public_key_bytes):,} bytes")
            return True
        except Exception as e:
            print(f"❌ 공개키 로드 실패: {e}")
            return False
    
    def encrypt_value(self, value):
        """서버 키로 암호화"""
        if self.context is None:
            raise ValueError("서버 공개키를 먼저 로드하세요")
        
        encrypted = ts.ckks_vector(self.context, [float(value)])
        encrypted_hex = encrypted.serialize().hex()
        encrypted_size = len(encrypted.serialize())
        
        return encrypted_hex, encrypted_size
    
    def generate_proof(self, sensor_value: float, algorithm: str = "CKKS") -> Dict[str, Any]:
        """센서 값에 대한 CKKS 증명 생성"""
        if self.context is None:
            raise ValueError("서버 공개키 먼저 로드하세요")
        
        start_time = time.time()
        
        try:
            # 암호화
            encrypted_hex, encrypted_size = self.encrypt_value(sensor_value)
            encrypted_base64 = base64.b64encode(bytes.fromhex(encrypted_hex)).decode('utf-8')
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            
            # Context 파라미터 정보 - 서버 실제 파라미터와 동일
            context_params = {
                "poly_modulus_degree": 8192,  # 서버가 실제 사용하는 값
                "coeff_mod_bit_sizes": [60, 40, 40, 60],  # 서버 실제값
                "scale": 1099511627776,  # 서버 실제값: 2^40
                "context_id": "lightweight"  # 서버 실제 context_id
            }
            
            # 서버와 동일한 context 파라미터 사용
            proof_data = {
                "encrypted_data": encrypted_base64,
                "context": "lightweight",  # lightweight context 사용
                "context_id": "lightweight",  # lightweight context
                "context_params": context_params,  # 서버 검증용 파라미터
                "algorithm": algorithm,
                # "sensor_value": sensor_value,  # 보안상 제거 - 실제 배포에서는 절대 포함하면 안됨
                "generation_time_ms": total_time,
                "encrypted_size_bytes": len(bytes.fromhex(encrypted_hex)),
                "timestamp": int(time.time()),
                "privacy_level": "full_homomorphic",
                "security_strength": "128-bit",
                # 서버 호환성을 위한 추가 필드
                "server_compatible": True,
                "context_source": "server_public_key",
                "scale_version": "v2_unified"  # 스케일 통일 버전 표시
            }
            
            return proof_data
            
        except Exception as e:
            print(f"❌ CKKS proof generation failed: {e}")
            raise e

    # 기존 호환성을 위한 메서드들
    def load_server_public_key_from_file(self, file_path):
        """기존 호환성을 위한 래퍼"""
        return self.load_server_public_key(file_path)
    
    def load_server_public_key_from_api(self, server_url='http://192.168.0.11:8085'):
        """서버 API에서 공개키와 컨텍스트 파라미터 다운로드"""
        try:
            import requests
            import base64
            
            # 서버의 public-key API 호출
            print("🔄 서버 public-key API 호출 중...")
            response = requests.get(f'{server_url}/api/v1/ckks/public-key')
            
            if response.status_code == 200:
                data = response.json()
                
                # 서버 공개키로 컨텍스트 생성
                context_base64 = data['public_key']
                context_bytes = base64.b64decode(context_base64)
                self.context = ts.context_from(context_bytes)
                
                # ⭐ 중요: 서버와 동일한 스케일 강제 설정
                self.context.global_scale = 2**40  # 1099511627776
                
                print(f"✅ 서버 컨텍스트 로드 성공")
                print(f"   Context ID: {data.get('context_id', 'lightweight')}")
                print(f"   Scale: {self.context.global_scale} (2^40)")
                print(f"   Poly degree: 8192")
                print(f"   Context 크기: {len(context_bytes):,} bytes")
                
                # 서버 파라미터 저장 (검증용)
                self.server_params = {
                    "poly_modulus_degree": 8192,
                    "coeff_mod_bit_sizes": [60, 40, 40, 60],
                    "scale": 2**40,
                    "context_id": data.get('context_id', 'lightweight')
                }
                
                return True
            else:
                print(f"❌ 서버 응답 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 공개키 로드 실패: {e}")
            return False
    
    def get_public_key_context(self):
        """검증 요청용 context 반환"""
        return getattr(self, 'public_key_base64', None)
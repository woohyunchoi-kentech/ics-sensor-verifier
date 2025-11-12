#!/usr/bin/env python3
"""
Correct Format Test
서버가 기대하는 정확한 EC Point 형식 테스트
"""

import sys
import requests
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256
from typing import Dict, Any

sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

class CorrectFormatTest:
    """정확한 형식 테스트"""
    
    def __init__(self):
        print("🔧 Correct Format Test")
        print("🎯 서버 기대 EC Point 형식 찾기")
        
        # 서버와 동일한 설정 (secp256k1)
        self.group = EcGroup(714)  # secp256k1
        self.order = self.group.order()
        self.g = self.group.generator()
        
        # 서버와 동일한 H
        g_bytes = self.g.export()
        h_hash = sha256(g_bytes + b"bulletproof_h").digest()
        h_scalar = Bn.from_binary(h_hash) % self.order
        self.h = h_scalar * self.g
        
        print("✅ secp256k1 초기화 완료")
    
    def create_valid_commitment(self, value: int) -> str:
        """유효한 커미트먼트 생성"""
        v = Bn(value)
        gamma = Bn(12345)  # 고정된 블라인딩 팩터
        
        # V = v*G + gamma*H (Pedersen commitment)
        V = v * self.g + gamma * self.h
        
        # 서버가 기대하는 형식으로 변환
        return V.export().hex()
    
    def create_valid_points(self) -> Dict[str, str]:
        """유효한 EC Point들 생성"""
        points = {}
        
        # 다양한 스칼라로 Point 생성
        scalars = {
            "A": Bn(11111),
            "S": Bn(22222), 
            "T1": Bn(33333),
            "T2": Bn(44444)
        }
        
        for name, scalar in scalars.items():
            point = scalar * self.g
            points[name] = point.export().hex()
        
        return points
    
    def create_inner_product_points(self) -> Dict[str, list]:
        """Inner Product용 유효한 Point들 생성"""
        L_points = []
        R_points = []
        
        # 5 rounds for 32-bit
        for i in range(5):
            L_scalar = Bn(1000 + i)
            R_scalar = Bn(2000 + i)
            
            L_point = L_scalar * self.g
            R_point = R_scalar * self.g
            
            L_points.append(L_point.export().hex())
            R_points.append(R_point.export().hex())
        
        return {"L": L_points, "R": R_points}
    
    def test_valid_format_proof(self, value: int = 42) -> bool:
        """유효한 형식의 증명 테스트"""
        print(f"\n🧪 유효한 형식 테스트: {value}")
        
        # 1. 유효한 커미트먼트 생성
        commitment = self.create_valid_commitment(value)
        print(f"  📊 커미트먼트: {commitment[:32]}...")
        
        # 2. 유효한 EC Point들 생성
        points = self.create_valid_points()
        print(f"  🔧 Point A: {points['A'][:32]}...")
        
        # 3. 유효한 Inner Product Points 생성
        inner_points = self.create_inner_product_points()
        print(f"  🔍 L[0]: {inner_points['L'][0][:32]}...")
        
        # 4. 유효한 스칼라 값들
        valid_scalars = {
            "tau_x": Bn(12345).hex(),
            "mu": Bn(11111).hex(),
            "t": Bn(54321).hex(),
            "a": Bn(0x56819823).hex(),
            "b": Bn(0x82CBFC54).hex()
        }
        
        # 5. 완전한 증명 구성
        valid_proof = {
            "commitment": commitment,
            "proof": {
                "A": points["A"],
                "S": points["S"], 
                "T1": points["T1"],
                "T2": points["T2"],
                "tau_x": valid_scalars["tau_x"],
                "mu": valid_scalars["mu"],
                "t": valid_scalars["t"],
                "inner_product_proof": {
                    "L": inner_points["L"],
                    "R": inner_points["R"],
                    "a": valid_scalars["a"],
                    "b": valid_scalars["b"]
                }
            },
            "range_min": 0,
            "range_max": 4294967295
        }
        
        # 6. 서버 테스트
        return self._test_server_format(valid_proof, "유효한 형식")
    
    def test_different_point_formats(self) -> bool:
        """다양한 Point 형식 테스트"""
        print(f"\n🔧 다양한 Point 형식 테스트")
        
        success = False
        
        # 형식 1: 표준 압축 형식 (현재)
        if not success:
            success = self.test_valid_format_proof(42)
        
        # 형식 2: 비압축 형식 테스트
        if not success:
            print(f"  🔧 비압축 형식 시도...")
            point = Bn(12345) * self.g
            uncompressed = self._to_uncompressed_hex(point)
            print(f"    비압축: {uncompressed[:32]}...")
            
        return success
    
    def _to_uncompressed_hex(self, point) -> str:
        """Point를 비압축 형식으로 변환"""
        try:
            # petlib Point를 비압축 형식으로
            point_bytes = point.export()
            if len(point_bytes) == 33:  # 압축된 형식
                # 04 prefix + x + y 형식으로 변환 시도
                return "04" + point_bytes[1:].hex() + "0" * 64
            return point_bytes.hex()
        except:
            return point.export().hex()
    
    def _test_server_format(self, proof_data: Dict[str, Any], test_name: str) -> bool:
        """서버 형식 테스트"""
        print(f"  🌐 {test_name} 서버 테스트...")
        
        try:
            response = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=proof_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                verified = result.get('verified', False)
                error_msg = result.get('error_message', '')
                processing_time = result.get('processing_time_ms', 0)
                
                print(f"    결과: {'✅ SUCCESS' if verified else '❌ FAIL'}")
                print(f"    시간: {processing_time:.1f}ms")
                if error_msg:
                    print(f"    오류: {error_msg}")
                
                if verified:
                    print(f"\n🎉🎉🎉 정확한 형식 발견! 🎉🎉🎉")
                    print(f"  ✅ {test_name} 성공!")
                    print(f"  🔧 이 형식으로 Production Mode 진행!")
                    return True
                else:
                    if "Invalid" not in error_msg and "Could not parse" not in error_msg:
                        print(f"    ⚡ 형식 문제 해결됨! 이제 수학적 검증 단계!")
                        return True  # 형식 오류가 아니면 성공으로 간주
                    
            else:
                print(f"    HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"    연결 오류: {e}")
        
        return False


def main():
    """Correct Format Test 실행"""
    print("🔧 Correct Format Test")
    print("🎯 서버 기대 EC Point 형식 찾기")
    print("🔍 Invalid format 오류 해결!")
    print("=" * 60)
    
    tester = CorrectFormatTest()
    
    # 1. 유효한 형식 테스트
    success = tester.test_valid_format_proof(42)
    
    if not success:
        # 2. 다양한 형식 테스트
        success = tester.test_different_point_formats()
    
    if success:
        print(f"\n🎉🎉🎉 FORMAT SUCCESS! 🎉🎉🎉")
        print("✅ 정확한 EC Point 형식 발견!")
        print("🚀 이제 Production Mode 수학적 검증만 남음!")
    else:
        print(f"\n🔧 Format Analysis")
        print("💡 서버 EC Point 파싱 로직 더 분석 필요")


if __name__ == "__main__":
    main()
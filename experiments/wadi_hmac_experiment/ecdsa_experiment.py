#!/usr/bin/env python3
"""
ECDSA 서명 알고리즘 실험
=====================
"""

import asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import base64
from typing import Dict, Any
from base_experiment import CryptoAlgorithm, BaseExperiment

class ECDSAAlgorithm(CryptoAlgorithm):
    """ECDSA 서명 알고리즘"""
    
    def __init__(self):
        super().__init__("ECDSA", "ecdsa")
        
        # ECDSA 키 쌍 생성 (P-256 곡선 사용)
        print("🔐 ECDSA P-256 키 쌍 생성 중...")
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        print("✅ ECDSA 키 생성 완료")
        
        # 공개키를 서버에 등록하기 위한 PEM 형식 변환
        self.public_key_pem = self.public_key.public_key_bytes(
            encoding=Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def generate_message(self, sensor_id: str, timestamp: int, value: float) -> str:
        """서명할 메시지 생성"""
        return f"{sensor_id}|{timestamp}|{value:.6f}"
    
    def generate_auth_data(self, sensor_id: str, timestamp: int, value: float) -> Dict[str, Any]:
        """ECDSA 서명 생성"""
        message = self.generate_message(sensor_id, timestamp, value)
        message_bytes = message.encode('utf-8')
        
        # ECDSA 서명 생성
        signature = self.private_key.sign(
            message_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        
        # Base64 인코딩
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            "signature": signature_b64,
            "public_key": self.public_key_pem
        }
    
    def get_payload(self, sensor_id: str, timestamp: int, value: float, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """서버 전송용 페이로드"""
        return {
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "sensor_value": value,
            "signature": auth_data["signature"],
            "public_key": auth_data["public_key"]
        }

async def main():
    """ECDSA 실험 메인"""
    
    print("🔐 ECDSA 서명 알고리즘 실험")
    print("=" * 50)
    
    # ECDSA 알고리즘 초기화
    ecdsa_algo = ECDSAAlgorithm()
    experiment = BaseExperiment(ecdsa_algo)
    
    # 실험 조건 (빠른 테스트)
    conditions = [
        (1, 1, 50),      # 1센서, 1Hz, 50개
        (1, 10, 50),     # 1센서, 10Hz, 50개
        (10, 1, 100),    # 10센서, 1Hz, 100개
        (10, 10, 500),   # 10센서, 10Hz, 500개
        (50, 1, 500),    # 50센서, 1Hz, 500개
        (50, 10, 2500),  # 50센서, 10Hz, 2500개
    ]
    
    results = []
    
    print(f"🚀 총 {len(conditions)}개 조건 ECDSA 실험 시작")
    
    for i, (sensor_count, frequency, max_requests) in enumerate(conditions, 1):
        print(f"\n{'='*60}")
        print(f"📍 ECDSA 조건 {i}/{len(conditions)}")
        print(f"{'='*60}")
        
        try:
            result = await experiment.run_condition(sensor_count, frequency, max_requests)
            results.append(result)
            
            # 중간 저장
            if i % 2 == 0:  # 2개마다 저장
                experiment.save_results(results, f"progress_{i:02d}")
            
            print(f"✅ ECDSA 조건 {i} 완료")
            
            # 조건 간 휴식
            if i < len(conditions):
                await asyncio.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\n⏹️ ECDSA 실험 중단됨 (완료: {i-1}/{len(conditions)})")
            break
        except Exception as e:
            print(f"❌ ECDSA 조건 {i} 실패: {e}")
            continue
    
    # 최종 결과 저장
    if results:
        final_path = experiment.save_results(results, "final")
        print_ecdsa_summary(results)
    
    print(f"\n🎉 ECDSA 실험 완료!")

def print_ecdsa_summary(results):
    """ECDSA 결과 요약"""
    if not results:
        return
    
    print(f"\n{'='*60}")
    print("🔐 ECDSA 실험 완료 요약")
    print(f"{'='*60}")
    
    total_requests = sum(r["total_requests"] for r in results)
    total_successful = sum(r["successful_requests"] for r in results)
    total_verified = sum(r["verified_requests"] for r in results)
    
    print(f"📊 ECDSA 전체 통계:")
    print(f"   완료 조건: {len(results)}개")
    print(f"   총 요청: {total_requests:,}개")
    print(f"   전체 성공률: {total_successful/max(1,total_requests)*100:.1f}%")
    print(f"   전체 검증률: {total_verified/max(1,total_requests)*100:.1f}%")
    
    if results:
        successful_results = [r for r in results if r["successful_requests"] > 0]
        if successful_results:
            avg_auth = sum(r["avg_auth_time_ms"] for r in successful_results) / len(successful_results)
            avg_network = sum(r["avg_network_time_ms"] for r in successful_results) / len(successful_results)
            avg_total = sum(r["avg_total_time_ms"] for r in successful_results) / len(successful_results)
            print(f"   평균 ECDSA 서명 시간: {avg_auth:.2f}ms")
            print(f"   평균 네트워크 시간: {avg_network:.1f}ms")
            print(f"   평균 총 시간: {avg_total:.1f}ms")
    
    print(f"\n📈 ECDSA 조건별 결과:")
    for i, result in enumerate(results, 1):
        print(f"   {i:2d}. {result['sensor_count']}센서 × {result['frequency']}Hz: "
              f"성공률 {result['success_rate']:.1f}%, "
              f"검증률 {result['verification_rate']:.1f}%, "
              f"서명 {result['avg_auth_time_ms']:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())
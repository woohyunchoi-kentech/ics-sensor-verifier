#!/usr/bin/env python3
"""
수정된 ED25519 실험 코드 테스트
"""

import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))

from experiments.baseline_research.ED25519.hai_ed25519_experiment import HAIEd25519Experiment


async def test_single_condition():
    """단일 조건 테스트"""
    print("🧪 ED25519 수정된 코드 테스트")
    print("="*50)
    
    experiment = HAIEd25519Experiment()
    
    # 1센서 × 1Hz × 10개 요청으로 테스트
    result = await experiment.run_experiment_condition(1, 1, 10)
    
    if result:
        stats, df = result
        print(f"\n✅ 테스트 성공!")
        print(f"   서버 성공률: {stats['server_success_rate']:.1f}%")
        print(f"   검증 성공률: {stats['verification_success_rate']:.1f}%")
        print(f"   평균 암호화: {stats['avg_crypto_time_ms']:.2f}ms")
        print(f"   평균 전송: {stats['avg_transmission_time_ms']:.2f}ms")
        print(f"   평균 검증: {stats['avg_verification_time_ms']:.2f}ms")
    else:
        print("❌ 테스트 실패")


if __name__ == "__main__":
    asyncio.run(test_single_condition())
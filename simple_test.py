#!/usr/bin/env python3

print("Testing bulletproofs negative values...")

try:
    import sys
    import os
    
    # 현재 디렉터리 추가
    sys.path.insert(0, os.getcwd())
    
    from crypto.bulletproofs_baseline import BulletproofsBaseline
    print("✅ Import successful")
    
    # Bulletproofs 생성기 초기화
    generator = BulletproofsBaseline(bit_length=32)
    print("✅ Generator initialized")
    
    # 음수 값 테스트
    test_value = -5.123
    proof = generator.generate_proof(
        sensor_value=test_value,
        min_val=-100.0,
        max_val=100.0
    )
    
    print(f"✅ Proof generated successfully!")
    print(f"   Original value: {test_value}")
    print(f"   Scaled value: {proof.get('scaled_value', 'N/A')}")
    print(f"   Range min: {proof.get('range_min', 'N/A')}")
    print(f"   Range max: {proof.get('range_max', 'N/A')}")
    print(f"   Generation time: {proof.get('generation_time_ms', 0):.2f}ms")

except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
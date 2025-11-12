#!/usr/bin/env python3
"""
빠른 HMAC 성능 테스트
====================

빠른 검증을 위한 짧은 시간 테스트
"""

import asyncio
import time
import hmac
import hashlib
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from performance_focused_experiment import PerformanceFocusedClient, ExperimentConfig, PerformanceHMACExperiment

async def quick_test():
    """빠른 성능 테스트 (10초씩)"""
    
    print("🚀 빠른 HMAC 성능 테스트")
    print("=" * 40)
    
    # 짧은 시간 설정
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10],  # 적은 센서 수
        frequencies=[1, 10],    # 적은 주파수
        duration_seconds=10,    # 10초만
        server_host="localhost",
        server_port=0,
        results_dir="../results/quick_test"
    )
    
    print(f"📊 빠른 테스트 설정:")
    print(f"  • 센서: {config.sensor_counts}")
    print(f"  • 주파수: {config.frequencies} Hz") 
    print(f"  • 시간: {config.duration_seconds}초/조건")
    
    experiment = PerformanceHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n✅ 빠른 테스트 완료!")
        
        # 결과 요약 출력
        results_dir = Path(config.results_dir)
        csv_files = list(results_dir.glob("*.csv"))
        
        if csv_files:
            for csv_file in csv_files:
                if "summary" in csv_file.name:
                    print(f"\n📄 결과 요약: {csv_file}")
                    df = pd.read_csv(csv_file)
                    print(df.to_string(index=False))
                    
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()

async def benchmark_hmac_generation():
    """HMAC 생성 성능 벤치마크"""
    print("\n🔑 HMAC 생성 성능 벤치마크")
    print("-" * 40)
    
    client = PerformanceFocusedClient()
    
    # 다양한 데이터 크기 테스트
    test_cases = [
        (1.5, "작은값"),
        (123.456789, "중간값"),
        (999999.999999, "큰값")
    ]
    
    for value, description in test_cases:
        times = []
        for _ in range(1000):  # 1000번 측정
            timestamp = int(time.time())
            hmac_hex, generation_time = client.calculate_hmac_performance(value, timestamp)
            times.append(generation_time)
        
        avg_time = np.mean(times)
        std_time = np.std(times)
        min_time = np.min(times)
        max_time = np.max(times)
        
        print(f"{description}:")
        print(f"  평균: {avg_time:.4f}ms")
        print(f"  표준편차: {std_time:.4f}ms")
        print(f"  최소/최대: {min_time:.4f}ms / {max_time:.4f}ms")
    
    print(f"\n✅ 벤치마크 완료")

if __name__ == "__main__":
    # HMAC 벤치마크 실행
    asyncio.run(benchmark_hmac_generation())
    
    # 빠른 성능 테스트 실행
    asyncio.run(quick_test())
#!/usr/bin/env python3
"""
빠른 WADI HMAC 테스트 (10초)
============================

전체 실험 전 빠른 검증
"""

import asyncio
from final_wadi_hmac_experiment import WADIHMACExperiment, ExperimentConfig

async def quick_wadi_test():
    """빠른 WADI 테스트"""
    
    print("🚀 빠른 WADI HMAC 테스트")
    print("=" * 40)
    
    # 짧은 테스트 설정
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10],
        frequencies=[1, 10],
        duration_seconds=10,  # 10초만
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/quick_wadi_test"
    )
    
    print(f"📊 빠른 테스트:")
    print(f"  • 센서: {config.sensor_counts}")
    print(f"  • 주파수: {config.frequencies} Hz") 
    print(f"  • 시간: {config.duration_seconds}초/조건")
    print(f"  • 예상: 100% HMAC 검증 성공")
    
    experiment = WADIHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n✅ 빠른 WADI 테스트 성공!")
        
        # 결과 요약
        import pandas as pd
        from pathlib import Path
        
        results_dir = Path(config.results_dir)
        summary_files = list(results_dir.glob("*_summary.csv"))
        
        if summary_files:
            df = pd.read_csv(summary_files[0])
            print(f"\n📊 검증 결과 요약:")
            for _, row in df.iterrows():
                print(f"  센서 {row['sensor_count']}개, {row['frequency']}Hz: "
                      f"검증률 {row['verification_rate']:.1f}%, "
                      f"HMAC {row['avg_hmac_generation_ms']:.3f}ms")
                
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")

if __name__ == "__main__":
    asyncio.run(quick_wadi_test())
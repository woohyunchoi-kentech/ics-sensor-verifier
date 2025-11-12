#!/usr/bin/env python3
"""
Mini WADI HMAC Experiment Test
=============================

빠른 시스템 검증을 위한 축소된 실험
"""

import asyncio
from experiment_runner import WADIHMACExperiment, ExperimentConfig

async def run_mini_test():
    """축소된 실험 실행"""
    
    # 최소 설정으로 실험
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 5],  # 축소된 센서 개수
        frequencies=[1, 2],    # 축소된 주파수
        duration_seconds=5,    # 짧은 실행 시간
        results_dir="../results"
    )
    
    print("🔬 Starting mini WADI HMAC experiment")
    print(f"📊 Configuration: {config.sensor_counts} sensors, {config.frequencies} Hz, {config.duration_seconds}s each")
    
    experiment = WADIHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print("✅ Mini experiment completed successfully!")
        
    except Exception as e:
        print(f"❌ Mini experiment failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_mini_test())
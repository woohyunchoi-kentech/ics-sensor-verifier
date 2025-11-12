#!/usr/bin/env python3
"""
누락된 WADI HMAC 실험 실행
=========================
직접 실행용 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path

# 현재 스크립트의 디렉토리를 파이썬 경로에 추가
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from final_wadi_hmac_experiment import WADIHMACExperiment, ExperimentConfig

async def run_50_sensor_1hz():
    """50센서, 1Hz 조건 실행"""
    
    print("🚀 누락된 실험: 50센서, 1Hz 시작")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[50],
        frequencies=[1],
        duration_seconds=1000,
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/complete_wadi_experiment"
    )
    
    # 결과 디렉토리 생성
    os.makedirs(config.results_dir, exist_ok=True)
    
    try:
        experiment = WADIHMACExperiment(config)
        await experiment.run_full_experiment()
        print("✅ 50센서, 1Hz 조건 완료!")
        return True
    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False

async def run_50_sensor_2hz():
    """50센서, 2Hz 조건 실행"""
    
    print("\n🚀 누락된 실험: 50센서, 2Hz 시작")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[50],
        frequencies=[2],
        duration_seconds=1000,
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/complete_wadi_experiment"
    )
    
    try:
        experiment = WADIHMACExperiment(config)
        await experiment.run_full_experiment()
        print("✅ 50센서, 2Hz 조건 완료!")
        return True
    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False

async def run_50_sensor_10hz():
    """50센서, 10Hz 조건 실행"""
    
    print("\n🚀 누락된 실험: 50센서, 10Hz 시작")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[50],
        frequencies=[10],
        duration_seconds=1000,
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/complete_wadi_experiment"
    )
    
    try:
        experiment = WADIHMACExperiment(config)
        await experiment.run_full_experiment()
        print("✅ 50센서, 10Hz 조건 완료!")
        return True
    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False

async def run_50_sensor_100hz():
    """50센서, 100Hz 조건 실행"""
    
    print("\n🚀 누락된 실험: 50센서, 100Hz 시작")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[50],
        frequencies=[100],
        duration_seconds=1000,
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/complete_wadi_experiment"
    )
    
    try:
        experiment = WADIHMACExperiment(config)
        await experiment.run_full_experiment()
        print("✅ 50센서, 100Hz 조건 완료!")
        return True
    except Exception as e:
        print(f"❌ 실패: {str(e)}")
        return False

async def main():
    """메인 실행 함수"""
    
    print("🎯 WADI HMAC 누락된 실험 실행기")
    print("=" * 60)
    print("실행할 조건들:")
    print("1. 50센서, 1Hz  (50,000 요청)")
    print("2. 50센서, 2Hz  (100,000 요청)")
    print("3. 50센서, 10Hz (500,000 요청)")
    print("4. 50센서, 100Hz (5,000,000 요청)")
    print("예상 소요 시간: 약 70분")
    print("=" * 60)
    
    results = []
    
    # 50센서 조건들 순차 실행
    result1 = await run_50_sensor_1hz()
    results.append(("50센서, 1Hz", result1))
    
    result2 = await run_50_sensor_2hz()
    results.append(("50센서, 2Hz", result2))
    
    result3 = await run_50_sensor_10hz()
    results.append(("50센서, 10Hz", result3))
    
    result4 = await run_50_sensor_100hz()
    results.append(("50센서, 100Hz", result4))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 실험 결과 요약")
    print("=" * 60)
    
    success_count = 0
    for condition, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{condition}: {status}")
        if success:
            success_count += 1
    
    print(f"\n성공률: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
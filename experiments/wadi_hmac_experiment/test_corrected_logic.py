#!/usr/bin/env python3
"""
수정된 주파수 로직 테스트
=======================
"""

import sys
from pathlib import Path

# 경로 설정
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from wadi_data_loader import WADIDataLoader
import asyncio
from final_wadi_hmac_experiment import WADIHMACExperiment, ExperimentConfig

def test_streaming_data_generation():
    """스트리밍 데이터 생성 테스트"""
    
    print("🧪 수정된 스트리밍 로직 테스트")
    print("=" * 50)
    
    loader = WADIDataLoader()
    success = loader.load_data()
    
    if not success:
        print("❌ 데이터 로드 실패")
        return
    
    # 테스트 조건들
    test_cases = [
        (2, 1, 5),    # 2센서, 1Hz, 5초
        (3, 2, 3),    # 3센서, 2Hz, 3초  
        (1, 3, 2),    # 1센서, 3Hz, 2초
    ]
    
    for sensors_count, frequency, duration in test_cases:
        print(f"\n📊 테스트: {sensors_count}센서, {frequency}Hz, {duration}초")
        
        # 센서 선택
        selected_sensors = loader.select_sensors(sensors_count)
        
        # 스트리밍 데이터 생성
        streaming_data = loader.get_streaming_data(
            sensors=selected_sensors,
            frequency=frequency,
            duration=duration
        )
        
        expected_points = sensors_count * frequency * duration
        actual_points = len(streaming_data)
        
        print(f"  예상 데이터 포인트: {expected_points}개")
        print(f"  실제 데이터 포인트: {actual_points}개")
        print(f"  일치 여부: {'✅' if expected_points == actual_points else '❌'}")
        
        # 센서별 데이터 포인트 수 확인
        sensor_counts = {}
        for data_point in streaming_data:
            sensor_id = data_point.get('sensor_id')
            if sensor_id:
                sensor_counts[sensor_id] = sensor_counts.get(sensor_id, 0) + 1
        
        print(f"  센서별 데이터 포인트:")
        for sensor_id, count in sensor_counts.items():
            expected_per_sensor = frequency * duration
            print(f"    {sensor_id}: {count}개 (예상: {expected_per_sensor}개)")
        
        # 타임스탬프 분포 확인
        if streaming_data:
            timestamps = [dp['timestamp'] for dp in streaming_data[:10]]
            print(f"  처음 10개 타임스탬프 간격:")
            for i in range(1, min(5, len(timestamps))):
                delta = (timestamps[i] - timestamps[i-1]).total_seconds()
                print(f"    {i}: {delta:.3f}초")

async def test_quick_experiment():
    """빠른 실험 테스트 (10초)"""
    
    print(f"\n🚀 빠른 실험 테스트: 2센서, 2Hz, 10초")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[2],
        frequencies=[2],
        duration_seconds=10,  # 10초만
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/test_corrected_logic"
    )
    
    experiment = WADIHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print("✅ 빠른 실험 성공!")
        
        # 결과 확인
        import glob
        result_files = glob.glob("../results/test_corrected_logic/*summary.csv")
        if result_files:
            import pandas as pd
            df = pd.read_csv(result_files[0])
            print(f"📊 실험 결과:")
            print(f"  총 요청: {df['total_requests'].iloc[0]:,}개")
            print(f"  성공률: {df['success_rate'].iloc[0]:.1f}%")
            print(f"  검증률: {df['verification_rate'].iloc[0]:.1f}%")
            
            expected_requests = 2 * 2 * 10  # 2센서 × 2Hz × 10초 = 40개
            actual_requests = df['total_requests'].iloc[0]
            print(f"  예상 vs 실제: {expected_requests} vs {actual_requests}")
            
    except Exception as e:
        print(f"❌ 실험 실패: {str(e)}")

if __name__ == "__main__":
    # 1. 데이터 생성 로직 테스트
    test_streaming_data_generation()
    
    # 2. 실제 실험 테스트
    print(f"\n" + "="*50)
    choice = input("빠른 실험 테스트를 실행하시겠습니까? (y/n): ").strip().lower()
    
    if choice == 'y':
        asyncio.run(test_quick_experiment())
    else:
        print("테스트 완료!")
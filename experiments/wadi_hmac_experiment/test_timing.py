#!/usr/bin/env python3
"""
실제 전송 타이밍 테스트
=====================
실제 서버로 전송하여 타이밍이 정확한지 확인
"""

import asyncio
import time
import sys
from pathlib import Path

current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from final_wadi_hmac_experiment import WADIHMACExperiment, ExperimentConfig

async def test_timing():
    """실제 타이밍 테스트 - 1센서, 2Hz, 10초"""
    
    print("🕒 실제 전송 타이밍 테스트")
    print("=" * 50)
    print("조건: 1센서, 2Hz, 10초")
    print("예상: 0.5초 간격으로 20번 전송")
    print("=" * 50)
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1],
        frequencies=[2],  # 2Hz = 0.5초 간격
        duration_seconds=10,  # 10초
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/timing_test"
    )
    
    experiment = WADIHMACExperiment(config)
    
    # 타이밍 로그 추가
    original_send = experiment.send_wadi_data
    
    send_times = []
    
    async def logged_send(data_point):
        current_time = time.time()
        send_times.append(current_time)
        
        # 실제 시간 출력
        if len(send_times) == 1:
            print(f"전송 {len(send_times):2d}: 시작 (0.000초)")
        else:
            interval = current_time - send_times[0]
            delta = current_time - send_times[-2] if len(send_times) > 1 else 0
            print(f"전송 {len(send_times):2d}: +{interval:.3f}초 (간격: {delta:.3f}초)")
        
        return await original_send(data_point)
    
    experiment.send_wadi_data = logged_send
    
    try:
        await experiment.run_full_experiment()
        
        print(f"\\n📊 타이밍 분석:")
        if len(send_times) >= 2:
            intervals = []
            for i in range(1, len(send_times)):
                interval = send_times[i] - send_times[i-1]
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            expected_interval = 0.5  # 2Hz = 0.5초 간격
            
            print(f"총 전송: {len(send_times)}번")
            print(f"평균 간격: {avg_interval:.3f}초 (예상: {expected_interval:.3f}초)")
            print(f"간격 정확도: {'✅' if abs(avg_interval - expected_interval) < 0.1 else '❌'}")
            
            # 개별 간격 확인
            print(f"\\n개별 간격:")
            for i, interval in enumerate(intervals[:10]):  # 처음 10개만
                status = "✅" if abs(interval - expected_interval) < 0.1 else "❌"
                print(f"  간격 {i+1}: {interval:.3f}초 {status}")
        
    except Exception as e:
        print(f"❌ 실험 실패: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_timing())
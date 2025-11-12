#!/usr/bin/env python3
"""
간단한 타이밍 테스트
==================
실제 전송 없이 타이밍 로직만 검증
"""

import asyncio
import time

async def test_timing_logic():
    """타이밍 로직 테스트"""
    
    print("🕒 타이밍 로직 테스트")
    print("=" * 50)
    print("조건: 2Hz, 5초 (10번 전송)")
    print("예상: 0.5초 간격")
    print("=" * 50)
    
    frequency = 2  # 2Hz
    duration = 5   # 5초
    total_transmissions = frequency * duration  # 10번 전송
    interval = 1.0 / frequency  # 0.5초 간격
    
    print(f"전송 간격: {interval}초")
    print(f"총 전송 횟수: {total_transmissions}번")
    print("")
    
    start_time = time.time()
    actual_times = []
    
    for transmission_id in range(total_transmissions):
        # 목표 시간 계산
        target_time = start_time + (transmission_id * interval)
        current_time = time.time()
        
        # 대기
        if current_time < target_time:
            await asyncio.sleep(target_time - current_time)
        
        # 실제 전송 시간 기록
        actual_time = time.time()
        actual_times.append(actual_time)
        
        # 진행 상황 출력
        elapsed = actual_time - start_time
        expected_elapsed = transmission_id * interval
        
        print(f"전송 {transmission_id + 1:2d}: {elapsed:.3f}초 (예상: {expected_elapsed:.3f}초)")
    
    print(f"\\n📊 타이밍 분석:")
    
    # 간격 분석
    intervals = []
    for i in range(1, len(actual_times)):
        interval_actual = actual_times[i] - actual_times[i-1]
        intervals.append(interval_actual)
    
    if intervals:
        avg_interval = sum(intervals) / len(intervals)
        max_deviation = max(abs(inv - interval) for inv in intervals)
        
        print(f"평균 간격: {avg_interval:.3f}초 (예상: {interval:.3f}초)")
        print(f"최대 편차: {max_deviation:.3f}초")
        print(f"정확도: {'✅' if max_deviation < 0.01 else '❌'}")
        
        # 개별 간격 확인
        print(f"\\n개별 간격:")
        for i, inv in enumerate(intervals):
            deviation = abs(inv - interval)
            status = "✅" if deviation < 0.01 else "❌"
            print(f"  간격 {i+1}: {inv:.3f}초 (편차: {deviation:.3f}초) {status}")

async def test_multiple_frequencies():
    """여러 주파수 테스트"""
    
    print(f"\\n" + "="*50)
    print("🚀 다중 주파수 타이밍 테스트")
    print("="*50)
    
    test_cases = [
        (1, 3),   # 1Hz, 3초
        (2, 3),   # 2Hz, 3초  
        (10, 2),  # 10Hz, 2초
    ]
    
    for frequency, duration in test_cases:
        print(f"\\n📊 {frequency}Hz, {duration}초 테스트:")
        
        total_transmissions = frequency * duration
        interval = 1.0 / frequency
        
        start_time = time.time()
        
        for transmission_id in range(total_transmissions):
            target_time = start_time + (transmission_id * interval)
            current_time = time.time()
            
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            actual_time = time.time()
            elapsed = actual_time - start_time
            expected = transmission_id * interval
            
            if transmission_id < 5:  # 처음 5개만 출력
                print(f"  전송 {transmission_id + 1}: {elapsed:.3f}초 (예상: {expected:.3f}초)")

if __name__ == "__main__":
    asyncio.run(test_timing_logic())
    asyncio.run(test_multiple_frequencies())
#!/usr/bin/env python3
"""
Precise Timer for Sensor Data Transmission
정확한 센서 데이터 전송을 위한 정밀 타이머
"""

import asyncio
import time
import threading
from typing import Callable, Optional
from datetime import datetime, timedelta


class PreciseTimer:
    """정밀한 주기적 실행을 위한 타이머"""
    
    def __init__(self, frequency: float, callback: Callable):
        """
        Args:
            frequency: 주파수 (Hz) - 초당 실행 횟수
            callback: 실행할 함수
        """
        self.frequency = frequency
        self.interval = 1.0 / frequency
        self.callback = callback
        self.running = False
        self.thread = None
        self.start_time = None
        self.execution_count = 0
        
    def start(self):
        """타이머 시작"""
        if self.running:
            return
            
        self.running = True
        self.start_time = time.perf_counter()
        self.execution_count = 0
        
        self.thread = threading.Thread(target=self._run_precise_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """타이머 중지"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _run_precise_loop(self):
        """정밀한 타이밍 루프"""
        while self.running:
            # 다음 실행 시점 계산
            next_execution_time = self.start_time + (self.execution_count * self.interval)
            current_time = time.perf_counter()
            
            # 대기 시간 계산
            sleep_time = next_execution_time - current_time
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # 콜백 실행
            if self.running:
                try:
                    self.callback()
                except Exception as e:
                    print(f"❌ 타이머 콜백 오류: {e}")
                
                self.execution_count += 1
    
    @property
    def actual_frequency(self) -> float:
        """실제 달성한 주파수"""
        if self.start_time is None or self.execution_count == 0:
            return 0.0
        
        elapsed = time.perf_counter() - self.start_time
        return self.execution_count / elapsed if elapsed > 0 else 0.0


class AsyncPreciseTimer:
    """비동기 정밀 타이머"""
    
    def __init__(self, frequency: float):
        self.frequency = frequency
        self.interval = 1.0 / frequency
        self.running = False
        self.start_time = None
        self.execution_count = 0
    
    async def run_with_callback(self, callback: Callable, duration: Optional[float] = None):
        """
        콜백 함수를 정확한 간격으로 실행
        
        Args:
            callback: 실행할 비동기 함수
            duration: 실행 시간 (초), None이면 무한 실행
        """
        self.running = True
        self.start_time = time.perf_counter()
        self.execution_count = 0
        
        end_time = self.start_time + duration if duration else None
        
        try:
            while self.running:
                # 다음 실행 시점 계산
                next_execution_time = self.start_time + (self.execution_count * self.interval)
                current_time = time.perf_counter()
                
                # 종료 조건 확인
                if end_time and current_time >= end_time:
                    break
                
                # 대기 시간 계산
                sleep_time = next_execution_time - current_time
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                # 콜백 실행
                if self.running:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback()
                        else:
                            callback()
                    except Exception as e:
                        print(f"❌ 비동기 타이머 콜백 오류: {e}")
                    
                    self.execution_count += 1
        finally:
            self.running = False
    
    def stop(self):
        """타이머 중지"""
        self.running = False
    
    @property 
    def actual_frequency(self) -> float:
        """실제 달성한 주파수"""
        if self.start_time is None or self.execution_count == 0:
            return 0.0
        
        elapsed = time.perf_counter() - self.start_time
        return self.execution_count / elapsed if elapsed > 0 else 0.0


# 사용 예제
async def test_precise_timing():
    """정밀 타이밍 테스트"""
    print("🕐 정밀 타이밍 테스트 시작")
    
    execution_times = []
    
    def record_execution():
        """실행 시간 기록"""
        now = time.perf_counter()
        execution_times.append(now)
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"📤 {timestamp} - 실행 #{len(execution_times)}")
    
    # 1Hz로 10초간 실행
    timer = AsyncPreciseTimer(frequency=1.0)
    await timer.run_with_callback(record_execution, duration=10.0)
    
    # 간격 분석
    if len(execution_times) > 1:
        intervals = [execution_times[i] - execution_times[i-1] 
                    for i in range(1, len(execution_times))]
        
        avg_interval = sum(intervals) / len(intervals)
        max_interval = max(intervals)
        min_interval = min(intervals)
        
        print(f"\n📊 타이밍 분석:")
        print(f"   실행 횟수: {len(execution_times)}")
        print(f"   목표 간격: 1.000초")
        print(f"   평균 간격: {avg_interval:.3f}초")
        print(f"   최대 간격: {max_interval:.3f}초") 
        print(f"   최소 간격: {min_interval:.3f}초")
        print(f"   실제 주파수: {timer.actual_frequency:.3f}Hz")


if __name__ == "__main__":
    asyncio.run(test_precise_timing())
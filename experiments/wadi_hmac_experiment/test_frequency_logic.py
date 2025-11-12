#!/usr/bin/env python3
"""
수정된 주파수 로직 테스트
=======================
올바른 주파수 개념 확인:
- 1Hz = 1초에 1번 전송
- 2Hz = 1초에 2번 전송 (0.5초 간격)
- 각 전송마다 모든 센서 데이터 포함
"""

import sys
from pathlib import Path

# 경로 설정
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from wadi_data_loader import WADIDataLoader
import pandas as pd

def test_corrected_frequency_logic():
    """수정된 주파수 로직 테스트"""
    
    print("🧪 수정된 주파수 로직 테스트")
    print("=" * 50)
    
    loader = WADIDataLoader("/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv")
    success = loader.load_data()
    
    if not success:
        print("❌ 데이터 로드 실패")
        return
    
    # 테스트 조건들
    test_cases = [
        (2, 1, 5),    # 2센서, 1Hz, 5초 → 5번 전송 × 2센서 = 10개 요청
        (3, 2, 3),    # 3센서, 2Hz, 3초 → 6번 전송 × 3센서 = 18개 요청  
        (1, 4, 2),    # 1센서, 4Hz, 2초 → 8번 전송 × 1센서 = 8개 요청
        (4, 10, 1),   # 4센서, 10Hz, 1초 → 10번 전송 × 4센서 = 40개 요청
    ]
    
    for sensors_count, frequency, duration in test_cases:
        print(f"\\n📊 테스트: {sensors_count}센서, {frequency}Hz, {duration}초")
        
        # 센서 선택
        selected_sensors = loader.select_sensors(sensors_count)
        
        # 스트리밍 데이터 생성
        streaming_data = loader.get_streaming_data(
            sensors=selected_sensors,
            frequency=frequency,
            duration=duration
        )
        
        # 올바른 계산
        expected_transmissions = frequency * duration  # 전송 횟수
        expected_total_requests = expected_transmissions * sensors_count  # 총 요청 수
        actual_requests = len(streaming_data)
        
        print(f"  전송 횟수: {expected_transmissions}번 (주파수 {frequency}Hz × {duration}초)")
        print(f"  예상 총 요청: {expected_total_requests}개 ({expected_transmissions}번 전송 × {sensors_count}센서)")
        print(f"  실제 요청: {actual_requests}개")
        print(f"  일치 여부: {'✅' if expected_total_requests == actual_requests else '❌'}")
        
        # 전송별 센서 개수 확인
        transmission_counts = {}
        for data_point in streaming_data:
            transmission_id = data_point.get('transmission_id', 0)
            if transmission_id not in transmission_counts:
                transmission_counts[transmission_id] = 0
            transmission_counts[transmission_id] += 1
        
        print(f"  전송별 센서 개수:")
        for i in range(min(5, expected_transmissions)):  # 처음 5개 전송만 확인
            count = transmission_counts.get(i, 0)
            print(f"    전송 {i}: {count}개 센서 (예상: {sensors_count}개)")
        
        # 타임스탬프 간격 확인
        if len(streaming_data) >= sensors_count * 2:  # 최소 2번 전송 데이터가 있어야 함
            print(f"  타임스탬프 간격 확인:")
            interval_expected = 1.0 / frequency
            
            # 같은 센서의 연속 두 전송 간격 확인
            first_sensor = selected_sensors[0]
            sensor_timestamps = []
            for dp in streaming_data[:20]:  # 처음 20개만 확인
                if dp['sensor_id'] == first_sensor:
                    sensor_timestamps.append(dp['timestamp'])
                    
            if len(sensor_timestamps) >= 2:
                actual_interval = (sensor_timestamps[1] - sensor_timestamps[0]).total_seconds()
                print(f"    예상 간격: {interval_expected:.3f}초")
                print(f"    실제 간격: {actual_interval:.3f}초")
                print(f"    간격 일치: {'✅' if abs(actual_interval - interval_expected) < 0.01 else '❌'}")

def show_frequency_examples():
    """주파수별 예시 출력"""
    
    print(f"\\n" + "="*50)
    print("📊 주파수별 예시")
    print("="*50)
    
    examples = [
        (1, 1, 10),   # 1센서, 1Hz, 10초
        (1, 2, 10),   # 1센서, 2Hz, 10초  
        (50, 2, 1000), # 50센서, 2Hz, 1000초
        (100, 100, 1000), # 100센서, 100Hz, 1000초
    ]
    
    for sensors, freq, duration in examples:
        transmissions = freq * duration
        total_requests = transmissions * sensors
        interval = 1.0 / freq
        
        print(f"\\n🎯 {sensors}센서, {freq}Hz, {duration}초:")
        print(f"  • 전송 간격: {interval:.3f}초")
        print(f"  • 총 전송 횟수: {transmissions:,}번")
        print(f"  • 총 요청 수: {total_requests:,}개")
        if duration <= 10:  # 짧은 실험만 타임라인 표시
            print(f"  • 타임라인: ", end="")
            for i in range(min(5, transmissions)):
                time = i * interval
                print(f"{time:.1f}초 ", end="")
            if transmissions > 5:
                print("...")

if __name__ == "__main__":
    test_corrected_frequency_logic()
    show_frequency_examples()
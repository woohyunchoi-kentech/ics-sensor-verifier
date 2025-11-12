#!/usr/bin/env python3
"""
선정된 센서 리스트 분석기
=======================
실험에서 사용된 센서들을 분석
"""

import sys
from pathlib import Path

# 경로 설정
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from wadi_data_loader import WADIDataLoader
import pandas as pd

def analyze_sensor_selection():
    """센서 선정 분석"""
    
    print("🔍 WADI 센서 선정 분석")
    print("=" * 50)
    
    # 데이터 로더 초기화
    loader = WADIDataLoader()
    success = loader.load_data()
    
    if not success:
        print("❌ 데이터 로드 실패")
        return
    
    print(f"✅ 총 {len(loader.sensor_list)}개 센서 로드 완료")
    
    # 센서 타입별 분류
    sensor_types = {
        'AIT': [],  # Analog Input Temperature
        'FIT': [],  # Flow Indicator Transmitter  
        'LIT': [],  # Level Indicator Transmitter
        'PIT': [],  # Pressure Indicator Transmitter
        'DPIT': [], # Differential Pressure Indicator Transmitter
        'Other': []
    }
    
    for sensor in loader.sensor_list:
        sensor_str = str(sensor)
        if 'AIT' in sensor_str:
            sensor_types['AIT'].append(sensor)
        elif 'FIT' in sensor_str:
            sensor_types['FIT'].append(sensor)
        elif 'LIT' in sensor_str:
            sensor_types['LIT'].append(sensor)
        elif 'PIT' in sensor_str:
            sensor_types['PIT'].append(sensor)
        elif 'DPIT' in sensor_str:
            sensor_types['DPIT'].append(sensor)
        else:
            sensor_types['Other'].append(sensor)
    
    print(f"\n📊 센서 타입별 분포:")
    for sensor_type, sensors in sensor_types.items():
        if sensors:
            print(f"  {sensor_type:>6}: {len(sensors):>3}개")
    
    # 다양한 센서 수로 선정 테스트
    test_counts = [1, 10, 50, 100]
    
    for count in test_counts:
        if count <= len(loader.sensor_list):
            print(f"\n🎯 {count}개 센서 선정 결과:")
            selected = loader.select_sensors(count)
            
            # 선정된 센서 타입별 분석
            selected_types = {
                'AIT': [], 'FIT': [], 'LIT': [], 'PIT': [], 'DPIT': [], 'Other': []
            }
            
            for sensor in selected:
                sensor_str = str(sensor)
                if 'AIT' in sensor_str:
                    selected_types['AIT'].append(sensor)
                elif 'FIT' in sensor_str:
                    selected_types['FIT'].append(sensor)
                elif 'LIT' in sensor_str:
                    selected_types['LIT'].append(sensor)
                elif 'PIT' in sensor_str:
                    selected_types['PIT'].append(sensor)
                elif 'DPIT' in sensor_str:
                    selected_types['DPIT'].append(sensor)
                else:
                    selected_types['Other'].append(sensor)
            
            print(f"  선정된 센서 타입 분포:")
            for sensor_type, sensors in selected_types.items():
                if sensors:
                    print(f"    {sensor_type:>6}: {len(sensors):>2}개")
            
            # 처음 10개 센서 이름 출력
            print(f"  처음 10개 센서:")
            for i, sensor in enumerate(selected[:10]):
                print(f"    {i+1:>2}. {sensor}")
            
            if len(selected) > 10:
                print(f"    ... (총 {len(selected)}개)")

def get_current_experiment_sensors():
    """현재 실험에서 사용 중인 센서들 추정"""
    
    print("\n" + "="*50)
    print("🚀 현재 50센서 실험 추정 센서 리스트")
    print("="*50)
    
    # 동일한 시드로 센서 선정 (재현성)
    loader = WADIDataLoader()
    success = loader.load_data()
    
    if success:
        # 50개 센서 선정
        selected_50 = loader.select_sensors(50)
        
        print(f"📋 50개 선정 센서 리스트:")
        
        # 타입별로 정리해서 출력
        by_type = {}
        for sensor in selected_50:
            sensor_str = str(sensor)
            if 'AIT' in sensor_str:
                sensor_type = 'AIT'
            elif 'FIT' in sensor_str:
                sensor_type = 'FIT' 
            elif 'LIT' in sensor_str:
                sensor_type = 'LIT'
            elif 'PIT' in sensor_str:
                sensor_type = 'PIT'
            elif 'DPIT' in sensor_str:
                sensor_type = 'DPIT'
            else:
                sensor_type = 'Other'
            
            if sensor_type not in by_type:
                by_type[sensor_type] = []
            by_type[sensor_type].append(sensor)
        
        # 타입별 출력
        for sensor_type in sorted(by_type.keys()):
            sensors = by_type[sensor_type]
            print(f"\n  📊 {sensor_type} 타입 ({len(sensors)}개):")
            for i, sensor in enumerate(sensors):
                print(f"    {i+1:>2}. {sensor}")

if __name__ == "__main__":
    analyze_sensor_selection()
    get_current_experiment_sensors()
#!/usr/bin/env python3
"""
HAI 데이터셋 로더
===============
실제 HAI 데이터를 로드하여 실험에 사용
"""

import pandas as pd
import numpy as np
from pathlib import Path
import random

class HAIDataLoader:
    def __init__(self, data_path="../../../../../data/hai/haiend-23.05/end-train1.csv"):
        """HAI 데이터셋 로더 초기화"""
        self.data_path = Path(data_path)
        self.data = None
        self.sensor_columns = None
        self.load_data()
    
    def load_data(self):
        """HAI 데이터셋 로드"""
        try:
            print(f"📂 HAI 데이터 로드 중: {self.data_path}")
            self.data = pd.read_csv(self.data_path)
            
            # 센서 컬럼만 추출 (Timestamp 제외)
            self.sensor_columns = [col for col in self.data.columns if col != 'Timestamp']
            
            print(f"✅ HAI 데이터 로드 완료:")
            print(f"   • 행 수: {len(self.data):,}")
            print(f"   • 센서 수: {len(self.sensor_columns)}")
            print(f"   • 시간 범위: {self.data.iloc[0]['Timestamp']} ~ {self.data.iloc[-1]['Timestamp']}")
            
            # 처음 10개 센서 이름 출력
            print(f"   • 센서 예시: {self.sensor_columns[:10]}")
            
        except Exception as e:
            raise Exception(f"HAI 데이터 로드 실패: {e}")
    
    def get_sensor_list(self, sensor_count):
        """지정된 개수의 센서 목록 반환"""
        if sensor_count > len(self.sensor_columns):
            raise ValueError(f"요청된 센서 수({sensor_count})가 available 센서 수({len(self.sensor_columns)})를 초과합니다.")
        
        # 랜덤하게 센서 선택 (재현 가능하도록 시드 고정)
        random.seed(42)
        selected_sensors = random.sample(self.sensor_columns, sensor_count)
        
        return selected_sensors
    
    def get_sensor_value(self, sensor_name, request_index=None):
        """특정 센서의 값 반환"""
        if sensor_name not in self.sensor_columns:
            raise ValueError(f"센서 '{sensor_name}'을 찾을 수 없습니다.")
        
        # 데이터 인덱스 결정
        if request_index is None:
            # 랜덤 선택
            data_index = random.randint(0, len(self.data) - 1)
        else:
            # 순차 선택 (데이터 범위 내에서 순환)
            data_index = request_index % len(self.data)
        
        value = self.data.iloc[data_index][sensor_name]
        
        # NaN 값 처리
        if pd.isna(value):
            # NaN인 경우 해당 센서의 평균값 사용
            value = self.data[sensor_name].mean()
            if pd.isna(value):  # 평균도 NaN인 경우
                value = 0.0
        
        return float(value)
    
    def get_streaming_data(self, sensor_count, frequency, duration_seconds):
        """스트리밍 형태로 센서 데이터 생성"""
        sensors = self.get_sensor_list(sensor_count)
        interval = 1.0 / frequency
        total_transmissions = int(duration_seconds / interval)
        
        streaming_data = []
        
        for transmission_id in range(total_transmissions):
            timestamp = transmission_id * interval
            
            for sensor in sensors:
                value = self.get_sensor_value(sensor, transmission_id)
                
                streaming_data.append({
                    'timestamp': timestamp,
                    'sensor_id': sensor,
                    'sensor_value': value,
                    'transmission_id': transmission_id
                })
        
        return streaming_data
    
    def get_info(self):
        """데이터셋 정보 반환"""
        if self.data is None:
            return "데이터가 로드되지 않았습니다."
        
        return {
            'total_rows': len(self.data),
            'total_sensors': len(self.sensor_columns),
            'sensor_names': self.sensor_columns[:20],  # 처음 20개만
            'time_range': (self.data.iloc[0]['Timestamp'], self.data.iloc[-1]['Timestamp']),
            'sample_values': {sensor: self.data[sensor].describe() for sensor in self.sensor_columns[:5]}
        }

if __name__ == "__main__":
    # HAI 데이터 로더 테스트
    loader = HAIDataLoader()
    
    print("\n🔍 HAI 데이터셋 정보:")
    info = loader.get_info()
    print(f"   총 행 수: {info['total_rows']:,}")
    print(f"   총 센서 수: {info['total_sensors']}")
    
    print("\n🧪 테스트: 10개 센서 선택")
    sensors = loader.get_sensor_list(10)
    for i, sensor in enumerate(sensors):
        value = loader.get_sensor_value(sensor, i)
        print(f"   {sensor}: {value:.6f}")
    
    print("\n✅ HAI 데이터 로더 테스트 완료")
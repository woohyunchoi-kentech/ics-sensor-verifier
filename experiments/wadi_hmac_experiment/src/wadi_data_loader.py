#!/usr/bin/env python3
"""
WADI Data Loader for HMAC Experiment
===================================

WADI 데이터셋에서 센서 데이터를 로드하고 HMAC 실험에 필요한 형태로 전처리하는 모듈

Author: Claude Code
Date: 2025-08-28
"""

import pandas as pd
import numpy as np
import json
from typing import List, Dict, Tuple, Any
from pathlib import Path
import logging

class WADIDataLoader:
    """WADI 데이터셋 로더 클래스"""
    
    def __init__(self, csv_path: str = None):
        """
        WADI 데이터 로더 초기화
        
        Args:
            csv_path: WADI CSV 파일 경로
        """
        if csv_path is None:
            # 기본 경로 설정 (올바른 경로로 수정)
            self.csv_path = "../../../data/wadi/WADI_14days_new.csv"
        else:
            self.csv_path = csv_path
            
        self.df = None
        self.sensor_list = []
        self.selected_sensors = []
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def load_data(self) -> bool:
        """
        WADI CSV 파일을 로드하고 전처리
        
        Returns:
            성공 여부
        """
        try:
            self.logger.info(f"Loading WADI data from {self.csv_path}")
            self.df = pd.read_csv(self.csv_path)
            
            # 기본 전처리
            self.df = self._preprocess_data()
            
            # 센서 목록 추출 (Date, Time, Row 제외)
            exclude_cols = ['Row', 'Date', 'Time']
            self.sensor_list = [col for col in self.df.columns if col not in exclude_cols]
            
            self.logger.info(f"Loaded {len(self.df)} rows with {len(self.sensor_list)} sensors")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading WADI data: {str(e)}")
            return False
    
    def _preprocess_data(self) -> pd.DataFrame:
        """
        데이터 전처리
        
        Returns:
            전처리된 DataFrame
        """
        df = self.df.copy()
        
        # NaN 값 처리 (이전 값으로 채우기)
        df = df.fillna(method='ffill').fillna(0)
        
        # 무한값 처리
        df = df.replace([np.inf, -np.inf], 0)
        
        # 날짜/시간 컬럼 처리
        if 'Date' in df.columns and 'Time' in df.columns:
            df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], errors='coerce')
        
        return df
    
    def select_sensors(self, sensor_count: int, method: str = 'diverse') -> List[str]:
        """
        센서 개수에 따라 센서를 선택
        
        Args:
            sensor_count: 선택할 센서 개수
            method: 선택 방법 ('diverse', 'random', 'sequential')
            
        Returns:
            선택된 센서 리스트
        """
        if sensor_count > len(self.sensor_list):
            self.logger.warning(f"Requested {sensor_count} sensors but only {len(self.sensor_list)} available")
            sensor_count = len(self.sensor_list)
        
        if method == 'diverse':
            # 다양한 타입의 센서를 고르게 선택
            selected = self._select_diverse_sensors(sensor_count)
        elif method == 'random':
            # 랜덤 선택
            selected = np.random.choice(self.sensor_list, sensor_count, replace=False).tolist()
        else:  # sequential
            # 순차적 선택
            selected = self.sensor_list[:sensor_count]
        
        self.selected_sensors = selected
        self.logger.info(f"Selected {len(selected)} sensors: {selected[:5]}...")
        return selected
    
    def _select_diverse_sensors(self, sensor_count: int) -> List[str]:
        """
        다양한 타입의 센서를 고르게 선택하는 메소드
        
        Args:
            sensor_count: 선택할 센서 개수
            
        Returns:
            선택된 센서 리스트
        """
        # 센서 타입별 분류
        sensor_types = {
            'AIT': [],  # Analytical Instruments (수질 센서)
            'FIT': [],  # Flow Instruments (유량 센서)
            'LT': [],   # Level Transmitters (수위 센서)
            'PIT': [],  # Pressure Instruments (압력 센서)
            'MV': [],   # Motor Valves (밸브 상태)
            'P': [],    # Pumps (펌프 상태)
            'LS': [],   # Level Switches (레벨 스위치)
            'OTHER': [] # 기타
        }
        
        # 센서를 타입별로 분류
        for sensor in self.sensor_list:
            classified = False
            for sensor_type in sensor_types.keys():
                if sensor_type != 'OTHER' and sensor_type in sensor:
                    sensor_types[sensor_type].append(sensor)
                    classified = True
                    break
            if not classified:
                sensor_types['OTHER'].append(sensor)
        
        # 각 타입에서 고르게 선택
        selected = []
        type_counts = {}
        
        # 타입별 선택 개수 계산
        non_empty_types = [t for t in sensor_types.keys() if len(sensor_types[t]) > 0]
        base_count = sensor_count // len(non_empty_types)
        remainder = sensor_count % len(non_empty_types)
        
        for i, sensor_type in enumerate(non_empty_types):
            count = base_count + (1 if i < remainder else 0)
            count = min(count, len(sensor_types[sensor_type]))
            type_counts[sensor_type] = count
        
        # 각 타입에서 센서 선택
        for sensor_type, count in type_counts.items():
            if count > 0:
                available = sensor_types[sensor_type]
                selected.extend(np.random.choice(available, count, replace=False))
        
        # 부족한 경우 추가 선택
        if len(selected) < sensor_count:
            remaining_sensors = [s for s in self.sensor_list if s not in selected]
            additional_count = sensor_count - len(selected)
            if len(remaining_sensors) >= additional_count:
                selected.extend(np.random.choice(remaining_sensors, additional_count, replace=False))
        
        return selected[:sensor_count]
    
    def get_sensor_data(self, sensors: List[str], start_idx: int = 0, count: int = 100) -> List[Dict[str, Any]]:
        """
        지정된 센서들의 데이터를 가져오기
        
        Args:
            sensors: 센서 이름 리스트
            start_idx: 시작 인덱스
            count: 가져올 데이터 개수
            
        Returns:
            센서 데이터 리스트 (각 항목은 timestamp, sensor_values 포함)
        """
        end_idx = min(start_idx + count, len(self.df))
        subset = self.df.iloc[start_idx:end_idx]
        
        data_points = []
        for idx, row in subset.iterrows():
            data_point = {
                'timestamp': row.get('DateTime', pd.Timestamp.now()),
                'row_index': idx,
                'sensor_values': {}
            }
            
            # 선택된 센서들의 값 추출
            for sensor in sensors:
                if sensor in row:
                    data_point['sensor_values'][sensor] = float(row[sensor])
                else:
                    data_point['sensor_values'][sensor] = 0.0
            
            data_points.append(data_point)
        
        return data_points
    
    def get_streaming_data(self, sensors: List[str], frequency: int, duration: int = 30) -> List[Dict[str, Any]]:
        """
        스트리밍 시뮬레이션을 위한 데이터 생성 (올바른 주파수 로직)
        
        Args:
            sensors: 센서 이름 리스트
            frequency: 전체 시스템의 초당 전송 횟수 (Hz)
            duration: 지속 시간 (초)
            
        Returns:
            frequency Hz로 전송할 데이터 포인트 리스트
            총 데이터 포인트 수 = frequency * duration
            
        예시:
            - 50센서, 2Hz, 1000초 → 1초에 2번 전송 (각 전송마다 50센서 데이터) → 총 2,000개 전송
            - 각 전송은 50개 센서의 데이터를 포함
        """
        # 올바른 계산: 주파수 × 시간 (전송 횟수)
        total_transmissions = frequency * duration
        
        # 데이터가 충분하지 않으면 반복 사용
        if total_transmissions > len(self.df):
            repeat_count = (total_transmissions // len(self.df)) + 1
            extended_df = pd.concat([self.df] * repeat_count, ignore_index=True)
        else:
            extended_df = self.df
        
        data_points = []
        
        # 전송 간격 계산 (초)
        interval = 1.0 / frequency  # 1Hz=1초, 2Hz=0.5초, 10Hz=0.1초, 100Hz=0.01초
        
        # 각 전송 시점마다 모든 센서 데이터 생성
        for transmission_idx in range(total_transmissions):
            # 각 전송 시점의 타임스탬프
            timestamp = pd.Timestamp.now() + pd.Timedelta(seconds=transmission_idx * interval)
            
            # 이 전송에서 사용할 데이터 행 선택
            row_idx = transmission_idx % len(extended_df)
            row = extended_df.iloc[row_idx]
            
            # 모든 센서에 대해 데이터 포인트 생성
            for sensor in sensors:
                data_point = {
                    'timestamp': timestamp,
                    'sequence': len(data_points),  # 전체 시퀀스
                    'transmission_id': transmission_idx,  # 몇 번째 전송인지
                    'sensor_id': sensor,  # 어떤 센서인지 명시
                    'sensor_values': {}
                }
                
                # 해당 센서의 값 추출
                if sensor in row:
                    value = row[sensor]
                    # NaN이나 무한값 체크 (안전한 타입 변환)
                    try:
                        float_value = float(value)
                        if pd.isna(float_value) or np.isinf(float_value) or np.isnan(float_value):
                            value = 0.0
                        else:
                            value = float_value
                    except (ValueError, TypeError):
                        value = 0.0
                    data_point['sensor_values'][sensor] = float(value)
                else:
                    data_point['sensor_values'][sensor] = 0.0
                
                data_points.append(data_point)
        
        return data_points
    
    def get_sensor_info(self) -> Dict[str, Any]:
        """
        센서 정보 요약 반환
        
        Returns:
            센서 정보 딕셔너리
        """
        if self.df is None:
            return {}
        
        sensor_info = {
            'total_sensors': len(self.sensor_list),
            'total_records': len(self.df),
            'sensor_types': {},
            'data_range': {},
            'missing_data': {}
        }
        
        # 센서 타입별 분류
        type_patterns = {
            'AIT': 'Analytical Instruments',
            'FIT': 'Flow Instruments', 
            'LT': 'Level Transmitters',
            'PIT': 'Pressure Instruments',
            'MV': 'Motor Valves',
            'P': 'Pumps',
            'LS': 'Level Switches',
            'FIC': 'Flow Controllers',
            'MCV': 'Motor Control Valves',
            'SV': 'Solenoid Valves'
        }
        
        for sensor in self.sensor_list:
            sensor_type = 'OTHER'
            for pattern, description in type_patterns.items():
                if pattern in sensor:
                    sensor_type = f"{pattern} ({description})"
                    break
            
            if sensor_type not in sensor_info['sensor_types']:
                sensor_info['sensor_types'][sensor_type] = []
            sensor_info['sensor_types'][sensor_type].append(sensor)
        
        # 데이터 범위 및 결측값 정보
        for sensor in self.sensor_list[:10]:  # 처음 10개만 상세 분석
            if sensor in self.df.columns:
                values = self.df[sensor].dropna()
                if len(values) > 0:
                    sensor_info['data_range'][sensor] = {
                        'min': float(values.min()),
                        'max': float(values.max()),
                        'mean': float(values.mean()),
                        'std': float(values.std()) if len(values) > 1 else 0.0
                    }
                
                missing_count = self.df[sensor].isna().sum()
                sensor_info['missing_data'][sensor] = {
                    'missing_count': int(missing_count),
                    'missing_percentage': float(missing_count / len(self.df) * 100)
                }
        
        return sensor_info
    
    def save_sensor_selection(self, sensors: List[str], filepath: str):
        """
        선택된 센서 리스트를 파일로 저장
        
        Args:
            sensors: 센서 리스트
            filepath: 저장할 파일 경로
        """
        sensor_data = {
            'selected_sensors': sensors,
            'total_sensors': len(sensors),
            'selection_timestamp': pd.Timestamp.now().isoformat(),
            'sensor_info': {}
        }
        
        # 각 센서별 기본 정보 추가
        for sensor in sensors:
            if sensor in self.df.columns:
                values = self.df[sensor].dropna()
                sensor_data['sensor_info'][sensor] = {
                    'data_points': len(values),
                    'min_value': float(values.min()) if len(values) > 0 else None,
                    'max_value': float(values.max()) if len(values) > 0 else None,
                    'mean_value': float(values.mean()) if len(values) > 0 else None
                }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(sensor_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved sensor selection to {filepath}")

if __name__ == "__main__":
    # 테스트 코드
    loader = WADIDataLoader()
    
    if loader.load_data():
        # 센서 정보 출력
        info = loader.get_sensor_info()
        print(f"Total sensors: {info['total_sensors']}")
        print(f"Total records: {info['total_records']}")
        
        # 각 센서 개수별 테스트
        for sensor_count in [1, 10, 50, 100]:
            print(f"\n=== Testing {sensor_count} sensors ===")
            
            sensors = loader.select_sensors(sensor_count)
            print(f"Selected sensors: {sensors[:5]}...")
            
            # 스트리밍 데이터 생성 테스트
            streaming_data = loader.get_streaming_data(sensors, frequency=1, duration=5)
            print(f"Generated {len(streaming_data)} data points for streaming")
            
            if streaming_data:
                sample = streaming_data[0]
                print(f"Sample data point: {list(sample['sensor_values'].keys())[:3]}...")
                print(f"Sample values: {list(sample['sensor_values'].values())[:3]}")
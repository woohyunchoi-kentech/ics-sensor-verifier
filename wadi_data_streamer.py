#!/usr/bin/env python3
"""
WADI 데이터셋 실시간 스트리밍 시스템
HAI 데이터 스트리머와 동일한 인터페이스 제공
"""

import pandas as pd
import numpy as np
import time
import threading
from typing import List, Dict, Generator, Optional, Tuple
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WADIDataStreamer:
    """WADI 데이터셋 실시간 스트리밍 클래스 (HAI와 동일 인터페이스)"""
    
    def __init__(self, csv_path: str, sensor_list: List[str], frequency_hz: float = 1.0):
        """
        초기화
        
        Args:
            csv_path: WADI CSV 파일 경로
            sensor_list: 스트리밍할 센서 ID 리스트
            frequency_hz: 데이터 전송 빈도 (Hz)
        """
        self.csv_path = Path(csv_path)
        self.sensor_list = sensor_list
        self.frequency_hz = frequency_hz
        self.streaming_interval = 1.0 / frequency_hz
        
        # 데이터 로드
        self.load_data()
        
        # 스트리밍 상태
        self.is_streaming = False
        self.current_index = 0
        self.stream_thread = None
        self.data_buffer = []
        self.buffer_lock = threading.Lock()
        
        logger.info(f"WADI 데이터 스트리머 초기화 완료")
        logger.info(f"  데이터 파일: {csv_path}")
        logger.info(f"  센서 수: {len(sensor_list)}")
        logger.info(f"  주파수: {frequency_hz} Hz")
    
    def load_data(self):
        """WADI CSV 데이터 로드"""
        try:
            logger.info(f"WADI 데이터 로딩 중: {self.csv_path}")
            
            # CSV 로드
            self.raw_data = pd.read_csv(self.csv_path)
            logger.info(f"원본 데이터: {len(self.raw_data)}행 × {len(self.raw_data.columns)}열")
            
            # 센서 컬럼만 추출 (숫자형만)
            numeric_columns = []
            for col in self.raw_data.columns:
                if self.raw_data[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                    if col not in ['Row', 'Date', 'Time']:  # 메타 컬럼 제외
                        numeric_columns.append(col)
            
            self.available_sensors = [f"WADI_{col}" for col in numeric_columns]
            logger.info(f"사용 가능한 센서: {len(self.available_sensors)}개")
            
            # 요청된 센서만 필터링
            self.actual_sensor_columns = []
            for sensor_id in self.sensor_list:
                # WADI_ 프리픽스 제거
                original_col = sensor_id.replace("WADI_", "")
                if original_col in numeric_columns:
                    self.actual_sensor_columns.append(original_col)
            
            if not self.actual_sensor_columns:
                raise ValueError("요청된 센서가 데이터에 존재하지 않습니다")
            
            logger.info(f"실제 사용 센서: {len(self.actual_sensor_columns)}개")
            
            # 센서 데이터만 추출
            self.sensor_data = self.raw_data[self.actual_sensor_columns].copy()
            
            # NaN 값 처리
            self.sensor_data = self.sensor_data.fillna(0.0)
            
            logger.info(f"WADI 데이터 로딩 완료: {len(self.sensor_data)}행")
            
        except Exception as e:
            logger.error(f"WADI 데이터 로딩 실패: {e}")
            raise
    
    def get_current_data(self) -> Optional[Dict[str, float]]:
        """현재 시점의 센서 데이터 반환"""
        if self.current_index >= len(self.sensor_data):
            self.current_index = 0  # 순환
        
        row = self.sensor_data.iloc[self.current_index]
        
        # WADI_ 프리픽스 추가하여 반환
        result = {}
        for i, sensor_col in enumerate(self.actual_sensor_columns):
            sensor_id = f"WADI_{sensor_col}"
            if sensor_id in self.sensor_list:
                result[sensor_id] = float(row[sensor_col])
        
        self.current_index += 1
        return result
    
    def get_batch_data(self, batch_size: int) -> List[Dict[str, float]]:
        """배치 데이터 반환"""
        batch_data = []
        for _ in range(batch_size):
            data_point = self.get_current_data()
            if data_point:
                batch_data.append(data_point)
        return batch_data
    
    def get_sensor_value(self, sensor_id: str) -> float:
        """특정 센서의 현재 값 반환"""
        current_data = self.get_current_data()
        return current_data.get(sensor_id, 0.0)
    
    def get_all_sensor_values(self) -> Dict[str, float]:
        """모든 센서의 현재 값 반환"""
        return self.get_current_data() or {}
    
    def start_streaming(self):
        """데이터 스트리밍 시작"""
        if self.is_streaming:
            logger.warning("이미 스트리밍 중입니다")
            return
        
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
        self.stream_thread.start()
        logger.info(f"WADI 데이터 스트리밍 시작 ({self.frequency_hz} Hz)")
    
    def stop_streaming(self):
        """데이터 스트리밍 중지"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2.0)
        logger.info("WADI 데이터 스트리밍 중지")
    
    def _stream_worker(self):
        """백그라운드 스트리밍 워커"""
        while self.is_streaming:
            try:
                # 현재 데이터 생성
                current_data = self.get_current_data()
                
                if current_data:
                    # 버퍼에 추가
                    with self.buffer_lock:
                        self.data_buffer.append({
                            'timestamp': time.time(),
                            'data': current_data
                        })
                        
                        # 버퍼 크기 제한
                        if len(self.data_buffer) > 1000:
                            self.data_buffer = self.data_buffer[-1000:]
                
                # 주파수에 맞게 대기
                time.sleep(self.streaming_interval)
                
            except Exception as e:
                logger.error(f"스트리밍 오류: {e}")
                time.sleep(1.0)
    
    def get_buffered_data(self, max_items: int = 100) -> List[Dict]:
        """버퍼된 데이터 반환"""
        with self.buffer_lock:
            return self.data_buffer[-max_items:] if self.data_buffer else []
    
    def clear_buffer(self):
        """데이터 버퍼 클리어"""
        with self.buffer_lock:
            self.data_buffer.clear()
    
    def get_statistics(self) -> Dict:
        """스트리밍 통계 반환"""
        return {
            'total_rows': len(self.sensor_data),
            'current_index': self.current_index,
            'sensor_count': len(self.actual_sensor_columns),
            'is_streaming': self.is_streaming,
            'frequency_hz': self.frequency_hz,
            'buffer_size': len(self.data_buffer)
        }

def get_wadi_sensor_list(sensor_count: int = 100) -> List[str]:
    """WADI 센서 ID 목록 반환 (HAI와 동일한 인터페이스)"""
    csv_path = "data/wadi/WADI_14days_new.csv"
    
    try:
        # WADI 데이터에서 센서 컬럼 추출
        data = pd.read_csv(csv_path, nrows=1)  # 첫 행만 읽어서 컬럼 확인
        
        numeric_columns = []
        for col in data.columns:
            if data[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                if col not in ['Row', 'Date', 'Time']:
                    numeric_columns.append(col)
        
        # WADI_ 프리픽스 추가
        wadi_sensors = [f"WADI_{col}" for col in numeric_columns]
        
        # 요청된 수만큼 반환
        return wadi_sensors[:sensor_count]
        
    except Exception as e:
        logger.error(f"WADI 센서 목록 생성 실패: {e}")
        # 기본값 반환
        return [f"WADI_SENSOR_{i:03d}" for i in range(1, sensor_count + 1)]

if __name__ == "__main__":
    # 테스트
    sensor_list = get_wadi_sensor_list(10)
    print(f"WADI 센서 목록 (10개): {sensor_list}")
    
    try:
        streamer = WADIDataStreamer("data/wadi/WADI_14days_new.csv", sensor_list[:5], 1.0)
        
        # 테스트 데이터 생성
        for i in range(3):
            data = streamer.get_current_data()
            print(f"샘플 {i+1}: {data}")
            
        print("✅ WADI 데이터 스트리머 테스트 성공")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
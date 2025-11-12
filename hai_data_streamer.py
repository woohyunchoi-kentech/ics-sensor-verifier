#!/usr/bin/env python3
"""
HAI 데이터셋 실시간 스트리밍 시스템
실제 ICS 센서 데이터를 지정된 빈도로 스트리밍
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

class HAIDataStreamer:
    """HAI 데이터셋 실시간 스트리밍 클래스"""
    
    def __init__(self, csv_path: str, sensor_list: List[str], frequency_hz: float = 1.0):
        """
        초기화
        
        Args:
            csv_path: HAI CSV 파일 경로
            sensor_list: 스트리밍할 센서 ID 리스트
            frequency_hz: 데이터 전송 빈도 (Hz)
        """
        self.csv_path = Path(csv_path)
        self.sensor_list = sensor_list
        self.frequency_hz = frequency_hz
        self.interval = 1.0 / frequency_hz
        
        # 데이터 로드 및 검증
        self._load_and_validate_data()
        
        # 스트리밍 상태
        self.current_index = 0
        self.is_streaming = False
        self.stream_thread = None
        self.data_buffer = []
        
        logger.info(f"HAI 스트리머 초기화 완료: {len(self.sensor_list)}개 센서, {frequency_hz}Hz")
        logger.info(f"사용 가능한 데이터 포인트: {len(self.data)}")
        
    def get_sensor_data_stream(self, sensor_id: str, sample_count: int = 100) -> List[float]:
        """
        특정 센서의 데이터 스트림 반환
        
        Args:
            sensor_id: 센서 ID
            sample_count: 반환할 샘플 수
            
        Returns:
            List[float]: 센서 데이터 리스트
        """
        if self.data is None:
            raise ValueError("데이터가 로드되지 않음")
            
        if sensor_id not in self.data.columns:
            # 센서가 없으면 시뮬레이션 데이터 생성
            return np.random.normal(0, 1, sample_count).tolist()
            
        # 실제 센서 데이터에서 샘플 추출
        sensor_data = self.data[sensor_id].dropna()
        if len(sensor_data) >= sample_count:
            start_idx = np.random.randint(0, len(sensor_data) - sample_count + 1)
            return sensor_data.iloc[start_idx:start_idx + sample_count].tolist()
        else:
            # 데이터가 부족하면 반복해서 채움
            repeated_data = np.tile(sensor_data.values, (sample_count // len(sensor_data)) + 1)
            return repeated_data[:sample_count].tolist()
    
    def _load_and_validate_data(self):
        """HAI CSV 데이터 로드 및 검증"""
        try:
            # CSV 파일 로드
            self.data = pd.read_csv(self.csv_path)
            logger.info(f"HAI 데이터 로드 완료: {self.data.shape}")
            
            # 센서 컬럼 존재 여부 확인
            available_sensors = list(self.data.columns)
            missing_sensors = [s for s in self.sensor_list if s not in available_sensors]
            
            if missing_sensors:
                logger.warning(f"누락된 센서들: {missing_sensors}")
                # 존재하는 센서들만 사용
                self.sensor_list = [s for s in self.sensor_list if s in available_sensors]
                logger.info(f"실제 사용할 센서들: {self.sensor_list}")
            
            if not self.sensor_list:
                raise ValueError("사용 가능한 센서가 없습니다!")
            
            # 센서 데이터만 추출 및 NaN 제거
            self.sensor_data = self.data[self.sensor_list].dropna()
            logger.info(f"센서 데이터 추출 완료: {self.sensor_data.shape}")
            
            # 데이터 통계 출력
            for sensor in self.sensor_list:
                values = self.sensor_data[sensor]
                logger.info(f"센서 {sensor}: min={values.min():.3f}, max={values.max():.3f}, "
                          f"mean={values.mean():.3f}, std={values.std():.3f}")
            
        except Exception as e:
            logger.error(f"HAI 데이터 로드 실패: {e}")
            raise
    
    def get_sensor_batch(self, batch_size: int = 1) -> List[Dict[str, float]]:
        """
        다음 배치 데이터 반환
        
        Args:
            batch_size: 반환할 데이터 포인트 수
            
        Returns:
            센서 데이터 딕셔너리 리스트
        """
        batch_data = []
        
        for _ in range(batch_size):
            if self.current_index >= len(self.sensor_data):
                # 데이터 끝에 도달하면 처음부터 다시 시작
                self.current_index = 0
                logger.info("데이터 끝 도달, 처음부터 재시작")
            
            # 현재 인덱스의 모든 센서 데이터 추출
            row_data = {}
            for sensor in self.sensor_list:
                value = self.sensor_data[sensor].iloc[self.current_index]
                row_data[sensor] = float(value)
            
            batch_data.append({
                'timestamp': time.time(),
                'index': self.current_index,
                'sensors': row_data
            })
            
            self.current_index += 1
        
        return batch_data
    
    def stream_realtime(self) -> Generator[Dict[str, float], None, None]:
        """
        실시간 데이터 스트리밍 제너레이터
        
        Yields:
            센서 데이터 딕셔너리
        """
        logger.info(f"실시간 스트리밍 시작: {self.frequency_hz}Hz")
        
        while True:
            start_time = time.time()
            
            # 다음 데이터 포인트 가져오기
            batch = self.get_sensor_batch(1)
            data_point = batch[0]
            
            yield data_point
            
            # 정확한 타이밍을 위한 대기
            elapsed = time.time() - start_time
            sleep_time = max(0, self.interval - elapsed)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif elapsed > self.interval * 1.5:
                logger.warning(f"스트리밍 지연 발생: {elapsed:.3f}s (목표: {self.interval:.3f}s)")
    
    def start_background_streaming(self, callback_func=None):
        """백그라운드에서 스트리밍 시작"""
        if self.is_streaming:
            logger.warning("이미 스트리밍 중입니다")
            return
        
        self.is_streaming = True
        self.data_buffer.clear()
        
        def stream_worker():
            try:
                for data_point in self.stream_realtime():
                    if not self.is_streaming:
                        break
                    
                    self.data_buffer.append(data_point)
                    
                    # 버퍼 크기 제한 (최대 1000개)
                    if len(self.data_buffer) > 1000:
                        self.data_buffer.pop(0)
                    
                    # 콜백 함수 호출
                    if callback_func:
                        callback_func(data_point)
            except Exception as e:
                logger.error(f"스트리밍 에러: {e}")
                self.is_streaming = False
        
        self.stream_thread = threading.Thread(target=stream_worker, daemon=True)
        self.stream_thread.start()
        logger.info("백그라운드 스트리밍 시작")
    
    def stop_streaming(self):
        """스트리밍 중지"""
        if self.is_streaming:
            self.is_streaming = False
            if self.stream_thread:
                self.stream_thread.join(timeout=2.0)
            logger.info("스트리밍 중지")
    
    def get_latest_data(self, count: int = 1) -> List[Dict]:
        """최근 데이터 반환"""
        return self.data_buffer[-count:] if self.data_buffer else []
    
    def get_sensor_statistics(self) -> Dict[str, Dict[str, float]]:
        """센서별 통계 정보 반환"""
        stats = {}
        for sensor in self.sensor_list:
            values = self.sensor_data[sensor]
            stats[sensor] = {
                'min': float(values.min()),
                'max': float(values.max()),
                'mean': float(values.mean()),
                'std': float(values.std()),
                'count': len(values)
            }
        return stats
    
    def reset_stream(self):
        """스트리밍 위치 초기화"""
        self.current_index = 0
        self.data_buffer.clear()
        logger.info("스트리밍 위치 초기화")

def get_hai_sensor_list(csv_path: str, sensor_count: int = 10) -> List[str]:
    """
    HAI 데이터에서 유효한 센서 리스트 반환
    
    Args:
        csv_path: HAI CSV 파일 경로
        sensor_count: 필요한 센서 수
        
    Returns:
        선택된 센서 ID 리스트
    """
    try:
        data = pd.read_csv(csv_path)
        
        # 센서로 보이는 컬럼들 필터링 (DM-으로 시작하는 것들)
        sensor_columns = [col for col in data.columns if col.startswith('DM-')]
        
        # NaN이 적은 센서들 우선 선택
        sensor_completeness = {}
        for sensor in sensor_columns:
            completeness = (1 - data[sensor].isna().sum() / len(data)) * 100
            sensor_completeness[sensor] = completeness
        
        # 완전성 기준으로 정렬
        sorted_sensors = sorted(sensor_completeness.items(), 
                              key=lambda x: x[1], reverse=True)
        
        selected_sensors = [sensor for sensor, completeness in sorted_sensors[:sensor_count]]
        
        logger.info(f"선택된 센서들:")
        for sensor in selected_sensors:
            completeness = sensor_completeness[sensor]
            logger.info(f"  {sensor}: {completeness:.1f}% 완전성")
        
        return selected_sensors
        
    except Exception as e:
        logger.error(f"센서 리스트 생성 실패: {e}")
        # 기본 센서 리스트 반환
        default_sensors = [
            'DM-PIT01', 'DM-PIT02', 'DM-FT01', 'DM-FT02', 'DM-FT03',
            'DM-LIT01', 'DM-TIT01', 'DM-TIT02', 'DM-PWIT-03', 'DM-LCV01-D'
        ]
        return default_sensors[:sensor_count]

if __name__ == "__main__":
    # 테스트 코드
    csv_path = "data/hai/haiend-23.05/end-train1.csv"
    
    # 10개 센서 선택
    sensors = get_hai_sensor_list(csv_path, 10)
    
    # 스트리머 생성
    streamer = HAIDataStreamer(csv_path, sensors, frequency_hz=2.0)
    
    # 통계 정보 출력
    stats = streamer.get_sensor_statistics()
    print("\n=== 센서 통계 ===")
    for sensor, stat in stats.items():
        print(f"{sensor}: {stat}")
    
    # 실시간 스트리밍 테스트 (5초간)
    print("\n=== 실시간 스트리밍 테스트 ===")
    start_time = time.time()
    
    try:
        for data_point in streamer.stream_realtime():
            elapsed = time.time() - start_time
            print(f"시간: {elapsed:.1f}s, 인덱스: {data_point['index']}, "
                  f"센서 수: {len(data_point['sensors'])}")
            
            # 첫 번째 센서값만 표시
            first_sensor = list(data_point['sensors'].keys())[0]
            first_value = data_point['sensors'][first_sensor]
            print(f"  {first_sensor}: {first_value:.6f}")
            
            if elapsed > 5.0:  # 5초 후 중단
                break
                
    except KeyboardInterrupt:
        print("사용자에 의해 중단됨")
    
    print("스트리밍 테스트 완료")
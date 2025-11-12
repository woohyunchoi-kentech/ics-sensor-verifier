#!/usr/bin/env python3
"""
WADI-CKKS GPU 가속 성능 실험 메인 스크립트
실제 WADI 데이터셋을 사용한 대규모 CKKS 암호화 성능 실험
HAI CKKS 실험과 동일한 구조로 16개 조건 완전 테스트
"""

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')

from performance_monitor import PerformanceMonitor
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest
from safety_controller import SafetyController, SafetyLevel
from visualizer import ExperimentVisualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wadi_ckks_experiment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WADIDataStreamer:
    """WADI 데이터셋 스트리머 (HAI 스트리머와 동일 인터페이스)"""
    
    def __init__(self, csv_path: str):
        """WADI CSV 파일 로드"""
        import pandas as pd
        
        self.csv_path = Path(csv_path)
        logger.info(f"🔄 WADI 데이터셋 로딩: {csv_path}")
        
        self.data = pd.read_csv(csv_path)
        logger.info(f"✅ WADI 데이터 로드 완료: {len(self.data)}행 × {len(self.data.columns)}열")
        
        # 센서 컬럼만 추출 (숫자 데이터)
        self.sensor_columns = []
        for col in self.data.columns:
            if self.data[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                self.sensor_columns.append(col)
        
        logger.info(f"📊 WADI 센서 컬럼 수: {len(self.sensor_columns)}")
        self.current_row = 0
        
        # pandas import를 전역으로 저장
        self.pd = pd
    
    def get_sensor_data(self, sensor_count: int) -> List[Tuple[str, float]]:
        """지정된 수의 센서 데이터 반환"""
        if self.current_row >= len(self.data):
            self.current_row = 0  # 처음부터 다시 시작
        
        row_data = self.data.iloc[self.current_row]
        selected_sensors = self.sensor_columns[:sensor_count]
        
        sensor_data = []
        for sensor_name in selected_sensors:
            value = row_data[sensor_name]
            if self.pd.isna(value):
                value = 0.0  # NaN 값 처리
            sensor_data.append((f"WADI_{sensor_name}", float(value)))
        
        self.current_row += 1
        return sensor_data
    
    def get_available_sensors(self) -> List[str]:
        """사용 가능한 센서 목록 반환"""
        return [f"WADI_{col}" for col in self.sensor_columns]

def get_wadi_sensor_list(sensor_count: int) -> List[str]:
    """WADI 센서 목록 반환"""
    csv_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv"
    streamer = WADIDataStreamer(csv_path)
    return streamer.get_available_sensors()[:sensor_count]

class WADICKKSGPUExperiment:
    """WADI-CKKS GPU 가속 성능 실험 메인 클래스"""
    
    def __init__(self, 
                 csv_path: str,
                 server_host: str = "192.168.0.11",
                 server_port: int = 8085,
                 results_dir: str = "experiment_results"):
        """
        실험 환경 초기화
        
        Args:
            csv_path: WADI 데이터셋 CSV 파일 경로
            server_host: CKKS 서버 호스트
            server_port: CKKS 서버 포트
            results_dir: 결과 저장 디렉토리
        """
        self.csv_path = Path(csv_path)
        self.server_host = server_host
        self.server_port = server_port
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # 시스템 컴포넌트 초기화
        self.data_streamer = None
        self.performance_monitor = None
        self.concurrent_manager = None
        self.safety_controller = None
        self.visualizer = None
        
        # 실험 구성
        self.experiment_matrix = {
            "1": [1, 2, 10, 100],    # 1 센서 × 4 주파수
            "10": [1, 2, 10, 100],   # 10 센서 × 4 주파수  
            "50": [1, 2, 10, 100],   # 50 센서 × 4 주파수
            "100": [1, 2, 10, 100]   # 100 센서 × 4 주파수
        }
        
        logger.info(f"🎯 WADI CKKS 실험 초기화 완료")
        logger.info(f"   • 데이터셋: {csv_path}")
        logger.info(f"   • 서버: {server_host}:{server_port}")
        logger.info(f"   • 실험 매트릭스: 16개 조건 (4×4)")
    
    async def initialize_systems(self):
        """시스템 컴포넌트 초기화"""
        try:
            # 데이터 스트리머 초기화
            self.data_streamer = WADIDataStreamer(self.csv_path)
            
            # 성능 모니터 초기화
            self.performance_monitor = PerformanceMonitor()
            
            # 동시성 관리자 초기화
            self.concurrent_manager = ConcurrentCKKSManager(
                server_host=self.server_host,
                server_port=self.server_port,
                max_concurrent=100
            )
            
            # 안전 제어기 초기화
            self.safety_controller = SafetyController(
                max_cpu_percent=90.0,
                max_memory_percent=85.0,
                max_network_mbps=1000.0
            )
            
            # 시각화 도구 초기화
            self.visualizer = ExperimentVisualizer()
            
            logger.info("✅ 모든 시스템 컴포넌트 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 시스템 초기화 실패: {e}")
            raise
    
    async def run_single_experiment(self,
                                    sensor_count: int,
                                    frequency_hz: int,
                                    duration_seconds: int,
                                    target_requests: Optional[int] = None) -> Dict:
        """
        단일 실험 조건 실행
        
        Args:
            sensor_count: 센서 수
            frequency_hz: 주파수 (Hz)
            duration_seconds: 최대 실행 시간 (초)
            target_requests: 목표 요청 수 (None이면 시간 기준)
            
        Returns:
            실험 결과 딕셔너리
        """
        condition_id = f"{sensor_count}sensors_{frequency_hz}hz"
        logger.info(f"🚀 실험 시작: {condition_id} (목표: {target_requests or 'N/A'}개 요청)")
        
        # 성능 모니터 시작
        self.performance_monitor.start_monitoring()
        
        # 실험 메타데이터
        metadata = {
            "id": condition_id,
            "sensor_count": sensor_count,
            "frequency_hz": frequency_hz,
            "duration": duration_seconds,
            "start_time": time.time(),
            "target_requests": target_requests
        }
        
        # 결과 저장용 리스트
        performance_samples = []
        system_samples = []
        
        # 실험 실행
        experiment_start = time.time()
        sample_count = 0
        
        try:
            while time.time() - experiment_start < duration_seconds:
                # 목표 요청 수 달성 체크
                if target_requests is not None and sample_count >= target_requests:
                    logger.info(f"✅ 목표 요청 수 {target_requests}개 달성!")
                    break
                
                # 안전 체크
                if not await self.safety_controller.is_safe():
                    logger.warning("⚠️ 안전 임계값 초과 - 실험 일시 중단")
                    await asyncio.sleep(1)
                    continue
                
                # 센서 데이터 준비
                sensor_data = self.data_streamer.get_sensor_data(sensor_count)
                
                # CKKS 요청 생성
                requests = []
                for sensor_name, value in sensor_data:
                    request = CKKSRequest(
                        sensor_id=sensor_name,
                        value=value,
                        timestamp=time.time(),
                        sample_id=sample_count
                    )
                    requests.append(request)
                
                # 배치 처리 시작
                batch_start = time.time()
                
                # 동시 CKKS 처리
                results = await self.concurrent_manager.process_batch(requests)
                
                batch_end = time.time()
                
                # 성능 데이터 수집
                successful_requests = sum(1 for r in results if r.success)
                failed_requests = len(results) - successful_requests
                
                performance_sample = {
                    "timestamp": batch_start,
                    "sample_id": sample_count,
                    "sensor_count": len(sensor_data),
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "batch_duration": batch_end - batch_start,
                    "cycle_duration": time.time() - batch_start
                }
                performance_samples.append(performance_sample)
                
                # 시스템 모니터링 데이터
                if sample_count % 10 == 0:  # 10번에 한 번씩 수집
                    system_sample = {
                        "timestamp": time.time(),
                        "metrics": self.performance_monitor.get_current_metrics()
                    }
                    system_samples.append(system_sample)
                
                sample_count += 1
                
                # 주파수 조절 (실제 주파수에 맞춘 대기)
                if frequency_hz > 0:
                    sleep_time = max(0, (1.0 / frequency_hz) - (time.time() - batch_start))
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                
                # 진행 상황 로깅 (100개마다)
                if sample_count % 100 == 0:
                    elapsed = time.time() - experiment_start
                    logger.info(f"   📊 진행: {sample_count}개 완료 ({elapsed:.1f}초 경과)")
        
        except Exception as e:
            logger.error(f"❌ 실험 실행 오류: {e}")
            raise
        
        finally:
            # 성능 모니터 정지
            self.performance_monitor.stop_monitoring()
        
        # 최종 메타데이터
        experiment_end = time.time()
        metadata.update({
            "actual_duration": experiment_end - experiment_start,
            "total_samples": sample_count
        })
        
        # CKKS 통계 수집
        ckks_stats = self.performance_monitor.get_ckks_statistics()
        
        # 안전 이벤트 수집
        safety_events = self.safety_controller.get_safety_events()
        
        result = {
            "metadata": metadata,
            "performance_samples": performance_samples,
            "system_samples": system_samples,
            "ckks_metrics": ckks_stats,
            "safety_events": safety_events
        }
        
        logger.info(f"✅ 실험 완료: {condition_id}")
        logger.info(f"   • 총 샘플: {sample_count}개")
        logger.info(f"   • 소요 시간: {metadata['actual_duration']:.1f}초")
        logger.info(f"   • CKKS 성공률: {ckks_stats.get('success_rate', 0):.1f}%")
        
        return result
    
    async def run_full_experiment(self) -> Dict:
        """전체 16개 조건 실험 실행"""
        logger.info("🎯 WADI CKKS 전체 실험 시작 (16개 조건)")
        
        experiment_start_time = time.time()
        
        # 실험 정보
        experiment_info = {
            "start_time": experiment_start_time,
            "csv_path": str(self.csv_path),
            "server": f"{self.server_host}:{self.server_port}",
            "matrix": self.experiment_matrix
        }
        
        # 전체 결과 저장용
        all_results = {}
        
        try:
            for sensor_count_key, frequencies in self.experiment_matrix.items():
                sensor_count = int(sensor_count_key)
                
                # 센서 그룹별 결과 저장
                sensor_results = {}
                
                for frequency_hz in frequencies:
                    logger.info(f"🔄 실험 진행: {sensor_count}개 센서 × {frequency_hz}Hz")
                    
                    # HMAC 베이스라인과 동일: 1,000개 요청 목표
                    target_requests = 1000
                    
                    # 최대 실행 시간 계산 (여유분 포함)
                    duration_seconds = max(30, target_requests // frequency_hz + 60)
                    
                    try:
                        # 단일 실험 실행
                        experiment_result = await self.run_single_experiment(
                            sensor_count=sensor_count,
                            frequency_hz=frequency_hz,
                            duration_seconds=duration_seconds,
                            target_requests=target_requests
                        )
                        
                        # 주파수별 키 생성
                        freq_key = f"{frequency_hz}hz"
                        sensor_results[freq_key] = experiment_result
                        
                        logger.info(f"✅ 완료: {sensor_count}센서×{frequency_hz}Hz")
                        
                        # 잠시 대기 (시스템 안정화)
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ 실험 실패: {sensor_count}센서×{frequency_hz}Hz - {e}")
                        continue
                
                # 센서 그룹별 결과 저장
                sensor_key = f"{sensor_count}_sensors"
                all_results[sensor_key] = sensor_results
                
                logger.info(f"🎯 센서 그룹 완료: {sensor_count}개 센서 (4개 주파수)")
        
        except Exception as e:
            logger.error(f"❌ 전체 실험 중단: {e}")
            raise
        
        # 실험 완료 정보
        experiment_end_time = time.time()
        experiment_info.update({
            "end_time": experiment_end_time,
            "total_duration": experiment_end_time - experiment_start_time
        })
        
        # 최종 결과 구조
        final_results = {
            "experiment_info": experiment_info,
            "results": all_results
        }
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"wadi_ckks_experiment_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"🎉 WADI CKKS 전체 실험 완료!")
        logger.info(f"   • 총 소요 시간: {experiment_info['total_duration']:.0f}초")
        logger.info(f"   • 결과 저장: {result_file}")
        
        return final_results

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="WADI CKKS GPU 성능 실험")
    parser.add_argument("--csv", 
                       default="/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/wadi/WADI_14days_new.csv",
                       help="WADI CSV 파일 경로")
    parser.add_argument("--server", default="192.168.0.11", help="CKKS 서버 호스트")
    parser.add_argument("--port", type=int, default=8085, help="CKKS 서버 포트")
    parser.add_argument("--results", default="experiment_results", help="결과 저장 디렉토리")
    
    args = parser.parse_args()
    
    # CSV 파일 존재 확인
    if not os.path.exists(args.csv):
        logger.error(f"❌ WADI CSV 파일을 찾을 수 없습니다: {args.csv}")
        return
    
    try:
        # 실험 인스턴스 생성
        experiment = WADICKKSGPUExperiment(
            csv_path=args.csv,
            server_host=args.server,
            server_port=args.port,
            results_dir=args.results
        )
        
        # 시스템 초기화
        await experiment.initialize_systems()
        
        # 전체 실험 실행
        results = await experiment.run_full_experiment()
        
        logger.info("🎊 WADI CKKS 실험이 성공적으로 완료되었습니다!")
        
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 실험이 중단되었습니다")
    except Exception as e:
        logger.error(f"❌ 실험 실행 중 오류: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
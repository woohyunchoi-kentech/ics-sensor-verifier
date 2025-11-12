#!/usr/bin/env python3
"""
HAI-CKKS GPU 가속 성능 실험 메인 스크립트
실제 HAI 데이터셋을 사용한 대규모 CKKS 암호화 성능 실험
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

from hai_data_streamer import HAIDataStreamer, get_hai_sensor_list
from wadi_data_streamer import WADIDataStreamer, get_wadi_sensor_list
from performance_monitor import PerformanceMonitor
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest
from safety_controller import SafetyController, SafetyLevel
from visualizer import ExperimentVisualizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hai_ckks_experiment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HAICKKSGPUExperiment:
    """HAI-CKKS GPU 가속 성능 실험 메인 클래스"""
    
    def __init__(self, 
                 csv_path: str,
                 server_host: str = "192.168.0.11",
                 server_port: int = 8085,
                 results_dir: str = "experiment_results"):
        """
        실험 환경 초기화
        
        Args:
            csv_path: HAI 데이터셋 CSV 파일 경로
            server_host: CKKS 서버 호스트
            server_port: CKKS 서버 포트
            results_dir: 결과 저장 디렉토리
        """
        self.csv_path = Path(csv_path)
        self.server_host = server_host
        self.server_port = server_port
        self.results_dir = Path(results_dir)
        
        # 결과 디렉토리 생성
        self.results_dir.mkdir(exist_ok=True)
        
        # 실험 매트릭스 정의 (HMAC 베이스라인과 동일한 16조건)
        self.experiment_matrix = {
            1: [1, 2, 10, 100],      # 1개 센서: 1, 2, 10, 100Hz
            10: [1, 2, 10, 100],     # 10개 센서: 1, 2, 10, 100Hz  
            50: [1, 2, 10, 100],     # 50개 센서: 1, 2, 10, 100Hz
            100: [1, 2, 10, 100]     # 100개 센서: 1, 2, 10, 100Hz
        }
        
        # 컴포넌트 초기화
        self.performance_monitor = PerformanceMonitor()
        self.safety_controller = SafetyController()
        self.visualizer = ExperimentVisualizer()
        
        # 실험 상태
        self.current_experiment = None
        self.experiment_results = {}
        self.start_time = None
        
        logger.info(f"HAI-CKKS GPU 실험 시스템 초기화 완료")
        logger.info(f"데이터셋: {self.csv_path}")
        logger.info(f"서버: {self.server_host}:{self.server_port}")
        logger.info(f"결과 디렉토리: {self.results_dir}")
    
    async def validate_server_connection(self) -> bool:
        """CKKS 서버 연결 검증"""
        try:
            server_url = f"http://{self.server_host}:{self.server_port}"
            manager = ConcurrentCKKSManager(
                server_url=server_url,
                max_concurrent=1
            )
            
            # 테스트 요청 생성
            test_request = CKKSRequest(
                sensor_id="TEST-01",
                value=1.0,
                timestamp=time.time(),
                request_id="test_001"
            )
            
            # 단일 요청 테스트
            response = await manager.send_single_request_async(test_request)
            
            if response.success:
                logger.info("✓ CKKS 서버 연결 성공")
                logger.info(f"  서버 응답시간: {response.response_time_ms:.3f}ms")
                return True
            else:
                logger.error(f"✗ CKKS 서버 연결 실패: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"✗ 서버 연결 검증 실패: {e}")
            return False
    
    def prepare_sensor_data(self, sensor_count: int, dataset_type: str = "hai") -> List[str]:
        """실험용 센서 데이터 준비"""
        try:
            if dataset_type == "wadi":
                # WADI 데이터셋에서 센서 선택
                available_sensors = get_wadi_sensor_list(sensor_count)
            else:
                # HAI 데이터셋에서 센서 선택
                available_sensors = get_hai_sensor_list(str(self.csv_path), sensor_count)
            
            if len(available_sensors) < sensor_count:
                logger.warning(f"요청된 센서 수 {sensor_count}개보다 적은 {len(available_sensors)}개만 사용 가능")
                sensor_count = len(available_sensors)
            
            selected_sensors = available_sensors[:sensor_count]
            logger.info(f"{dataset_type.upper()} 선택된 센서 ({len(selected_sensors)}개): {selected_sensors[:3]}...")
            
            return selected_sensors
            
        except Exception as e:
            logger.error(f"센서 데이터 준비 실패: {e}")
            raise
    
    async def run_single_experiment(self, 
                                  sensor_count: int, 
                                  frequency_hz: float,
                                  duration_seconds: int = 60,
                                  target_requests: int = None,
                                  dataset_type: str = "hai") -> Dict:
        """단일 실험 실행"""
        
        experiment_id = f"{sensor_count}sensors_{frequency_hz}hz"
        if target_requests:
            logger.info(f"🚀 실험 시작: {experiment_id} (목표: {target_requests}개 요청, 최대 {duration_seconds}초)")
        else:
            logger.info(f"🚀 실험 시작: {experiment_id} ({duration_seconds}초)")
        
        self.current_experiment = {
            'id': experiment_id,
            'sensor_count': sensor_count,
            'frequency_hz': frequency_hz,
            'duration': duration_seconds,
            'start_time': time.time()
        }
        
        try:
            # 1. 센서 데이터 준비
            sensors = self.prepare_sensor_data(sensor_count, dataset_type)
            
            # 2. 데이터 스트리머 생성
            if dataset_type == "wadi":
                streamer = WADIDataStreamer(
                    csv_path=str(self.csv_path),
                    sensor_list=sensors,
                    frequency_hz=frequency_hz
                )
            else:
                streamer = HAIDataStreamer(
                    csv_path=str(self.csv_path),
                    sensor_list=sensors,
                    frequency_hz=frequency_hz
                )
            
            # 3. CKKS 매니저 생성 (동시성 제한)
            max_concurrent = min(sensor_count * 2, 50)  # 과부하 방지
            server_url = f"http://{self.server_host}:{self.server_port}"
            manager = ConcurrentCKKSManager(
                server_url=server_url,
                max_concurrent=max_concurrent
            )
            
            # 4. 성능 모니터링 시작
            self.performance_monitor.start_monitoring()
            
            # 5. 실험 데이터 수집
            experiment_data = {
                'metadata': self.current_experiment.copy(),
                'performance_samples': [],
                'system_samples': [],
                'ckks_metrics': [],
                'safety_events': []
            }
            
            # 6. 실시간 데이터 스트리밍 및 CKKS 처리
            experiment_start = time.time()
            sample_count = 0
            
            while time.time() - experiment_start < duration_seconds and (target_requests is None or sample_count < target_requests):
                cycle_start = time.time()
                
                # 안전성 확인
                is_safe, warnings = self.safety_controller.is_safe_to_continue()
                if not is_safe:
                    logger.error(f"⚠️ 안전성 문제로 실험 중단: {warnings}")
                    experiment_data['safety_events'].append({
                        'timestamp': time.time(),
                        'event': 'experiment_stopped',
                        'reasons': warnings
                    })
                    break
                
                # HAI 데이터 배치 가져오기
                batch_data = streamer.get_sensor_batch(len(sensors))
                current_data = batch_data[0]
                
                # CKKS 요청 생성
                requests = []
                for i, (sensor_id, value) in enumerate(current_data['sensors'].items()):
                    request = CKKSRequest(
                        sensor_id=sensor_id,
                        value=value,
                        timestamp=current_data['timestamp'],
                        request_id=f"{sample_count}_{i}"
                    )
                    requests.append(request)
                
                # 배치 CKKS 처리
                batch_start = time.time()
                responses = await manager.send_batch_requests_async(requests)
                batch_duration = time.time() - batch_start
                
                # 성능 메트릭 기록
                successful_responses = [r for r in responses if r.success]
                failed_responses = [r for r in responses if not r.success]
                
                if successful_responses:
                    avg_encryption_time = sum(r.encryption_time_ms for r in successful_responses if r.encryption_time_ms) / len(successful_responses)
                    # decryption_time은 CKKSResponse에 없으므로 0으로 설정
                    avg_decryption_time = 0
                    avg_response_time = sum(r.response_time_ms for r in successful_responses) / len(successful_responses)
                    
                    self.performance_monitor.record_ckks_metric(
                        encryption_time=avg_encryption_time,
                        decryption_time=avg_decryption_time,
                        response_time=avg_response_time
                    )
                
                # 실험 데이터 기록
                sample_data = {
                    'timestamp': time.time(),
                    'sample_id': sample_count,
                    'sensor_count': len(requests),
                    'successful_requests': len(successful_responses),
                    'failed_requests': len(failed_responses),
                    'batch_duration': batch_duration,
                    'cycle_duration': time.time() - cycle_start
                }
                experiment_data['performance_samples'].append(sample_data)
                
                # 시스템 메트릭 기록 (5초마다)
                if sample_count % (frequency_hz * 5) == 0:
                    system_metrics = self.performance_monitor.get_current_system_status()
                    experiment_data['system_samples'].append({
                        'timestamp': time.time(),
                        'metrics': system_metrics
                    })
                
                # 안전성 확인 (간단한 체크)
                current_status = self.performance_monitor.get_current_system_status()
                cpu_usage = current_status.get('cpu_percent', 0)
                memory_usage = current_status.get('memory_percent', 0)
                
                # 높은 부하 시 경고 로그
                if cpu_usage > 80:
                    logger.warning(f"높은 CPU 사용률: {cpu_usage:.1f}%")
                if memory_usage > 80:
                    logger.warning(f"높은 메모리 사용률: {memory_usage:.1f}%")
                
                sample_count += 1
                
                # 주기 조절
                cycle_duration = time.time() - cycle_start
                target_interval = 1.0 / frequency_hz
                sleep_time = max(0, target_interval - cycle_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                elif cycle_duration > target_interval * 1.5:
                    logger.warning(f"주기 지연: {cycle_duration:.3f}s (목표: {target_interval:.3f}s)")
            
            # 7. 실험 종료 및 결과 정리
            experiment_duration = time.time() - experiment_start
            experiment_data['metadata']['actual_duration'] = experiment_duration
            experiment_data['metadata']['total_samples'] = sample_count
            
            # CKKS 메트릭 수집
            ckks_metrics = self.performance_monitor.get_ckks_statistics()
            experiment_data['ckks_metrics'] = ckks_metrics
            
            logger.info(f"✅ 실험 완료: {experiment_id}")
            logger.info(f"   실행 시간: {experiment_duration:.1f}초")
            logger.info(f"   총 샘플: {sample_count}개")
            logger.info(f"   평균 응답시간: {ckks_metrics.get('avg_response_time', 0):.3f}ms")
            
            return experiment_data
            
        except Exception as e:
            logger.error(f"❌ 실험 실행 중 오류: {e}")
            raise
        
        finally:
            # 성능 모니터링 정지
            self.performance_monitor.stop_monitoring()
            self.current_experiment = None
    
    async def run_full_experiment_matrix(self) -> Dict:
        """전체 실험 매트릭스 실행"""
        
        logger.info("🎯 전체 실험 매트릭스 시작")
        logger.info(f"실험 조건: {sum(len(freqs) for freqs in self.experiment_matrix.values())}개")
        
        self.start_time = time.time()
        all_results = {
            'experiment_info': {
                'start_time': self.start_time,
                'csv_path': str(self.csv_path),
                'server': f"{self.server_host}:{self.server_port}",
                'matrix': self.experiment_matrix
            },
            'results': {}
        }
        
        try:
            # 서버 연결 검증
            if not await self.validate_server_connection():
                raise RuntimeError("CKKS 서버 연결 실패")
            
            total_experiments = sum(len(freqs) for freqs in self.experiment_matrix.values())
            completed_experiments = 0
            
            # 각 센서 수별로 실험 실행
            for sensor_count, frequencies in self.experiment_matrix.items():
                logger.info(f"\n📊 {sensor_count}개 센서 실험 시작")
                
                sensor_results = {}
                
                for frequency_hz in frequencies:
                    try:
                        # 단일 실험 실행 (1000개 요청 기준)
                        target_requests = 1000
                        duration_seconds = max(30, target_requests // frequency_hz)
                        experiment_result = await self.run_single_experiment(
                            sensor_count=sensor_count,
                            frequency_hz=frequency_hz,
                            duration_seconds=duration_seconds,
                            target_requests=target_requests
                        )
                        
                        sensor_results[f"{frequency_hz}hz"] = experiment_result
                        completed_experiments += 1
                        
                        # 진행률 표시
                        progress = (completed_experiments / total_experiments) * 100
                        logger.info(f"📈 전체 진행률: {progress:.1f}% ({completed_experiments}/{total_experiments})")
                        
                        # 실험 간 휴식 시간 (서버 부하 완화)
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"❌ 실험 실패 ({sensor_count}센서, {frequency_hz}Hz): {e}")
                        sensor_results[f"{frequency_hz}hz"] = {
                            'error': str(e),
                            'timestamp': time.time()
                        }
                
                all_results['results'][f"{sensor_count}_sensors"] = sensor_results
                
                # 센서 그룹별 휴식 시간
                logger.info(f"⏸️ {sensor_count}개 센서 실험 완료, 10초 대기...")
                await asyncio.sleep(10)
            
            # 실험 완료
            total_duration = time.time() - self.start_time
            all_results['experiment_info']['end_time'] = time.time()
            all_results['experiment_info']['total_duration'] = total_duration
            
            logger.info(f"\n🎉 전체 실험 완료!")
            logger.info(f"   총 실행 시간: {total_duration/60:.1f}분")
            logger.info(f"   완료된 실험: {completed_experiments}/{total_experiments}")
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ 실험 매트릭스 실행 실패: {e}")
            raise
    
    def save_results(self, results: Dict, filename_prefix: str = None) -> str:
        """실험 결과 저장"""
        
        if filename_prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"hai_ckks_experiment_{timestamp}"
        
        # JSON 결과 저장
        json_path = self.results_dir / f"{filename_prefix}.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 실험 결과 저장: {json_path}")
        return str(json_path)
    
    def generate_visualizations(self, results: Dict, output_prefix: str = None) -> List[str]:
        """실험 결과 시각화 생성"""
        
        if output_prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_prefix = f"hai_ckks_viz_{timestamp}"
        
        visualization_files = []
        
        try:
            # 각 실험별 시각화 생성
            for sensor_key, sensor_results in results['results'].items():
                sensor_count = int(sensor_key.split('_')[0])
                
                for freq_key, experiment_data in sensor_results.items():
                    if 'error' in experiment_data:
                        continue
                    
                    frequency = float(freq_key.replace('hz', ''))
                    
                    # 성능 차트 생성
                    if experiment_data.get('performance_samples'):
                        chart_path = self.visualizer.create_realtime_performance_chart(
                            sensor_count=sensor_count,
                            performance_data=experiment_data['performance_samples'],
                            system_data=experiment_data.get('system_samples', [])
                        )
                        if chart_path:
                            visualization_files.append(chart_path)
            
            # 종합 비교 차트 생성
            summary_path = self.visualizer.create_experiment_summary_chart(results)
            if summary_path:
                visualization_files.append(summary_path)
            
            logger.info(f"📊 시각화 생성 완료: {len(visualization_files)}개 파일")
            for file_path in visualization_files:
                logger.info(f"   📈 {file_path}")
            
            return visualization_files
            
        except Exception as e:
            logger.error(f"시각화 생성 실패: {e}")
            return []

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="HAI-CKKS GPU 가속 성능 실험")
    parser.add_argument("--csv", required=True, help="데이터셋 CSV 파일 경로")
    parser.add_argument("--dataset", choices=["hai", "wadi"], default="hai", help="데이터셋 유형 (hai 또는 wadi)")
    parser.add_argument("--host", default="192.168.0.11", help="CKKS 서버 호스트")
    parser.add_argument("--port", type=int, default=8085, help="CKKS 서버 포트")
    parser.add_argument("--results", default="experiment_results", help="결과 저장 디렉토리")
    parser.add_argument("--test-connection", action="store_true", help="서버 연결 테스트만 실행")
    
    args = parser.parse_args()
    
    # HAI CSV 파일 존재 확인
    if not Path(args.csv).exists():
        logger.error(f"HAI 데이터셋 파일을 찾을 수 없습니다: {args.csv}")
        sys.exit(1)
    
    try:
        # 실험 시스템 생성
        experiment = HAICKKSGPUExperiment(
            csv_path=args.csv,
            server_host=args.host,
            server_port=args.port,
            results_dir=args.results
        )
        
        # 서버 연결 테스트만 실행
        if args.test_connection:
            logger.info("🔍 서버 연결 테스트 실행...")
            if await experiment.validate_server_connection():
                logger.info("✅ 서버 연결 성공!")
                sys.exit(0)
            else:
                logger.error("❌ 서버 연결 실패!")
                sys.exit(1)
        
        # 전체 실험 실행
        logger.info("🚀 HAI-CKKS GPU 실험 시작...")
        
        results = await experiment.run_full_experiment_matrix()
        
        # 결과 저장
        result_file = experiment.save_results(results)
        
        # 시각화 생성
        visualization_files = experiment.generate_visualizations(results)
        
        logger.info("\n🎉 실험 완료!")
        logger.info(f"📁 결과 파일: {result_file}")
        logger.info(f"📊 시각화 파일: {len(visualization_files)}개")
        
    except KeyboardInterrupt:
        logger.info("❌ 사용자에 의해 실험 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 실험 실행 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
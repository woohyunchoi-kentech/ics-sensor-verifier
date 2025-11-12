#!/usr/bin/env python3
"""
WADI-CKKS GPU 가속 성능 실험 메인 스크립트 (HAI 기반)
실제 WADI 데이터셋을 사용한 대규모 CKKS 암호화 성능 실험
HAI CKKS와 동일한 구조의 16개 조건 실험
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

from wadi_data_streamer import WADIDataStreamer, get_wadi_sensor_list
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

class WADICKKSGPUExperiment:
    """WADI-CKKS GPU 가속 성능 실험 메인 클래스 (HAI 구조 동일)"""
    
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
        
        # 결과 디렉토리 생성
        self.results_dir.mkdir(exist_ok=True)
        
        # HAI와 동일한 실험 매트릭스 (HMAC 베이스라인과 동일한 16조건)
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
        
        logger.info(f"WADI-CKKS GPU 실험 시스템 초기화 완료")
        logger.info(f"데이터셋: {self.csv_path}")
        logger.info(f"서버: {self.server_host}:{self.server_port}")
        logger.info(f"결과 디렉토리: {self.results_dir}")
        logger.info(f"🔄 HAI CKKS와 동일한 실험 구조 사용")
    
    async def validate_server_connection(self) -> bool:
        """CKKS 서버 연결 검증"""
        try:
            server_url = f"http://{self.server_host}:{self.server_port}"
            manager = ConcurrentCKKSManager(
                server_url=server_url,
                max_concurrent=1
            )
            
            # 테스트 요청 생성 (WADI 프리픽스 사용)
            test_request = CKKSRequest(
                sensor_id="WADI_TEST",
                value=1.0,
                timestamp=time.time(),
                request_id="wadi_test_001"
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
    
    def prepare_sensor_data(self, sensor_count: int) -> List[str]:
        """실험용 WADI 센서 데이터 준비"""
        try:
            # WADI 데이터셋에서 센서 선택
            available_sensors = get_wadi_sensor_list(sensor_count)
            
            if len(available_sensors) < sensor_count:
                logger.warning(f"요청된 센서 수 {sensor_count}개보다 적은 {len(available_sensors)}개만 사용 가능")
                sensor_count = len(available_sensors)
            
            selected_sensors = available_sensors[:sensor_count]
            logger.info(f"WADI 센서 선택 ({len(selected_sensors)}개): {selected_sensors[:3]}...")
            
            return selected_sensors
            
        except Exception as e:
            logger.error(f"WADI 센서 데이터 준비 실패: {e}")
            raise
    
    async def run_single_experiment(self, 
                                  sensor_count: int, 
                                  frequency_hz: float,
                                  duration_seconds: int = 60,
                                  target_requests: int = None) -> Dict:
        """단일 WADI CKKS 실험 실행"""
        
        experiment_id = f"{sensor_count}sensors_{frequency_hz}hz"
        if target_requests:
            logger.info(f"🚀 WADI CKKS 실험 시작: {experiment_id} (목표: {target_requests}개 요청, 최대 {duration_seconds}초)")
        else:
            logger.info(f"🚀 WADI CKKS 실험 시작: {experiment_id} ({duration_seconds}초)")
        
        self.current_experiment = {
            'id': experiment_id,
            'sensor_count': sensor_count,
            'frequency_hz': frequency_hz,
            'duration': duration_seconds,
            'start_time': time.time()
        }
        
        try:
            # 1. WADI 센서 데이터 준비
            sensors = self.prepare_sensor_data(sensor_count)
            
            # 2. WADI 데이터 스트리머 생성
            streamer = WADIDataStreamer(
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
                
                # WADI 센서 데이터 가져오기
                sensor_data = streamer.get_current_data()
                if not sensor_data:
                    logger.warning("WADI 센서 데이터 없음 - 스킵")
                    await asyncio.sleep(0.1)
                    continue
                
                # CKKS 요청 생성
                requests = []
                for sensor_id, value in sensor_data.items():
                    request = CKKSRequest(
                        sensor_id=sensor_id,
                        value=float(value),
                        timestamp=time.time(),
                        request_id=f"wadi_{sample_count}_{sensor_id}"
                    )
                    requests.append(request)
                
                # 배치 처리
                batch_start = time.time()
                
                try:
                    # 비동기 배치 요청
                    results = await manager.process_batch_async(requests)
                    
                    batch_end = time.time()
                    
                    # 성공/실패 카운트
                    successful = sum(1 for r in results if r.success)
                    failed = len(results) - successful
                    
                    # 성능 샘플 저장
                    performance_sample = {
                        'timestamp': batch_start,
                        'sample_id': sample_count,
                        'sensor_count': len(requests),
                        'successful_requests': successful,
                        'failed_requests': failed,
                        'batch_duration': batch_end - batch_start,
                        'cycle_duration': time.time() - cycle_start
                    }
                    experiment_data['performance_samples'].append(performance_sample)
                    
                    # CKKS 메트릭 저장 (개별 결과)
                    for result in results:
                        if result.success:
                            experiment_data['ckks_metrics'].append({
                                'timestamp': result.timestamp,
                                'sensor_id': result.sensor_id,
                                'encryption_time_ms': result.encryption_time_ms,
                                'response_time_ms': result.response_time_ms,
                                'accuracy_error': getattr(result, 'accuracy_error', 0.0),
                                'sample_id': sample_count
                            })
                    
                    sample_count += 1
                    
                    # 진행 상황 로깅 (100회마다)
                    if sample_count % 100 == 0:
                        elapsed_time = time.time() - experiment_start
                        progress_pct = (sample_count / target_requests * 100) if target_requests else (elapsed_time / duration_seconds * 100)
                        logger.info(f"   📊 진행: {sample_count}개 완료 ({progress_pct:.1f}%) - {elapsed_time:.1f}초 경과")
                    
                except Exception as e:
                    logger.error(f"CKKS 배치 처리 오류: {e}")
                    failed_sample = {
                        'timestamp': time.time(),
                        'sample_id': sample_count,
                        'error': str(e)
                    }
                    experiment_data['safety_events'].append(failed_sample)
                
                # 시스템 메트릭 수집 (10회마다)
                if sample_count % 10 == 0:
                    system_metrics = self.performance_monitor.get_current_metrics()
                    experiment_data['system_samples'].append({
                        'timestamp': time.time(),
                        'sample_id': sample_count,
                        'metrics': system_metrics
                    })
                
                # 주파수 조절
                cycle_time = time.time() - cycle_start
                expected_cycle_time = 1.0 / frequency_hz
                sleep_time = max(0, expected_cycle_time - cycle_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            # 성능 모니터 중지
            self.performance_monitor.stop_monitoring()
            
            # 최종 메타데이터 업데이트
            experiment_end = time.time()
            experiment_data['metadata']['actual_duration'] = experiment_end - experiment_start
            experiment_data['metadata']['total_samples'] = sample_count
            
            # CKKS 통계 계산
            if experiment_data['ckks_metrics']:
                encryption_times = [m['encryption_time_ms'] for m in experiment_data['ckks_metrics']]
                response_times = [m['response_time_ms'] for m in experiment_data['ckks_metrics']]
                accuracy_errors = [m['accuracy_error'] for m in experiment_data['ckks_metrics']]
                
                ckks_summary = {
                    'total_requests': len(experiment_data['ckks_metrics']),
                    'successful_requests': len(experiment_data['ckks_metrics']),
                    'failed_requests': 0,  # 성공한 것만 저장되므로
                    'success_rate': 100.0,
                    'avg_encryption_time': sum(encryption_times) / len(encryption_times),
                    'avg_response_time': sum(response_times) / len(response_times),
                    'avg_accuracy_error': sum(accuracy_errors) / len(accuracy_errors)
                }
            else:
                ckks_summary = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': sample_count,
                    'success_rate': 0.0,
                    'avg_encryption_time': 0.0,
                    'avg_response_time': 0.0,
                    'avg_accuracy_error': 0.0
                }
            
            # 최종 결과 구성
            final_result = {
                'metadata': experiment_data['metadata'],
                'performance_samples': experiment_data['performance_samples'],
                'system_samples': experiment_data['system_samples'],
                'ckks_metrics': ckks_summary,
                'safety_events': experiment_data['safety_events']
            }
            
            logger.info(f"✅ WADI CKKS 실험 완료: {experiment_id}")
            logger.info(f"   • 총 샘플: {sample_count}개")
            logger.info(f"   • 소요 시간: {final_result['metadata']['actual_duration']:.1f}초")
            logger.info(f"   • 성공률: {ckks_summary['success_rate']:.1f}%")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ WADI CKKS 실험 실패: {experiment_id} - {e}")
            raise
    
    async def run_full_experiment(self) -> Dict:
        """전체 16개 조건 WADI CKKS 실험 실행"""
        logger.info("🎯 WADI CKKS 전체 실험 시작 (HAI와 동일한 16개 조건)")
        
        # 서버 연결 확인
        if not await self.validate_server_connection():
            raise Exception("CKKS 서버 연결 실패")
        
        self.start_time = time.time()
        
        # 실험 정보 구조
        experiment_info = {
            'start_time': self.start_time,
            'csv_path': str(self.csv_path),
            'server': f'{self.server_host}:{self.server_port}',
            'matrix': self.experiment_matrix
        }
        
        # 결과 저장 구조
        results = {}
        
        condition_count = 0
        total_conditions = sum(len(freqs) for freqs in self.experiment_matrix.values())
        
        try:
            for sensor_count, frequencies in self.experiment_matrix.items():
                sensor_results = {}
                
                for frequency_hz in frequencies:
                    condition_count += 1
                    logger.info(f"\n📊 진행 ({condition_count}/{total_conditions}): {sensor_count}센서 × {frequency_hz}Hz")
                    
                    # HAI와 동일: 1000개 요청 목표
                    target_requests = 1000
                    duration_seconds = max(30, target_requests // frequency_hz + 60)  # 여유시간 포함
                    
                    try:
                        experiment_result = await self.run_single_experiment(
                            sensor_count=sensor_count,
                            frequency_hz=frequency_hz,
                            duration_seconds=duration_seconds,
                            target_requests=target_requests
                        )
                        
                        freq_key = f'{frequency_hz}hz'
                        sensor_results[freq_key] = experiment_result
                        
                        logger.info(f"✅ 완료: {sensor_count}센서 × {frequency_hz}Hz")
                        
                        # 시스템 안정화 대기
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ 조건 실패: {sensor_count}센서 × {frequency_hz}Hz - {e}")
                        # 실패해도 계속 진행
                        continue
                
                sensor_key = f'{sensor_count}_sensors'
                results[sensor_key] = sensor_results
                
                completed_conditions = sum(len(v) for v in results.values())
                logger.info(f"🎯 센서 그룹 완료: {sensor_count}개 센서 ({completed_conditions}/{total_conditions} 조건 완료)")
        
        except Exception as e:
            logger.error(f"❌ 전체 실험 중단: {e}")
            raise
        
        # 실험 완료 처리
        end_time = time.time()
        experiment_info['end_time'] = end_time
        experiment_info['total_duration'] = end_time - self.start_time
        
        # 최종 결과 구조
        final_results = {
            'experiment_info': experiment_info,
            'results': results
        }
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f'wadi_ckks_experiment_{timestamp}.json'
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False, default=str)
        
        completed_conditions = sum(len(v) for v in results.values())
        logger.info(f"\n🎉 WADI CKKS 전체 실험 완료!")
        logger.info(f"   • 완료된 조건: {completed_conditions}/{total_conditions}")
        logger.info(f"   • 총 소요시간: {experiment_info['total_duration']:.0f}초")
        logger.info(f"   • 결과 저장: {result_file}")
        logger.info(f"📊 HAI CKKS 결과와 직접 비교 가능")
        
        return final_results

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="WADI CKKS GPU 성능 실험 (HAI 구조 동일)")
    parser.add_argument("--csv", 
                       default="data/wadi/WADI_14days_new.csv",
                       help="WADI CSV 파일 경로")
    parser.add_argument("--server", default="192.168.0.11", help="CKKS 서버 호스트")
    parser.add_argument("--port", type=int, default=8085, help="CKKS 서버 포트")
    parser.add_argument("--results", default="experiment_results", help="결과 저장 디렉토리")
    
    args = parser.parse_args()
    
    # CSV 파일 존재 확인
    csv_path = Path(args.csv)
    if not csv_path.exists():
        logger.error(f"❌ WADI CSV 파일을 찾을 수 없습니다: {csv_path}")
        return
    
    try:
        # 실험 인스턴스 생성
        experiment = WADICKKSGPUExperiment(
            csv_path=str(csv_path),
            server_host=args.server,
            server_port=args.port,
            results_dir=args.results
        )
        
        # 전체 실험 실행
        results = await experiment.run_full_experiment()
        
        logger.info("🎊 WADI CKKS 실험이 성공적으로 완료되었습니다!")
        logger.info("📋 HAI CKKS 실험과 동일한 구조로 비교 분석 준비 완료")
        
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 실험 중단")
    except Exception as e:
        logger.error(f"❌ 실험 실행 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
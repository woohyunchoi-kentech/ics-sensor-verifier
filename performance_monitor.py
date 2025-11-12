#!/usr/bin/env python3
"""
실시간 성능 모니터링 시스템
GPU/CPU 사용률, 네트워크 성능, 암호화 성능 실시간 추적
"""

import time
import psutil
import threading
import queue
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
import json
import csv
from pathlib import Path
import logging

# GPU 모니터링을 위한 라이브러리 (선택적)
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    logging.warning("GPUtil 없음 - GPU 모니터링 비활성화")

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.dates import DateFormatter
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
    NUMPY_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib 없음 - 실시간 시각화 비활성화")
    try:
        import numpy as np
        NUMPY_AVAILABLE = True
    except ImportError:
        NUMPY_AVAILABLE = False
        logging.warning("NumPy 없음 - 통계 계산 제한적")

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """실시간 성능 모니터링 클래스"""
    
    def __init__(self, max_history: int = 1000):
        """
        초기화
        
        Args:
            max_history: 메트릭 히스토리 최대 보관 수
        """
        self.max_history = max_history
        self.is_monitoring = False
        self.monitor_thread = None
        
        # 메트릭 데이터 저장소
        self.metrics = {
            'timestamps': deque(maxlen=max_history),
            'cpu_percent': deque(maxlen=max_history),
            'memory_percent': deque(maxlen=max_history),
            'memory_used_gb': deque(maxlen=max_history),
            'gpu_percent': deque(maxlen=max_history),
            'gpu_memory_percent': deque(maxlen=max_history),
            'network_bytes_sent': deque(maxlen=max_history),
            'network_bytes_recv': deque(maxlen=max_history),
        }
        
        # 실험별 성능 데이터
        self.experiment_data = defaultdict(list)
        
        # CKKS 성능 메트릭
        self.ckks_metrics = {
            'encryption_times': deque(maxlen=max_history),
            'decryption_times': deque(maxlen=max_history),
            'response_times': deque(maxlen=max_history),
            'accuracy_errors': deque(maxlen=max_history),
            'request_counts': deque(maxlen=max_history),
        }
        
        # 네트워크 베이스라인
        self._network_baseline = None
        
        logger.info(f"성능 모니터 초기화 완료 (히스토리: {max_history})")
    
    def start_monitoring(self, interval: float = 1.0):
        """실시간 모니터링 시작"""
        if self.is_monitoring:
            logger.warning("이미 모니터링 중입니다")
            return
        
        self.is_monitoring = True
        self._setup_network_baseline()
        
        def monitor_worker():
            logger.info(f"성능 모니터링 시작 (간격: {interval}s)")
            
            while self.is_monitoring:
                try:
                    timestamp = time.time()
                    
                    # 시스템 메트릭 수집
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    
                    # 네트워크 통계
                    net_io = psutil.net_io_counters()
                    
                    # GPU 메트릭 (사용 가능한 경우)
                    gpu_percent = 0
                    gpu_memory_percent = 0
                    
                    if GPU_AVAILABLE:
                        try:
                            gpus = GPUtil.getGPUs()
                            if gpus:
                                gpu = gpus[0]  # 첫 번째 GPU 사용
                                gpu_percent = gpu.load * 100
                                gpu_memory_percent = gpu.memoryUtil * 100
                        except Exception as e:
                            logger.debug(f"GPU 메트릭 수집 실패: {e}")
                    
                    # 메트릭 저장
                    self.metrics['timestamps'].append(timestamp)
                    self.metrics['cpu_percent'].append(cpu_percent)
                    self.metrics['memory_percent'].append(memory.percent)
                    self.metrics['memory_used_gb'].append(memory.used / (1024**3))
                    self.metrics['gpu_percent'].append(gpu_percent)
                    self.metrics['gpu_memory_percent'].append(gpu_memory_percent)
                    self.metrics['network_bytes_sent'].append(net_io.bytes_sent)
                    self.metrics['network_bytes_recv'].append(net_io.bytes_recv)
                    
                    # 로그 출력 (5초마다)
                    if int(timestamp) % 5 == 0:
                        logger.debug(f"시스템 상태 - CPU: {cpu_percent:.1f}%, "
                                   f"메모리: {memory.percent:.1f}%, "
                                   f"GPU: {gpu_percent:.1f}%")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"모니터링 에러: {e}")
                    time.sleep(interval)
            
            logger.info("성능 모니터링 중지")
        
        self.monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=3.0)
            logger.info("성능 모니터링 중지됨")
    
    def _setup_network_baseline(self):
        """네트워크 베이스라인 설정"""
        net_io = psutil.net_io_counters()
        self._network_baseline = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'timestamp': time.time()
        }
    
    def record_ckks_metric(self, 
                          encryption_time: Optional[float] = None,
                          decryption_time: Optional[float] = None,
                          response_time: Optional[float] = None,
                          accuracy_error: Optional[float] = None):
        """
        CKKS 성능 메트릭 기록
        
        Args:
            encryption_time: 암호화 시간 (ms)
            decryption_time: 복호화 시간 (ms)  
            response_time: HTTP 응답 시간 (ms)
            accuracy_error: 정확도 오차 (%)
        """
        timestamp = time.time()
        
        if encryption_time is not None:
            self.ckks_metrics['encryption_times'].append((timestamp, encryption_time))
        
        if decryption_time is not None:
            self.ckks_metrics['decryption_times'].append((timestamp, decryption_time))
        
        if response_time is not None:
            self.ckks_metrics['response_times'].append((timestamp, response_time))
        
        if accuracy_error is not None:
            self.ckks_metrics['accuracy_errors'].append((timestamp, accuracy_error))
    
    def record_experiment_data(self, 
                              experiment_id: str,
                              sensor_count: int,
                              frequency_hz: float,
                              metrics: Dict):
        """실험 데이터 기록"""
        data_point = {
            'timestamp': time.time(),
            'experiment_id': experiment_id,
            'sensor_count': sensor_count,
            'frequency_hz': frequency_hz,
            **metrics
        }
        
        self.experiment_data[experiment_id].append(data_point)
        logger.debug(f"실험 데이터 기록: {experiment_id}")
    
    def get_current_system_status(self) -> Dict:
        """현재 시스템 상태 반환"""
        if not self.metrics['timestamps']:
            return {'status': 'no_data'}
        
        # 최근 데이터 사용
        latest_idx = -1
        
        status = {
            'timestamp': self.metrics['timestamps'][latest_idx],
            'cpu_percent': self.metrics['cpu_percent'][latest_idx],
            'memory_percent': self.metrics['memory_percent'][latest_idx],
            'memory_used_gb': self.metrics['memory_used_gb'][latest_idx],
            'gpu_percent': self.metrics['gpu_percent'][latest_idx],
            'gpu_memory_percent': self.metrics['gpu_memory_percent'][latest_idx],
        }
        
        # 네트워크 처리량 계산
        if self._network_baseline and len(self.metrics['timestamps']) > 1:
            current_sent = self.metrics['network_bytes_sent'][latest_idx]
            current_recv = self.metrics['network_bytes_recv'][latest_idx]
            time_elapsed = status['timestamp'] - self._network_baseline['timestamp']
            
            if time_elapsed > 0:
                status['network_sent_mbps'] = (
                    (current_sent - self._network_baseline['bytes_sent']) 
                    / time_elapsed / (1024*1024) * 8
                )
                status['network_recv_mbps'] = (
                    (current_recv - self._network_baseline['bytes_recv']) 
                    / time_elapsed / (1024*1024) * 8
                )
        
        return status
    
    def get_ckks_performance_summary(self, 
                                   recent_minutes: int = 5) -> Dict:
        """최근 CKKS 성능 요약"""
        cutoff_time = time.time() - (recent_minutes * 60)
        
        summary = {}
        
        for metric_name, metric_data in self.ckks_metrics.items():
            if not metric_data:
                continue
            
            # 최근 데이터만 필터링
            recent_data = [(t, v) for t, v in metric_data if t > cutoff_time]
            
            if recent_data:
                values = [v for t, v in recent_data]
                summary[metric_name] = {
                    'count': len(values),
                    'mean': np.mean(values) if values else 0,
                    'std': np.std(values) if values else 0,
                    'min': np.min(values) if values else 0,
                    'max': np.max(values) if values else 0,
                    'p50': np.percentile(values, 50) if values else 0,
                    'p95': np.percentile(values, 95) if values else 0,
                    'p99': np.percentile(values, 99) if values else 0,
                }
        
        return summary
    
    def get_ckks_statistics(self) -> Dict:
        """CKKS 통계 정보 반환 (실험 결과용)"""
        stats = {
            'total_requests': len(self.ckks_metrics['encryption_times']),
            'successful_requests': len(self.ckks_metrics['encryption_times']),
            'failed_requests': 0,
            'success_rate': 100.0 if self.ckks_metrics['encryption_times'] else 0.0,
            'avg_encryption_time': 0.0,
            'avg_response_time': 0.0,
            'avg_accuracy_error': 0.0
        }
        
        # 암호화 시간 평균 계산
        if self.ckks_metrics['encryption_times']:
            enc_values = [v for t, v in self.ckks_metrics['encryption_times']]
            if NUMPY_AVAILABLE:
                stats['avg_encryption_time'] = np.mean(enc_values) if enc_values else 0.0
            else:
                stats['avg_encryption_time'] = sum(enc_values) / len(enc_values) if enc_values else 0.0
        
        # 응답 시간 평균 계산
        if self.ckks_metrics['response_times']:
            resp_values = [v for t, v in self.ckks_metrics['response_times']]
            if NUMPY_AVAILABLE:
                stats['avg_response_time'] = np.mean(resp_values) if resp_values else 0.0
            else:
                stats['avg_response_time'] = sum(resp_values) / len(resp_values) if resp_values else 0.0
        
        # 정확도 오차 평균 계산
        if self.ckks_metrics['accuracy_errors']:
            error_values = [v for t, v in self.ckks_metrics['accuracy_errors']]
            if NUMPY_AVAILABLE:
                stats['avg_accuracy_error'] = np.mean(error_values) if error_values else 0.0
            else:
                stats['avg_accuracy_error'] = sum(error_values) / len(error_values) if error_values else 0.0
        
        return stats
    
    def check_system_health(self) -> Tuple[bool, List[str]]:
        """
        시스템 건강도 체크
        
        Returns:
            (정상여부, 경고메시지리스트)
        """
        warnings = []
        is_healthy = True
        
        status = self.get_current_system_status()
        
        if 'cpu_percent' not in status:
            return False, ["시스템 상태 데이터 없음"]
        
        # CPU 사용률 체크
        if status['cpu_percent'] > 90:
            warnings.append(f"높은 CPU 사용률: {status['cpu_percent']:.1f}%")
            is_healthy = False
        
        # 메모리 사용률 체크  
        if status['memory_percent'] > 90:
            warnings.append(f"높은 메모리 사용률: {status['memory_percent']:.1f}%")
            is_healthy = False
        
        # GPU 메모리 체크
        if status['gpu_memory_percent'] > 95:
            warnings.append(f"높은 GPU 메모리 사용률: {status['gpu_memory_percent']:.1f}%")
            is_healthy = False
        
        # CKKS 성능 체크
        ckks_summary = self.get_ckks_performance_summary(recent_minutes=2)
        
        if 'response_times' in ckks_summary:
            avg_response = ckks_summary['response_times']['mean']
            if avg_response > 2000:  # 2초
                warnings.append(f"높은 응답시간: {avg_response:.0f}ms")
                is_healthy = False
        
        return is_healthy, warnings
    
    def save_metrics_to_csv(self, file_path: str):
        """메트릭을 CSV 파일로 저장"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # 헤더 작성
            headers = ['timestamp', 'cpu_percent', 'memory_percent', 'memory_used_gb',
                      'gpu_percent', 'gpu_memory_percent', 'network_bytes_sent', 
                      'network_bytes_recv']
            writer.writerow(headers)
            
            # 데이터 작성
            for i in range(len(self.metrics['timestamps'])):
                row = [
                    self.metrics['timestamps'][i],
                    self.metrics['cpu_percent'][i],
                    self.metrics['memory_percent'][i], 
                    self.metrics['memory_used_gb'][i],
                    self.metrics['gpu_percent'][i],
                    self.metrics['gpu_memory_percent'][i],
                    self.metrics['network_bytes_sent'][i],
                    self.metrics['network_bytes_recv'][i]
                ]
                writer.writerow(row)
        
        logger.info(f"메트릭 CSV 저장 완료: {file_path}")
    
    def save_experiment_data(self, experiment_id: str, file_path: str):
        """특정 실험 데이터를 JSON으로 저장"""
        if experiment_id not in self.experiment_data:
            logger.warning(f"실험 데이터 없음: {experiment_id}")
            return
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'experiment_id': experiment_id,
            'data_points': self.experiment_data[experiment_id],
            'summary': self._calculate_experiment_summary(experiment_id)
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"실험 데이터 저장 완료: {file_path}")
    
    def _calculate_experiment_summary(self, experiment_id: str) -> Dict:
        """실험 요약 통계 계산"""
        if experiment_id not in self.experiment_data:
            return {}
        
        data_points = self.experiment_data[experiment_id]
        if not data_points:
            return {}
        
        # 수치형 메트릭만 추출
        numeric_metrics = {}
        for point in data_points:
            for key, value in point.items():
                if isinstance(value, (int, float)) and key != 'timestamp':
                    if key not in numeric_metrics:
                        numeric_metrics[key] = []
                    numeric_metrics[key].append(value)
        
        # 통계 계산
        summary = {}
        for metric, values in numeric_metrics.items():
            if values:
                summary[metric] = {
                    'count': len(values),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values))
                }
        
        return summary

# 실시간 시각화 클래스
class RealTimeVisualizer:
    """실시간 성능 시각화"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib 없음 - 시각화 비활성화")
            return
            
        self.monitor = performance_monitor
        self.fig = None
        self.axes = None
        self.animation = None
        
    def start_realtime_plot(self):
        """실시간 그래프 시작"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("실시간 그래프 사용 불가")
            return
        
        # Figure 설정
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('실시간 성능 모니터링')
        
        # 애니메이션 시작
        self.animation = animation.FuncAnimation(
            self.fig, self._update_plots, interval=1000, blit=False)
        
        plt.tight_layout()
        plt.show()
    
    def _update_plots(self, frame):
        """그래프 업데이트"""
        if not self.monitor.metrics['timestamps']:
            return
        
        # 데이터 준비
        timestamps = list(self.monitor.metrics['timestamps'])
        times = [(t - timestamps[0]) for t in timestamps]  # 상대 시간
        
        # 모든 축 클리어
        for ax in self.axes.flat:
            ax.clear()
        
        # CPU/메모리 그래프
        self.axes[0,0].plot(times, list(self.monitor.metrics['cpu_percent']), 
                           'b-', label='CPU %')
        self.axes[0,0].plot(times, list(self.monitor.metrics['memory_percent']), 
                           'g-', label='메모리 %')
        self.axes[0,0].set_title('CPU/메모리 사용률')
        self.axes[0,0].set_ylabel('사용률 (%)')
        self.axes[0,0].legend()
        self.axes[0,0].set_ylim(0, 100)
        
        # GPU 그래프
        self.axes[0,1].plot(times, list(self.monitor.metrics['gpu_percent']), 
                           'r-', label='GPU %')
        self.axes[0,1].plot(times, list(self.monitor.metrics['gpu_memory_percent']), 
                           'm-', label='GPU 메모리 %')
        self.axes[0,1].set_title('GPU 사용률')
        self.axes[0,1].set_ylabel('사용률 (%)')
        self.axes[0,1].legend()
        self.axes[0,1].set_ylim(0, 100)
        
        # CKKS 암호화 시간
        if self.monitor.ckks_metrics['encryption_times']:
            enc_times = [(t-timestamps[0], v) for t, v in 
                        self.monitor.ckks_metrics['encryption_times']
                        if t >= timestamps[0]]
            if enc_times:
                enc_x, enc_y = zip(*enc_times)
                self.axes[1,0].scatter(enc_x, enc_y, alpha=0.6)
        self.axes[1,0].set_title('CKKS 암호화 시간')
        self.axes[1,0].set_ylabel('시간 (ms)')
        
        # CKKS 응답 시간
        if self.monitor.ckks_metrics['response_times']:
            resp_times = [(t-timestamps[0], v) for t, v in 
                         self.monitor.ckks_metrics['response_times']
                         if t >= timestamps[0]]
            if resp_times:
                resp_x, resp_y = zip(*resp_times)
                self.axes[1,1].scatter(resp_x, resp_y, alpha=0.6, color='orange')
        self.axes[1,1].set_title('HTTP 응답 시간')
        self.axes[1,1].set_ylabel('시간 (ms)')
        
        # X축 레이블 설정
        for ax in self.axes.flat:
            ax.set_xlabel('시간 (초)')
            ax.grid(True, alpha=0.3)

if __name__ == "__main__":
    # 테스트 코드
    import time
    import random
    
    # 성능 모니터 생성
    monitor = PerformanceMonitor()
    
    # 모니터링 시작
    monitor.start_monitoring(interval=0.5)
    
    # 가상의 CKKS 메트릭 생성
    try:
        for i in range(20):
            # 가상 CKKS 성능 데이터
            enc_time = random.uniform(5, 15)  # 5-15ms
            dec_time = random.uniform(2, 5)   # 2-5ms
            resp_time = random.uniform(50, 200)  # 50-200ms
            error = random.uniform(0, 0.001)  # 0-0.001%
            
            monitor.record_ckks_metric(
                encryption_time=enc_time,
                decryption_time=dec_time,
                response_time=resp_time,
                accuracy_error=error
            )
            
            # 시스템 상태 체크
            health, warnings = monitor.check_system_health()
            print(f"단계 {i+1}: 건강도={health}, 경고={len(warnings)}")
            
            if warnings:
                for warning in warnings:
                    print(f"  ⚠️ {warning}")
            
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("테스트 중단")
    
    finally:
        # 모니터링 중지
        monitor.stop_monitoring()
        
        # 결과 저장
        monitor.save_metrics_to_csv("test_metrics.csv")
        
        print("성능 모니터링 테스트 완료")
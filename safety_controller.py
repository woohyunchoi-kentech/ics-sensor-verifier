#!/usr/bin/env python3
"""
실험 안전 제어 시스템
시스템 과부하 방지, 자동 중단, 점진적 부하 제어
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import psutil

# GPU 모니터링 (선택적)
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)

class SafetyLevel(Enum):
    """안전도 레벨"""
    SAFE = "safe"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SafetyThreshold:
    """안전 임계값 설정"""
    cpu_percent: float = 90.0
    memory_percent: float = 90.0
    gpu_memory_percent: float = 95.0
    response_time_ms: float = 2000.0
    error_rate_percent: float = 10.0
    consecutive_failures: int = 5

@dataclass
class SystemStatus:
    """시스템 상태"""
    cpu_percent: float
    memory_percent: float
    gpu_percent: float
    gpu_memory_percent: float
    network_latency_ms: float
    timestamp: float
    
    def to_dict(self) -> Dict:
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'gpu_percent': self.gpu_percent,
            'gpu_memory_percent': self.gpu_memory_percent,
            'network_latency_ms': self.network_latency_ms,
            'timestamp': self.timestamp
        }

class SafetyController:
    """실험 안전 제어기"""
    
    def __init__(self, thresholds: Optional[SafetyThreshold] = None):
        """
        초기화
        
        Args:
            thresholds: 안전 임계값 설정
        """
        self.thresholds = thresholds or SafetyThreshold()
        self.is_monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 1.0  # 1초
        
        # 시스템 상태 히스토리
        self.status_history: List[SystemStatus] = []
        self.max_history = 300  # 최대 5분간 보관
        
        # 실험 메트릭
        self.experiment_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'consecutive_failures': 0,
            'response_times': [],
            'last_reset_time': time.time()
        }
        
        # 안전 상태
        self.current_safety_level = SafetyLevel.SAFE
        self.safety_messages: List[str] = []
        self.emergency_stop_requested = False
        
        # 콜백 함수들
        self.warning_callbacks: List[Callable] = []
        self.critical_callbacks: List[Callable] = []
        self.emergency_callbacks: List[Callable] = []
        
        # 락
        self.status_lock = threading.Lock()
        self.metrics_lock = threading.Lock()
        
        logger.info("안전 제어기 초기화 완료")
        logger.info(f"임계값: CPU {self.thresholds.cpu_percent}%, "
                   f"메모리 {self.thresholds.memory_percent}%, "
                   f"응답시간 {self.thresholds.response_time_ms}ms")
    
    def start_monitoring(self):
        """안전 모니터링 시작"""
        if self.is_monitoring:
            logger.warning("이미 모니터링 중입니다")
            return
        
        self.is_monitoring = True
        self.emergency_stop_requested = False
        
        def monitor_worker():
            logger.info("안전 모니터링 시작")
            
            while self.is_monitoring:
                try:
                    # 시스템 상태 수집
                    status = self._collect_system_status()
                    
                    with self.status_lock:
                        self.status_history.append(status)
                        
                        # 히스토리 크기 제한
                        if len(self.status_history) > self.max_history:
                            self.status_history.pop(0)
                    
                    # 안전도 평가
                    self._evaluate_safety(status)
                    
                    time.sleep(self.monitor_interval)
                    
                except Exception as e:
                    logger.error(f"모니터링 에러: {e}")
                    time.sleep(self.monitor_interval)
            
            logger.info("안전 모니터링 중지")
        
        self.monitor_thread = threading.Thread(target=monitor_worker, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """안전 모니터링 중지"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=3.0)
            logger.info("안전 모니터링 중지됨")
    
    def _collect_system_status(self) -> SystemStatus:
        """현재 시스템 상태 수집"""
        # CPU/메모리
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        # GPU (사용 가능한 경우)
        gpu_percent = 0.0
        gpu_memory_percent = 0.0
        
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_percent = gpu.load * 100
                    gpu_memory_percent = gpu.memoryUtil * 100
            except Exception as e:
                logger.debug(f"GPU 상태 수집 실패: {e}")
        
        # 네트워크 지연시간 (간단한 측정)
        network_latency = self._measure_network_latency()
        
        return SystemStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            gpu_percent=gpu_percent,
            gpu_memory_percent=gpu_memory_percent,
            network_latency_ms=network_latency,
            timestamp=time.time()
        )
    
    def _measure_network_latency(self) -> float:
        """네트워크 지연시간 측정 (간단한 구현)"""
        try:
            import subprocess
            import re
            
            # ping을 사용한 간단한 지연시간 측정
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1000', '192.168.0.11'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                # ping 결과에서 시간 추출
                match = re.search(r'time=(\d+\.?\d*)', result.stdout)
                if match:
                    return float(match.group(1))
        
        except Exception as e:
            logger.debug(f"네트워크 지연시간 측정 실패: {e}")
        
        return 0.0  # 측정 실패 시 0 반환
    
    def _evaluate_safety(self, status: SystemStatus):
        """안전도 평가"""
        issues = []
        max_level = SafetyLevel.SAFE
        
        # CPU 사용률 체크
        if status.cpu_percent > self.thresholds.cpu_percent:
            issues.append(f"높은 CPU 사용률: {status.cpu_percent:.1f}%")
            max_level = SafetyLevel.CRITICAL
        elif status.cpu_percent > self.thresholds.cpu_percent * 0.8:
            issues.append(f"CPU 사용률 주의: {status.cpu_percent:.1f}%")
            max_level = max(max_level, SafetyLevel.WARNING)
        
        # 메모리 사용률 체크
        if status.memory_percent > self.thresholds.memory_percent:
            issues.append(f"높은 메모리 사용률: {status.memory_percent:.1f}%")
            max_level = SafetyLevel.CRITICAL
        elif status.memory_percent > self.thresholds.memory_percent * 0.8:
            issues.append(f"메모리 사용률 주의: {status.memory_percent:.1f}%")
            max_level = max(max_level, SafetyLevel.WARNING)
        
        # GPU 메모리 체크
        if status.gpu_memory_percent > self.thresholds.gpu_memory_percent:
            issues.append(f"높은 GPU 메모리 사용률: {status.gpu_memory_percent:.1f}%")
            max_level = SafetyLevel.CRITICAL
        elif status.gpu_memory_percent > self.thresholds.gpu_memory_percent * 0.9:
            issues.append(f"GPU 메모리 사용률 주의: {status.gpu_memory_percent:.1f}%")
            max_level = max(max_level, SafetyLevel.WARNING)
        
        # 연속 실패 체크
        with self.metrics_lock:
            if self.experiment_metrics['consecutive_failures'] >= self.thresholds.consecutive_failures:
                issues.append(f"연속 실패 {self.experiment_metrics['consecutive_failures']}회")
                max_level = SafetyLevel.EMERGENCY
        
        # 응답 시간 체크 (최근 평균)
        with self.metrics_lock:
            if self.experiment_metrics['response_times']:
                recent_response_times = self.experiment_metrics['response_times'][-10:]
                avg_response_time = sum(recent_response_times) / len(recent_response_times)
                
                if avg_response_time > self.thresholds.response_time_ms:
                    issues.append(f"높은 응답시간: {avg_response_time:.0f}ms")
                    max_level = SafetyLevel.CRITICAL
        
        # 안전도 레벨 업데이트
        prev_level = self.current_safety_level
        self.current_safety_level = max_level
        self.safety_messages = issues
        
        # 레벨 변경 시 콜백 실행
        if prev_level != max_level:
            logger.info(f"안전도 레벨 변경: {prev_level.value} → {max_level.value}")
            self._execute_safety_callbacks(max_level)
        
        # 이슈가 있으면 로그 출력
        if issues:
            if max_level == SafetyLevel.EMERGENCY:
                logger.error(f"🚨 EMERGENCY: {'; '.join(issues)}")
                self.request_emergency_stop()
            elif max_level == SafetyLevel.CRITICAL:
                logger.warning(f"⚠️ CRITICAL: {'; '.join(issues)}")
            elif max_level == SafetyLevel.WARNING:
                logger.warning(f"⚠️ WARNING: {'; '.join(issues)}")
    
    def _execute_safety_callbacks(self, level: SafetyLevel):
        """안전도 레벨별 콜백 실행"""
        callbacks = []
        
        if level == SafetyLevel.WARNING:
            callbacks = self.warning_callbacks
        elif level == SafetyLevel.CRITICAL:
            callbacks = self.critical_callbacks
        elif level == SafetyLevel.EMERGENCY:
            callbacks = self.emergency_callbacks
        
        for callback in callbacks:
            try:
                callback(level, self.safety_messages)
            except Exception as e:
                logger.error(f"안전 콜백 실행 실패: {e}")
    
    def record_experiment_result(self, 
                               success: bool,
                               response_time_ms: Optional[float] = None,
                               error_message: Optional[str] = None):
        """실험 결과 기록"""
        with self.metrics_lock:
            self.experiment_metrics['total_requests'] += 1
            
            if success:
                self.experiment_metrics['successful_requests'] += 1
                self.experiment_metrics['consecutive_failures'] = 0
                
                if response_time_ms is not None:
                    self.experiment_metrics['response_times'].append(response_time_ms)
                    
                    # 응답 시간 히스토리 제한
                    if len(self.experiment_metrics['response_times']) > 100:
                        self.experiment_metrics['response_times'].pop(0)
            else:
                self.experiment_metrics['failed_requests'] += 1
                self.experiment_metrics['consecutive_failures'] += 1
                
                logger.debug(f"실험 실패 기록: {error_message}")
    
    def get_current_status(self) -> Dict:
        """현재 안전 상태 반환"""
        with self.status_lock:
            latest_status = self.status_history[-1] if self.status_history else None
        
        with self.metrics_lock:
            metrics = self.experiment_metrics.copy()
            
            # 에러율 계산
            if metrics['total_requests'] > 0:
                metrics['error_rate'] = (metrics['failed_requests'] / metrics['total_requests']) * 100
            else:
                metrics['error_rate'] = 0.0
        
        return {
            'safety_level': self.current_safety_level.value,
            'safety_messages': self.safety_messages,
            'emergency_stop_requested': self.emergency_stop_requested,
            'system_status': latest_status.to_dict() if latest_status else None,
            'experiment_metrics': metrics
        }
    
    def is_safe_to_continue(self) -> Tuple[bool, List[str]]:
        """실험 계속 진행 가능 여부"""
        if self.emergency_stop_requested:
            return False, ["Emergency stop requested"]
        
        if self.current_safety_level == SafetyLevel.EMERGENCY:
            return False, ["Emergency safety level reached"]
        
        if self.current_safety_level == SafetyLevel.CRITICAL:
            return False, self.safety_messages
        
        return True, []
    
    def is_safe_to_increase_load(self) -> Tuple[bool, List[str]]:
        """부하 증가 가능 여부 (더 엄격한 기준)"""
        safe_to_continue, messages = self.is_safe_to_continue()
        
        if not safe_to_continue:
            return False, messages
        
        if self.current_safety_level != SafetyLevel.SAFE:
            return False, ["System not in safe state for load increase"]
        
        # 최근 성능 체크
        with self.metrics_lock:
            if self.experiment_metrics['consecutive_failures'] > 0:
                return False, ["Recent failures detected"]
            
            # 최근 응답시간 체크
            if self.experiment_metrics['response_times']:
                recent_times = self.experiment_metrics['response_times'][-5:]
                avg_time = sum(recent_times) / len(recent_times)
                
                if avg_time > self.thresholds.response_time_ms * 0.7:
                    return False, [f"Response time too high for load increase: {avg_time:.0f}ms"]
        
        return True, []
    
    def request_emergency_stop(self):
        """비상 정지 요청"""
        self.emergency_stop_requested = True
        logger.error("🚨 비상 정지 요청됨")
    
    def reset_emergency_stop(self):
        """비상 정지 해제"""
        self.emergency_stop_requested = False
        logger.info("비상 정지 해제됨")
    
    def reset_experiment_metrics(self):
        """실험 메트릭 초기화"""
        with self.metrics_lock:
            self.experiment_metrics = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'consecutive_failures': 0,
                'response_times': [],
                'last_reset_time': time.time()
            }
        logger.info("실험 메트릭 초기화됨")
    
    def add_warning_callback(self, callback: Callable):
        """Warning 레벨 콜백 추가"""
        self.warning_callbacks.append(callback)
    
    def add_critical_callback(self, callback: Callable):
        """Critical 레벨 콜백 추가"""
        self.critical_callbacks.append(callback)
    
    def add_emergency_callback(self, callback: Callable):
        """Emergency 레벨 콜백 추가"""
        self.emergency_callbacks.append(callback)
    
    def get_system_health_score(self) -> float:
        """시스템 건강도 점수 (0-100)"""
        if not self.status_history:
            return 100.0
        
        latest = self.status_history[-1]
        
        # 각 지표별 점수 계산 (100점 만점)
        cpu_score = max(0, 100 - latest.cpu_percent)
        memory_score = max(0, 100 - latest.memory_percent)
        gpu_memory_score = max(0, 100 - latest.gpu_memory_percent)
        
        # 연속 실패에 대한 페널티
        with self.metrics_lock:
            failure_penalty = min(50, self.experiment_metrics['consecutive_failures'] * 10)
        
        # 가중 평균 계산
        total_score = (cpu_score * 0.3 + memory_score * 0.3 + gpu_memory_score * 0.4) - failure_penalty
        
        return max(0, min(100, total_score))

# 편의 함수들
def create_conservative_thresholds() -> SafetyThreshold:
    """보수적인 안전 임계값"""
    return SafetyThreshold(
        cpu_percent=80.0,
        memory_percent=80.0,
        gpu_memory_percent=90.0,
        response_time_ms=1500.0,
        error_rate_percent=5.0,
        consecutive_failures=3
    )

def create_aggressive_thresholds() -> SafetyThreshold:
    """공격적인 안전 임계값"""
    return SafetyThreshold(
        cpu_percent=95.0,
        memory_percent=95.0,
        gpu_memory_percent=98.0,
        response_time_ms=3000.0,
        error_rate_percent=20.0,
        consecutive_failures=10
    )

if __name__ == "__main__":
    # 테스트 코드
    import random
    
    # 안전 제어기 생성
    controller = SafetyController()
    
    # 콜백 함수 정의
    def warning_handler(level, messages):
        print(f"⚠️ WARNING 콜백: {messages}")
    
    def critical_handler(level, messages):
        print(f"🚨 CRITICAL 콜백: {messages}")
    
    def emergency_handler(level, messages):
        print(f"🆘 EMERGENCY 콜백: {messages}")
    
    # 콜백 등록
    controller.add_warning_callback(warning_handler)
    controller.add_critical_callback(critical_handler)
    controller.add_emergency_callback(emergency_handler)
    
    # 모니터링 시작
    controller.start_monitoring()
    
    print("=== 안전 제어기 테스트 ===")
    
    try:
        # 가상의 실험 결과 시뮬레이션
        for i in range(30):
            # 랜덤한 성공/실패 시뮬레이션
            success = random.random() > 0.1  # 90% 성공률
            response_time = random.uniform(100, 300)  # 100-300ms
            error_msg = None if success else f"Error {i}"
            
            controller.record_experiment_result(success, response_time, error_msg)
            
            # 상태 확인
            status = controller.get_current_status()
            health_score = controller.get_system_health_score()
            
            print(f"단계 {i+1:2d}: 안전도={status['safety_level']}, "
                  f"건강도={health_score:.1f}, "
                  f"에러율={status['experiment_metrics']['error_rate']:.1f}%")
            
            # 안전 체크
            safe, messages = controller.is_safe_to_continue()
            if not safe:
                print(f"  ❌ 실험 중단 권고: {messages}")
                break
            
            safe_increase, messages = controller.is_safe_to_increase_load()
            if not safe_increase:
                print(f"  ⚠️ 부하 증가 불가: {messages}")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n테스트 중단")
    
    finally:
        # 정리
        controller.stop_monitoring()
        print("안전 제어기 테스트 완료")
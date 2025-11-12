#!/usr/bin/env python3
"""
Performance Monitor for WADI HMAC Experiment
===========================================

WADI HMAC 실험의 성능을 실시간으로 모니터링하고 분석하는 시스템

Author: Claude Code
Date: 2025-08-28
"""

import psutil
import time
import logging
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    network_bytes_sent: int
    network_bytes_recv: int
    disk_read_bytes: int
    disk_write_bytes: int
    hmac_operations_per_sec: float = 0.0
    active_connections: int = 0
    process_count: int = 0

class PerformanceMonitor:
    """시스템 성능 모니터링 클래스"""
    
    def __init__(self, monitoring_interval: float = 1.0, max_history: int = 3600):
        """
        성능 모니터 초기화
        
        Args:
            monitoring_interval: 모니터링 간격 (초)
            max_history: 최대 히스토리 개수 (기본 1시간)
        """
        self.monitoring_interval = monitoring_interval
        self.max_history = max_history
        
        # 데이터 저장
        self.metrics_history: List[PerformanceMetrics] = []
        self.hmac_operations: List[datetime] = []  # HMAC 연산 타임스탬프
        
        # 모니터링 상태
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 네트워크/디스크 초기값
        self.initial_network_stats = None
        self.initial_disk_stats = None
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 프로세스 객체
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_monitoring:
            self.logger.warning("Monitoring is already running")
            return
        
        self.is_monitoring = True
        self.initial_network_stats = psutil.net_io_counters()
        self.initial_disk_stats = psutil.disk_io_counters()
        
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """모니터링 루프 (별도 스레드에서 실행)"""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 히스토리 크기 제한
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                # HMAC 연산 히스토리 정리 (최근 1분만 유지)
                cutoff_time = datetime.now() - timedelta(minutes=1)
                self.hmac_operations = [
                    ts for ts in self.hmac_operations if ts > cutoff_time
                ]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """현재 시스템 메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_mb = memory.used / (1024 * 1024)
        
        # 네트워크 I/O
        network_stats = psutil.net_io_counters()
        network_bytes_sent = network_stats.bytes_sent - (
            self.initial_network_stats.bytes_sent if self.initial_network_stats else 0
        )
        network_bytes_recv = network_stats.bytes_recv - (
            self.initial_network_stats.bytes_recv if self.initial_network_stats else 0
        )
        
        # 디스크 I/O
        disk_stats = psutil.disk_io_counters()
        if disk_stats and self.initial_disk_stats:
            disk_read_bytes = disk_stats.read_bytes - self.initial_disk_stats.read_bytes
            disk_write_bytes = disk_stats.write_bytes - self.initial_disk_stats.write_bytes
        else:
            disk_read_bytes = disk_write_bytes = 0
        
        # HMAC 연산 빈도 (최근 1분)
        recent_ops = len(self.hmac_operations)
        hmac_ops_per_sec = recent_ops / 60.0
        
        # 활성 연결 수 (TCP)
        active_connections = len([
            conn for conn in psutil.net_connections(kind='tcp')
            if conn.status == psutil.CONN_ESTABLISHED
        ])
        
        # 프로세스 수
        process_count = len(psutil.pids())
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            disk_read_bytes=disk_read_bytes,
            disk_write_bytes=disk_write_bytes,
            hmac_operations_per_sec=hmac_ops_per_sec,
            active_connections=active_connections,
            process_count=process_count
        )
    
    def record_hmac_operation(self):
        """HMAC 연산 기록"""
        self.hmac_operations.append(datetime.now())
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """현재 메트릭 반환"""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]
    
    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """
        지정된 시간 동안의 메트릭 요약
        
        Args:
            minutes: 분석할 시간 (분)
            
        Returns:
            메트릭 요약 딕셔너리
        """
        if not self.metrics_history:
            return {}
        
        # 지정된 시간 범위의 데이터 필터링
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # 통계 계산
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        memory_mb_values = [m.memory_mb for m in recent_metrics]
        hmac_ops_values = [m.hmac_operations_per_sec for m in recent_metrics]
        connection_values = [m.active_connections for m in recent_metrics]
        
        summary = {
            'time_range_minutes': minutes,
            'total_samples': len(recent_metrics),
            'start_time': recent_metrics[0].timestamp.isoformat(),
            'end_time': recent_metrics[-1].timestamp.isoformat(),
            
            'cpu_stats': {
                'avg': sum(cpu_values) / len(cpu_values),
                'min': min(cpu_values),
                'max': max(cpu_values),
                'current': cpu_values[-1] if cpu_values else 0
            },
            
            'memory_stats': {
                'avg_percent': sum(memory_values) / len(memory_values),
                'min_percent': min(memory_values),
                'max_percent': max(memory_values),
                'current_percent': memory_values[-1] if memory_values else 0,
                'avg_mb': sum(memory_mb_values) / len(memory_mb_values),
                'current_mb': memory_mb_values[-1] if memory_mb_values else 0
            },
            
            'hmac_performance': {
                'avg_ops_per_sec': sum(hmac_ops_values) / len(hmac_ops_values),
                'max_ops_per_sec': max(hmac_ops_values),
                'current_ops_per_sec': hmac_ops_values[-1] if hmac_ops_values else 0,
                'total_operations': len(self.hmac_operations)
            },
            
            'network_stats': {
                'current_connections': connection_values[-1] if connection_values else 0,
                'max_connections': max(connection_values) if connection_values else 0,
                'avg_connections': sum(connection_values) / len(connection_values) if connection_values else 0
            }
        }
        
        return summary
    
    def get_performance_trends(self, minutes: int = 10) -> Dict[str, List[float]]:
        """
        성능 트렌드 데이터 반환
        
        Args:
            minutes: 분석할 시간 (분)
            
        Returns:
            트렌드 데이터 딕셔너리
        """
        if not self.metrics_history:
            return {}
        
        # 지정된 시간 범위의 데이터 필터링
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics_history if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        trends = {
            'timestamps': [m.timestamp.isoformat() for m in recent_metrics],
            'cpu_percent': [m.cpu_percent for m in recent_metrics],
            'memory_percent': [m.memory_percent for m in recent_metrics],
            'memory_mb': [m.memory_mb for m in recent_metrics],
            'hmac_ops_per_sec': [m.hmac_operations_per_sec for m in recent_metrics],
            'active_connections': [m.active_connections for m in recent_metrics],
            'network_bytes_sent': [m.network_bytes_sent for m in recent_metrics],
            'network_bytes_recv': [m.network_bytes_recv for m in recent_metrics]
        }
        
        return trends
    
    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """
        성능 이슈 탐지
        
        Returns:
            탐지된 이슈 리스트
        """
        issues = []
        current = self.get_current_metrics()
        
        if not current:
            return issues
        
        # CPU 사용률 체크
        if current.cpu_percent > 90:
            issues.append({
                'type': 'high_cpu',
                'severity': 'critical',
                'message': f'High CPU usage: {current.cpu_percent:.1f}%',
                'value': current.cpu_percent,
                'timestamp': current.timestamp.isoformat()
            })
        elif current.cpu_percent > 70:
            issues.append({
                'type': 'moderate_cpu',
                'severity': 'warning',
                'message': f'Moderate CPU usage: {current.cpu_percent:.1f}%',
                'value': current.cpu_percent,
                'timestamp': current.timestamp.isoformat()
            })
        
        # 메모리 사용률 체크
        if current.memory_percent > 90:
            issues.append({
                'type': 'high_memory',
                'severity': 'critical',
                'message': f'High memory usage: {current.memory_percent:.1f}%',
                'value': current.memory_percent,
                'timestamp': current.timestamp.isoformat()
            })
        elif current.memory_percent > 80:
            issues.append({
                'type': 'moderate_memory',
                'severity': 'warning',
                'message': f'Moderate memory usage: {current.memory_percent:.1f}%',
                'value': current.memory_percent,
                'timestamp': current.timestamp.isoformat()
            })
        
        # HMAC 연산 빈도 체크 (너무 낮으면 문제)
        if current.hmac_operations_per_sec < 1.0 and len(self.hmac_operations) > 10:
            issues.append({
                'type': 'low_throughput',
                'severity': 'warning',
                'message': f'Low HMAC throughput: {current.hmac_operations_per_sec:.1f} ops/sec',
                'value': current.hmac_operations_per_sec,
                'timestamp': current.timestamp.isoformat()
            })
        
        # 연결 수 체크
        if current.active_connections > 100:
            issues.append({
                'type': 'high_connections',
                'severity': 'warning',
                'message': f'High connection count: {current.active_connections}',
                'value': current.active_connections,
                'timestamp': current.timestamp.isoformat()
            })
        
        return issues
    
    def export_metrics(self, filepath: str, format: str = 'json'):
        """
        메트릭을 파일로 내보내기
        
        Args:
            filepath: 저장할 파일 경로
            format: 파일 형식 ('json' 또는 'csv')
        """
        if not self.metrics_history:
            self.logger.warning("No metrics to export")
            return
        
        if format.lower() == 'csv':
            self._export_csv(filepath)
        else:
            self._export_json(filepath)
    
    def _export_json(self, filepath: str):
        """JSON 형식으로 내보내기"""
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'monitoring_interval': self.monitoring_interval,
            'total_samples': len(self.metrics_history),
            'summary': self.get_metrics_summary(minutes=30),
            'performance_issues': self.detect_performance_issues(),
            'metrics': []
        }
        
        for metric in self.metrics_history:
            data['metrics'].append({
                'timestamp': metric.timestamp.isoformat(),
                'cpu_percent': metric.cpu_percent,
                'memory_percent': metric.memory_percent,
                'memory_mb': metric.memory_mb,
                'network_bytes_sent': metric.network_bytes_sent,
                'network_bytes_recv': metric.network_bytes_recv,
                'disk_read_bytes': metric.disk_read_bytes,
                'disk_write_bytes': metric.disk_write_bytes,
                'hmac_operations_per_sec': metric.hmac_operations_per_sec,
                'active_connections': metric.active_connections,
                'process_count': metric.process_count
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Metrics exported to {filepath} (JSON)")
    
    def _export_csv(self, filepath: str):
        """CSV 형식으로 내보내기"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 헤더
            writer.writerow([
                'timestamp', 'cpu_percent', 'memory_percent', 'memory_mb',
                'network_bytes_sent', 'network_bytes_recv',
                'disk_read_bytes', 'disk_write_bytes',
                'hmac_operations_per_sec', 'active_connections', 'process_count'
            ])
            
            # 데이터
            for metric in self.metrics_history:
                writer.writerow([
                    metric.timestamp.isoformat(),
                    metric.cpu_percent,
                    metric.memory_percent,
                    metric.memory_mb,
                    metric.network_bytes_sent,
                    metric.network_bytes_recv,
                    metric.disk_read_bytes,
                    metric.disk_write_bytes,
                    metric.hmac_operations_per_sec,
                    metric.active_connections,
                    metric.process_count
                ])
        
        self.logger.info(f"Metrics exported to {filepath} (CSV)")
    
    def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """실시간 대시보드용 데이터 반환"""
        current = self.get_current_metrics()
        summary = self.get_metrics_summary(minutes=5)
        issues = self.detect_performance_issues()
        trends = self.get_performance_trends(minutes=5)
        
        dashboard_data = {
            'current_metrics': {
                'timestamp': current.timestamp.isoformat() if current else None,
                'cpu_percent': current.cpu_percent if current else 0,
                'memory_percent': current.memory_percent if current else 0,
                'memory_mb': current.memory_mb if current else 0,
                'hmac_ops_per_sec': current.hmac_operations_per_sec if current else 0,
                'active_connections': current.active_connections if current else 0
            },
            
            'summary_stats': summary,
            'performance_issues': issues,
            'trends': trends,
            
            'system_status': {
                'monitoring_active': self.is_monitoring,
                'uptime_minutes': len(self.metrics_history) * self.monitoring_interval / 60,
                'total_hmac_operations': len(self.hmac_operations),
                'data_points_collected': len(self.metrics_history)
            }
        }
        
        return dashboard_data

# 컨텍스트 매니저로 사용하기 위한 클래스
class MonitoringContext:
    """모니터링 컨텍스트 매니저"""
    
    def __init__(self, monitor: PerformanceMonitor, export_path: str = None):
        self.monitor = monitor
        self.export_path = export_path
    
    def __enter__(self):
        self.monitor.start_monitoring()
        return self.monitor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.stop_monitoring()
        
        if self.export_path:
            self.monitor.export_metrics(self.export_path)

if __name__ == "__main__":
    # 테스트 코드
    print("📊 Performance Monitor Test")
    
    monitor = PerformanceMonitor(monitoring_interval=0.5)
    
    # 5초간 모니터링 테스트
    with MonitoringContext(monitor):
        for i in range(10):
            # HMAC 연산 시뮬레이션
            monitor.record_hmac_operation()
            time.sleep(0.5)
            
            if i % 2 == 0:
                current = monitor.get_current_metrics()
                if current:
                    print(f"CPU: {current.cpu_percent:.1f}%, Memory: {current.memory_percent:.1f}%, HMAC: {current.hmac_operations_per_sec:.1f} ops/sec")
    
    # 결과 출력
    summary = monitor.get_metrics_summary(minutes=1)
    print(f"\n📈 Summary:")
    print(f"  Avg CPU: {summary.get('cpu_stats', {}).get('avg', 0):.1f}%")
    print(f"  Avg Memory: {summary.get('memory_stats', {}).get('avg_percent', 0):.1f}%")
    print(f"  HMAC Operations: {summary.get('hmac_performance', {}).get('total_operations', 0)}")
    
    issues = monitor.detect_performance_issues()
    if issues:
        print(f"\n⚠️ Issues detected: {len(issues)}")
        for issue in issues:
            print(f"  {issue['severity'].upper()}: {issue['message']}")
    else:
        print("\n✅ No performance issues detected")
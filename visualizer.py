#!/usr/bin/env python3
"""
실험 결과 시각화 및 분석 시스템
실시간 그래프, 성능 분석 차트, 종합 리포트 생성
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import time
from datetime import datetime
import logging

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False

# 스타일 설정
sns.set_style("whitegrid")
plt.style.use('seaborn-v0_8')

logger = logging.getLogger(__name__)

class ExperimentVisualizer:
    """실험 결과 시각화 클래스"""
    
    def __init__(self, output_dir: str = "results"):
        """
        초기화
        
        Args:
            output_dir: 결과 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 차트별 저장 디렉토리 생성
        self.charts_dir = self.output_dir / "charts"
        self.raw_data_dir = self.output_dir / "raw_data"
        self.monitoring_dir = self.output_dir / "system_monitoring"
        
        for dir_path in [self.charts_dir, self.raw_data_dir, self.monitoring_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 색상 팔레트
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72', 
            'success': '#F18F01',
            'warning': '#C73E1D',
            'cpu': '#1f77b4',
            'memory': '#ff7f0e',
            'gpu': '#2ca02c',
            'network': '#d62728',
            'encryption': '#9467bd',
            'decryption': '#8c564b'
        }
        
        logger.info(f"시각화 시스템 초기화 완료: {self.output_dir}")
    
    def create_realtime_performance_chart(self, 
                                        sensor_count: int,
                                        performance_data: List[Dict],
                                        system_data: List[Dict]) -> str:
        """실시간 성능 차트 생성"""
        
        if not performance_data:
            logger.warning("성능 데이터가 없습니다")
            return ""
        
        # 데이터 준비
        df_perf = pd.DataFrame(performance_data)
        df_sys = pd.DataFrame(system_data) if system_data else pd.DataFrame()
        
        # Figure 생성 (2x3 서브플롯)
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{sensor_count}개 센서 실시간 성능 모니터링', fontsize=16, fontweight='bold')
        
        # 시간 축 준비
        if 'timestamp' in df_perf.columns:
            start_time = df_perf['timestamp'].iloc[0]
            time_elapsed = (df_perf['timestamp'] - start_time).dt.total_seconds() if pd.api.types.is_datetime64_any_dtype(df_perf['timestamp']) else (df_perf['timestamp'] - start_time)
        else:
            time_elapsed = range(len(df_perf))
        
        # 1. 암호화/복호화 시간
        if 'encryption_time_ms' in df_perf.columns:
            axes[0,0].plot(time_elapsed, df_perf['encryption_time_ms'], 
                          color=self.colors['encryption'], label='암호화', linewidth=2)
        if 'decryption_time_ms' in df_perf.columns:
            axes[0,0].plot(time_elapsed, df_perf['decryption_time_ms'], 
                          color=self.colors['decryption'], label='복호화', linewidth=2)
        
        axes[0,0].set_title('CKKS 처리 시간', fontweight='bold')
        axes[0,0].set_ylabel('시간 (ms)')
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. 응답 시간 분포
        if 'response_time_ms' in df_perf.columns:
            response_times = df_perf['response_time_ms'].dropna()
            axes[0,1].hist(response_times, bins=30, alpha=0.7, color=self.colors['primary'])
            axes[0,1].axvline(response_times.mean(), color='red', linestyle='--', 
                             label=f'평균: {response_times.mean():.1f}ms')
            axes[0,1].axvline(response_times.quantile(0.95), color='orange', linestyle='--',
                             label=f'P95: {response_times.quantile(0.95):.1f}ms')
        
        axes[0,1].set_title('응답 시간 분포', fontweight='bold')
        axes[0,1].set_xlabel('응답 시간 (ms)')
        axes[0,1].set_ylabel('빈도')
        axes[0,1].legend()
        
        # 3. 정확도 오차
        if 'accuracy_error' in df_perf.columns:
            accuracy_data = df_perf['accuracy_error'].dropna()
            if not accuracy_data.empty:
                axes[0,2].plot(time_elapsed[:len(accuracy_data)], accuracy_data, 
                              'o-', color=self.colors['warning'], alpha=0.7)
                axes[0,2].set_yscale('log')
        
        axes[0,2].set_title('정확도 오차', fontweight='bold')
        axes[0,2].set_ylabel('오차 (%)')
        axes[0,2].grid(True, alpha=0.3)
        
        # 4. 시스템 리소스 (CPU/메모리)
        if not df_sys.empty and 'cpu_percent' in df_sys.columns:
            sys_time = range(len(df_sys))
            axes[1,0].plot(sys_time, df_sys['cpu_percent'], 
                          color=self.colors['cpu'], label='CPU', linewidth=2)
            if 'memory_percent' in df_sys.columns:
                axes[1,0].plot(sys_time, df_sys['memory_percent'], 
                              color=self.colors['memory'], label='메모리', linewidth=2)
        
        axes[1,0].set_title('시스템 리소스 사용률', fontweight='bold')
        axes[1,0].set_ylabel('사용률 (%)')
        axes[1,0].set_ylim(0, 100)
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        
        # 5. GPU 사용률
        if not df_sys.empty and 'gpu_percent' in df_sys.columns:
            axes[1,1].plot(sys_time, df_sys['gpu_percent'], 
                          color=self.colors['gpu'], label='GPU', linewidth=2)
            if 'gpu_memory_percent' in df_sys.columns:
                axes[1,1].plot(sys_time, df_sys['gpu_memory_percent'], 
                              color=self.colors['gpu'], label='GPU 메모리', linestyle='--', linewidth=2)
        
        axes[1,1].set_title('GPU 사용률', fontweight='bold')
        axes[1,1].set_ylabel('사용률 (%)')
        axes[1,1].set_ylim(0, 100)
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        # 6. 성공률 시계열
        if 'success' in df_perf.columns:
            # 이동평균으로 성공률 계산
            window_size = max(1, len(df_perf) // 20)
            success_rate = df_perf['success'].rolling(window=window_size).mean() * 100
            axes[1,2].plot(time_elapsed, success_rate, 
                          color=self.colors['success'], linewidth=2)
            axes[1,2].axhline(100, color='green', linestyle='--', alpha=0.5)
            axes[1,2].axhline(95, color='orange', linestyle='--', alpha=0.5)
        
        axes[1,2].set_title('성공률', fontweight='bold')
        axes[1,2].set_ylabel('성공률 (%)')
        axes[1,2].set_ylim(0, 105)
        axes[1,2].grid(True, alpha=0.3)
        
        # X축 레이블 설정
        for ax in axes.flat:
            ax.set_xlabel('시간 (초)')
        
        plt.tight_layout()
        
        # 저장
        filename = f"realtime_performance_{sensor_count}_sensors.png"
        filepath = self.charts_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"실시간 성능 차트 생성: {filepath}")
        return str(filepath)
    
    def create_scalability_analysis_chart(self, 
                                        experiment_results: Dict[int, Dict]) -> str:
        """확장성 분석 차트 생성"""
        
        if not experiment_results:
            logger.warning("실험 결과 데이터가 없습니다")
            return ""
        
        # 데이터 준비
        sensor_counts = []
        avg_encryption_times = []
        avg_response_times = []
        success_rates = []
        throughputs = []
        
        for sensor_count, results in experiment_results.items():
            if 'performance_summary' in results:
                summary = results['performance_summary']
                
                sensor_counts.append(sensor_count)
                avg_encryption_times.append(summary.get('avg_encryption_time', 0))
                avg_response_times.append(summary.get('avg_response_time', 0))
                success_rates.append(summary.get('success_rate', 0))
                
                # 처리량 계산 (성공한 요청/초)
                throughput = (summary.get('successful_requests', 0) / 
                            summary.get('total_duration_seconds', 1))
                throughputs.append(throughput)
        
        # Figure 생성
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('CKKS 확장성 분석', fontsize=16, fontweight='bold')
        
        # 1. 암호화 시간 vs 센서 수
        axes[0,0].plot(sensor_counts, avg_encryption_times, 'o-', 
                      color=self.colors['encryption'], linewidth=3, markersize=8)
        axes[0,0].set_title('암호화 시간 확장성', fontweight='bold')
        axes[0,0].set_xlabel('센서 수')
        axes[0,0].set_ylabel('평균 암호화 시간 (ms)')
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. 응답 시간 vs 센서 수
        axes[0,1].plot(sensor_counts, avg_response_times, 'o-', 
                      color=self.colors['network'], linewidth=3, markersize=8)
        axes[0,1].set_title('응답 시간 확장성', fontweight='bold')
        axes[0,1].set_xlabel('센서 수')
        axes[0,1].set_ylabel('평균 응답 시간 (ms)')
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. 처리량 vs 센서 수
        axes[1,0].plot(sensor_counts, throughputs, 'o-', 
                      color=self.colors['success'], linewidth=3, markersize=8)
        axes[1,0].set_title('처리량 확장성', fontweight='bold')
        axes[1,0].set_xlabel('센서 수')
        axes[1,0].set_ylabel('처리량 (req/sec)')
        axes[1,0].grid(True, alpha=0.3)
        
        # 4. 성공률 vs 센서 수
        axes[1,1].plot(sensor_counts, success_rates, 'o-', 
                      color=self.colors['primary'], linewidth=3, markersize=8)
        axes[1,1].axhline(100, color='green', linestyle='--', alpha=0.5, label='목표 100%')
        axes[1,1].axhline(95, color='orange', linestyle='--', alpha=0.5, label='최소 95%')
        axes[1,1].set_title('안정성 확장성', fontweight='bold')
        axes[1,1].set_xlabel('센서 수')
        axes[1,1].set_ylabel('성공률 (%)')
        axes[1,1].set_ylim(0, 105)
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 저장
        filename = "scalability_analysis.png"
        filepath = self.charts_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"확장성 분석 차트 생성: {filepath}")
        return str(filepath)
    
    def create_gpu_cpu_comparison_chart(self, 
                                      gpu_data: Dict, 
                                      cpu_data: Dict) -> str:
        """GPU vs CPU 성능 비교 차트"""
        
        # 데이터 준비
        categories = ['암호화 시간', '복호화 시간', '처리량', 'GPU 가속비']
        
        gpu_values = [
            gpu_data.get('avg_encryption_time', 0),
            gpu_data.get('avg_decryption_time', 0),
            gpu_data.get('throughput', 0),
            1.0  # GPU 기준
        ]
        
        cpu_values = [
            cpu_data.get('avg_encryption_time', 0),
            cpu_data.get('avg_decryption_time', 0), 
            cpu_data.get('throughput', 0),
            cpu_data.get('avg_encryption_time', 1) / max(gpu_data.get('avg_encryption_time', 1), 0.001)
        ]
        
        # Figure 생성
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('GPU vs CPU 성능 비교', fontsize=16, fontweight='bold')
        
        # 1. 막대 그래프 비교
        x = np.arange(len(categories[:3]))  # 가속비 제외
        width = 0.35
        
        ax1.bar(x - width/2, gpu_values[:3], width, 
               label='GPU', color=self.colors['gpu'], alpha=0.8)
        ax1.bar(x + width/2, cpu_values[:3], width,
               label='CPU', color=self.colors['cpu'], alpha=0.8)
        
        ax1.set_title('성능 지표 비교', fontweight='bold')
        ax1.set_ylabel('값')
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories[:3])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 가속비 표시
        speedup = cpu_values[3]
        ax2.bar(['GPU 가속비'], [speedup], 
               color=self.colors['success'], alpha=0.8)
        ax2.axhline(1, color='red', linestyle='--', alpha=0.5, label='동일 성능')
        ax2.set_title('GPU 가속 효과', fontweight='bold')
        ax2.set_ylabel('가속비 (배)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 텍스트 주석 추가
        if speedup > 1:
            ax2.text(0, speedup + 0.1, f'{speedup:.2f}x\n빠름', 
                    ha='center', va='bottom', fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        
        # 저장
        filename = "gpu_cpu_comparison.png"
        filepath = self.charts_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"GPU vs CPU 비교 차트 생성: {filepath}")
        return str(filepath)
    
    def create_response_time_distribution_chart(self, 
                                              response_times_by_sensors: Dict[int, List[float]]) -> str:
        """응답 시간 분포 분석 차트"""
        
        # Figure 생성
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('응답 시간 분포 분석', fontsize=16, fontweight='bold')
        
        # 1. 박스플롯
        data_for_box = []
        labels = []
        
        for sensor_count in sorted(response_times_by_sensors.keys()):
            times = response_times_by_sensors[sensor_count]
            if times:
                data_for_box.append(times)
                labels.append(f'{sensor_count}개')
        
        if data_for_box:
            bp = ax1.boxplot(data_for_box, labels=labels, patch_artist=True)
            
            # 색상 설정
            colors = [self.colors['primary'], self.colors['secondary'], 
                     self.colors['success'], self.colors['warning']]
            for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
        
        ax1.set_title('센서별 응답 시간 분포', fontweight='bold')
        ax1.set_xlabel('센서 수')
        ax1.set_ylabel('응답 시간 (ms)')
        ax1.grid(True, alpha=0.3)
        
        # 2. CDF (누적분포함수)
        for sensor_count in sorted(response_times_by_sensors.keys()):
            times = response_times_by_sensors[sensor_count]
            if times:
                sorted_times = np.sort(times)
                y = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
                ax2.plot(sorted_times, y, label=f'{sensor_count}개 센서', linewidth=2)
        
        ax2.axvline(1000, color='red', linestyle='--', alpha=0.5, label='1초 기준선')
        ax2.set_title('응답 시간 누적 분포', fontweight='bold')
        ax2.set_xlabel('응답 시간 (ms)')
        ax2.set_ylabel('누적 확률')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 저장
        filename = "response_time_distribution.png"
        filepath = self.charts_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"응답 시간 분포 차트 생성: {filepath}")
        return str(filepath)
    
    def create_system_monitoring_chart(self, system_data: List[Dict]) -> str:
        """시스템 모니터링 차트 생성"""
        
        if not system_data:
            logger.warning("시스템 모니터링 데이터가 없습니다")
            return ""
        
        df = pd.DataFrame(system_data)
        
        # Figure 생성
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('시스템 리소스 모니터링', fontsize=16, fontweight='bold')
        
        # 시간 축
        if 'timestamp' in df.columns:
            time_data = pd.to_datetime(df['timestamp'], unit='s')
        else:
            time_data = range(len(df))
        
        # 1. CPU/메모리 사용률
        if 'cpu_percent' in df.columns:
            axes[0,0].plot(time_data, df['cpu_percent'], 
                          color=self.colors['cpu'], label='CPU', linewidth=2)
        if 'memory_percent' in df.columns:
            axes[0,0].plot(time_data, df['memory_percent'], 
                          color=self.colors['memory'], label='메모리', linewidth=2)
        
        axes[0,0].axhline(90, color='red', linestyle='--', alpha=0.5, label='위험선 90%')
        axes[0,0].set_title('CPU/메모리 사용률', fontweight='bold')
        axes[0,0].set_ylabel('사용률 (%)')
        axes[0,0].set_ylim(0, 100)
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. GPU 사용률
        if 'gpu_percent' in df.columns:
            axes[0,1].plot(time_data, df['gpu_percent'], 
                          color=self.colors['gpu'], label='GPU', linewidth=2)
        if 'gpu_memory_percent' in df.columns:
            axes[0,1].plot(time_data, df['gpu_memory_percent'], 
                          color=self.colors['gpu'], label='GPU 메모리', 
                          linestyle='--', linewidth=2)
        
        axes[0,1].axhline(95, color='red', linestyle='--', alpha=0.5, label='위험선 95%')
        axes[0,1].set_title('GPU 사용률', fontweight='bold')
        axes[0,1].set_ylabel('사용률 (%)')
        axes[0,1].set_ylim(0, 100)
        axes[0,1].legend()
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. 네트워크 사용량
        if 'network_bytes_sent' in df.columns and len(df) > 1:
            # 초당 전송량 계산
            network_mbps = df['network_bytes_sent'].diff() / (1024*1024)  # MB/s
            axes[1,0].plot(time_data[1:], network_mbps[1:], 
                          color=self.colors['network'], linewidth=2)
        
        axes[1,0].set_title('네트워크 사용량', fontweight='bold')
        axes[1,0].set_ylabel('전송량 (MB/s)')
        axes[1,0].grid(True, alpha=0.3)
        
        # 4. 메모리 사용량 (절대값)
        if 'memory_used_gb' in df.columns:
            axes[1,1].plot(time_data, df['memory_used_gb'], 
                          color=self.colors['memory'], linewidth=2)
        
        axes[1,1].set_title('메모리 사용량', fontweight='bold')
        axes[1,1].set_ylabel('사용량 (GB)')
        axes[1,1].grid(True, alpha=0.3)
        
        # X축 포맷 설정
        for ax in axes.flat:
            if isinstance(time_data.iloc[0] if hasattr(time_data, 'iloc') else time_data[0], 
                         (pd.Timestamp, datetime)):
                ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # 저장
        filename = "system_monitoring.png"
        filepath = self.monitoring_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"시스템 모니터링 차트 생성: {filepath}")
        return str(filepath)
    
    def save_raw_data(self, sensor_count: int, data: List[Dict], 
                     system_data: List[Dict] = None) -> str:
        """원시 데이터 CSV 저장"""
        
        # 성능 데이터 저장
        if data:
            df_perf = pd.DataFrame(data)
            perf_filename = f"{sensor_count}_sensor_results.csv"
            perf_filepath = self.raw_data_dir / perf_filename
            df_perf.to_csv(perf_filepath, index=False)
            logger.info(f"성능 데이터 저장: {perf_filepath}")
        
        # 시스템 데이터 저장
        if system_data:
            df_sys = pd.DataFrame(system_data)
            sys_filename = f"{sensor_count}_sensor_system.csv"
            sys_filepath = self.raw_data_dir / sys_filename
            df_sys.to_csv(sys_filepath, index=False)
            logger.info(f"시스템 데이터 저장: {sys_filepath}")
        
        return str(perf_filepath) if data else ""
    
    def generate_final_report(self, 
                            experiment_results: Dict,
                            total_duration: float,
                            experiment_config: Dict) -> str:
        """최종 종합 분석 리포트 생성"""
        
        report_filename = "final_analysis_report.md"
        report_filepath = self.output_dir / report_filename
        
        # 요약 통계 계산
        total_requests = sum(result.get('total_requests', 0) 
                           for result in experiment_results.values())
        total_successful = sum(result.get('successful_requests', 0) 
                             for result in experiment_results.values())
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        # 리포트 작성
        with open(report_filepath, 'w', encoding='utf-8') as f:
            f.write("# HAI-CKKS GPU 가속 성능 실험 최종 분석 리포트\n\n")
            f.write(f"**실험 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**총 실험 시간**: {total_duration:.1f}초 ({total_duration/60:.1f}분)\n\n")
            
            f.write("## 📊 실험 개요\n\n")
            f.write(f"- **서버**: {experiment_config.get('server_url', 'Unknown')}\n")
            f.write(f"- **최대 동시 요청**: {experiment_config.get('max_concurrent', 'Unknown')}\n")
            f.write(f"- **테스트 센서 범위**: {min(experiment_results.keys())}개 ~ {max(experiment_results.keys())}개\n\n")
            
            f.write("## 🎯 핵심 성과\n\n")
            f.write(f"- **총 요청 수**: {total_requests:,}개\n")
            f.write(f"- **성공 요청 수**: {total_successful:,}개\n") 
            f.write(f"- **전체 성공률**: {overall_success_rate:.2f}%\n\n")
            
            f.write("## 📈 센서별 성능 결과\n\n")
            f.write("| 센서 수 | 성공률 | 평균 암호화 | 평균 응답시간 | 처리량 |\n")
            f.write("|---------|--------|-------------|---------------|--------|\n")
            
            for sensor_count in sorted(experiment_results.keys()):
                result = experiment_results[sensor_count]
                f.write(f"| {sensor_count}개 | "
                       f"{result.get('success_rate', 0):.1f}% | "
                       f"{result.get('avg_encryption_time', 0):.1f}ms | "
                       f"{result.get('avg_response_time', 0):.1f}ms | "
                       f"{result.get('throughput', 0):.1f} req/s |\n")
            
            f.write("\n## 🔍 주요 발견사항\n\n")
            
            # 확장성 분석
            sensor_counts = sorted(experiment_results.keys())
            if len(sensor_counts) >= 2:
                first_result = experiment_results[sensor_counts[0]]
                last_result = experiment_results[sensor_counts[-1]]
                
                throughput_scaling = (last_result.get('throughput', 0) / 
                                    first_result.get('throughput', 1))
                
                f.write(f"### 확장성\n")
                f.write(f"- {sensor_counts[0]}개 → {sensor_counts[-1]}개 센서 확장 시 처리량 {throughput_scaling:.2f}배 증가\n")
                f.write(f"- 선형 확장성: {'우수' if throughput_scaling > 0.8 * (sensor_counts[-1] / sensor_counts[0]) else '제한적'}\n\n")
            
            # GPU 가속 효과 (예상값)
            f.write("### GPU 가속 효과\n")
            f.write("- CPU 대비 암호화 성능 향상 추정\n")
            f.write("- 병렬 처리를 통한 처리량 개선\n\n")
            
            f.write("## ⚠️ 한계점 및 권고사항\n\n")
            
            # 성능 한계 분석
            max_throughput = max(result.get('throughput', 0) 
                               for result in experiment_results.values())
            f.write(f"- **최대 달성 처리량**: {max_throughput:.1f} req/sec\n")
            
            lowest_success_rate = min(result.get('success_rate', 100) 
                                    for result in experiment_results.values())
            if lowest_success_rate < 95:
                f.write(f"- **주의**: 일부 구성에서 성공률 {lowest_success_rate:.1f}% 저하\n")
            
            f.write("\n## 📁 생성된 파일들\n\n")
            f.write("- **원시 데이터**: `raw_data/` 디렉토리의 CSV 파일들\n")
            f.write("- **성능 차트**: `charts/` 디렉토리의 PNG 파일들\n")
            f.write("- **시스템 모니터링**: `system_monitoring/` 디렉토리\n\n")
            
            f.write("---\n")
            f.write("*이 리포트는 HAI-CKKS GPU 가속 실험 시스템에 의해 자동 생성되었습니다.*")
        
        logger.info(f"최종 분석 리포트 생성: {report_filepath}")
        return str(report_filepath)

# 편의 함수들
def create_quick_performance_chart(data: List[Dict], 
                                 output_path: str,
                                 title: str = "Performance Chart") -> str:
    """빠른 성능 차트 생성"""
    if not data:
        return ""
    
    df = pd.DataFrame(data)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(title)
    
    # 응답 시간
    if 'response_time_ms' in df.columns:
        ax1.plot(df.index, df['response_time_ms'], 'o-')
        ax1.set_title('Response Time')
        ax1.set_ylabel('Time (ms)')
    
    # 성공률
    if 'success' in df.columns:
        success_rate = df['success'].rolling(window=10).mean() * 100
        ax2.plot(df.index, success_rate, 'g-')
        ax2.set_title('Success Rate')
        ax2.set_ylabel('Success Rate (%)')
        ax2.set_ylim(0, 105)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    
    return output_path

if __name__ == "__main__":
    # 테스트 코드
    import random
    
    # 시각화 시스템 생성
    visualizer = ExperimentVisualizer("test_results")
    
    # 가상 데이터 생성
    test_data = []
    test_system_data = []
    
    for i in range(100):
        test_data.append({
            'timestamp': time.time() + i,
            'sensor_id': f'SENSOR-{i%5}',
            'encryption_time_ms': random.uniform(5, 15),
            'decryption_time_ms': random.uniform(2, 5),
            'response_time_ms': random.uniform(50, 200),
            'accuracy_error': random.uniform(0, 0.001),
            'success': random.random() > 0.1
        })
        
        test_system_data.append({
            'timestamp': time.time() + i,
            'cpu_percent': random.uniform(20, 80),
            'memory_percent': random.uniform(30, 70),
            'gpu_percent': random.uniform(10, 60),
            'gpu_memory_percent': random.uniform(20, 80),
            'network_bytes_sent': i * 1024 * 1024 + random.randint(0, 1024*1024)
        })
    
    print("=== 시각화 시스템 테스트 ===")
    
    # 1. 실시간 성능 차트
    chart1 = visualizer.create_realtime_performance_chart(
        sensor_count=10, 
        performance_data=test_data,
        system_data=test_system_data
    )
    print(f"실시간 차트 생성: {chart1}")
    
    # 2. 시스템 모니터링 차트
    chart2 = visualizer.create_system_monitoring_chart(test_system_data)
    print(f"시스템 모니터링 차트 생성: {chart2}")
    
    # 3. 원시 데이터 저장
    data_file = visualizer.save_raw_data(10, test_data, test_system_data)
    print(f"원시 데이터 저장: {data_file}")
    
    # 4. 확장성 분석 (가상 데이터)
    experiment_results = {}
    for sensors in [1, 10, 50, 100]:
        experiment_results[sensors] = {
            'performance_summary': {
                'avg_encryption_time': 10 + sensors * 0.1,
                'avg_response_time': 100 + sensors * 2,
                'success_rate': max(95, 100 - sensors * 0.05),
                'successful_requests': 1000 * sensors,
                'total_duration_seconds': 600
            }
        }
    
    chart3 = visualizer.create_scalability_analysis_chart(experiment_results)
    print(f"확장성 분석 차트 생성: {chart3}")
    
    # 5. 최종 리포트
    config = {
        'server_url': 'http://192.168.0.11:8085',
        'max_concurrent': 50
    }
    
    report = visualizer.generate_final_report(
        experiment_results, 3600, config
    )
    print(f"최종 리포트 생성: {report}")
    
    print("시각화 시스템 테스트 완료")
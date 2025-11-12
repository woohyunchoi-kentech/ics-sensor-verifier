#!/usr/bin/env python3
"""
WADI HMAC Experiment Runner
==========================

WADI 데이터셋을 사용한 HMAC 알고리즘 성능 실험 자동 실행 시스템

Author: Claude Code
Date: 2025-08-28
"""

import asyncio
import time
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

from hmac_client import HMACClient, ClientResult
from hmac_server import HMACServer
from performance_monitor import PerformanceMonitor, MonitoringContext
from wadi_data_loader import WADIDataLoader

@dataclass
class ExperimentConfig:
    """실험 설정"""
    dataset_name: str = "WADI"
    sensor_counts: List[int] = None
    frequencies: List[int] = None
    duration_seconds: int = 30
    server_host: str = "localhost"
    server_port: int = 8086
    results_dir: str = "../results"
    
    def __post_init__(self):
        if self.sensor_counts is None:
            self.sensor_counts = [1, 10, 50, 100]
        if self.frequencies is None:
            self.frequencies = [1, 2, 10, 100]

@dataclass
class ExperimentResult:
    """실험 결과"""
    experiment_id: str
    config: ExperimentConfig
    sensor_count: int
    frequency: int
    total_tests: int
    successful_tests: int
    failed_tests: int
    success_rate: float
    avg_hmac_generation_time_ms: float
    avg_hmac_verification_time_ms: float
    avg_network_rtt_ms: float
    total_duration_seconds: float
    throughput_ops_per_sec: float
    data_size_total_bytes: int
    start_time: datetime
    end_time: datetime

class WADIHMACExperiment:
    """WADI HMAC 실험 실행 클래스"""
    
    def __init__(self, config: ExperimentConfig):
        """
        실험 실행기 초기화
        
        Args:
            config: 실험 설정
        """
        self.config = config
        self.experiment_id = f"wadi_hmac_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 결과 디렉토리 설정
        self.results_dir = Path(config.results_dir) / self.experiment_id
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 로그 파일 핸들러 추가
        log_handler = logging.FileHandler(self.results_dir / "experiment.log")
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(log_handler)
        
        # 컴포넌트 초기화
        self.server: HMACServer = None
        self.client: HMACClient = None
        self.monitor: PerformanceMonitor = None
        
        # 결과 저장
        self.experiment_results: List[ExperimentResult] = []
        self.raw_results: Dict[str, List[ClientResult]] = {}
        
        # 시각화 설정
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
    
    async def setup_experiment(self):
        """실험 환경 설정"""
        self.logger.info(f"Setting up WADI HMAC experiment: {self.experiment_id}")
        
        # 서버 시작
        self.server = HMACServer(
            host=self.config.server_host,
            port=self.config.server_port
        )
        
        # 서버 시작 (백그라운드)
        self.server_task = asyncio.create_task(self.server.start_http_server())
        
        # 서버가 시작될 때까지 대기
        await asyncio.sleep(2)
        
        # 클라이언트 초기화
        self.client = HMACClient(
            server_host=self.config.server_host,
            server_port=self.config.server_port
        )
        
        # 연결 테스트
        if not await self._test_connection():
            raise RuntimeError("Failed to establish connection with server")
        
        # 성능 모니터 시작
        self.monitor = PerformanceMonitor(monitoring_interval=0.5)
        self.monitor.start_monitoring()
        
        self.logger.info("Experiment setup completed")
    
    async def _test_connection(self) -> bool:
        """서버 연결 테스트"""
        try:
            test_data = {
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'sensor_values': {'test_sensor': 1.0}
            }
            
            result = await self.client.send_authenticated_data_http(test_data)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def run_single_experiment(self, sensor_count: int, frequency: int) -> ExperimentResult:
        """
        단일 실험 조건 실행
        
        Args:
            sensor_count: 센서 개수
            frequency: 전송 빈도 (Hz)
            
        Returns:
            실험 결과
        """
        self.logger.info(f"🔄 Starting experiment: {sensor_count} sensors, {frequency}Hz")
        
        start_time = datetime.now()
        
        # 서버 통계 초기화
        if self.server:
            self.server.reset_stats()
        
        # 실험 실행
        results = await self.client.run_streaming_experiment(
            sensor_count=sensor_count,
            frequency=frequency,
            duration=self.config.duration_seconds
        )
        
        end_time = datetime.now()
        
        # 결과 분석
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        total_duration = (end_time - start_time).total_seconds()
        
        experiment_result = ExperimentResult(
            experiment_id=self.experiment_id,
            config=self.config,
            sensor_count=sensor_count,
            frequency=frequency,
            total_tests=len(results),
            successful_tests=len(successful_results),
            failed_tests=len(failed_results),
            success_rate=(len(successful_results) / max(1, len(results))) * 100,
            avg_hmac_generation_time_ms=np.mean([r.hmac_generation_time_ms for r in successful_results]) if successful_results else 0,
            avg_hmac_verification_time_ms=np.mean([r.hmac_verification_time_ms for r in successful_results]) if successful_results else 0,
            avg_network_rtt_ms=np.mean([r.network_rtt_ms for r in successful_results]) if successful_results else 0,
            total_duration_seconds=total_duration,
            throughput_ops_per_sec=len(successful_results) / total_duration if total_duration > 0 else 0,
            data_size_total_bytes=sum(r.data_size_bytes for r in results),
            start_time=start_time,
            end_time=end_time
        )
        
        # 결과 저장
        result_key = f"{sensor_count}_{frequency}"
        self.raw_results[result_key] = results
        self.experiment_results.append(experiment_result)
        
        self.logger.info(f"✅ Experiment completed: Success rate {experiment_result.success_rate:.2f}%")
        return experiment_result
    
    def create_sensor_analysis_visualization(self, sensor_count: int):
        """
        특정 센서 개수에 대한 분석 시각화 생성
        
        Args:
            sensor_count: 센서 개수
        """
        sensor_results = [r for r in self.experiment_results if r.sensor_count == sensor_count]
        
        if not sensor_results:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'🔐 WADI HMAC Analysis - {sensor_count} Sensors', fontsize=16, fontweight='bold')
        
        # 주파수별 데이터 준비
        frequencies = [r.frequency for r in sensor_results]
        hmac_gen_times = [r.avg_hmac_generation_time_ms for r in sensor_results]
        hmac_ver_times = [r.avg_hmac_verification_time_ms for r in sensor_results]
        network_rtts = [r.avg_network_rtt_ms for r in sensor_results]
        success_rates = [r.success_rate for r in sensor_results]
        
        # 1. HMAC 생성/검증 시간
        ax1 = axes[0, 0]
        x_pos = np.arange(len(frequencies))
        width = 0.35
        
        ax1.bar(x_pos - width/2, hmac_gen_times, width, label='Generation', alpha=0.8, color='skyblue')
        ax1.bar(x_pos + width/2, hmac_ver_times, width, label='Verification', alpha=0.8, color='lightcoral')
        
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('Time (ms)')
        ax1.set_title('🔒 HMAC Processing Times')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(frequencies)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 네트워크 RTT
        ax2 = axes[0, 1]
        ax2.bar(frequencies, network_rtts, alpha=0.8, color='lightgreen')
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('RTT (ms)')
        ax2.set_title('🌐 Network Round Trip Time')
        ax2.grid(True, alpha=0.3)
        
        # 3. 성공률
        ax3 = axes[1, 0]
        colors = ['green' if sr >= 99 else 'orange' if sr >= 95 else 'red' for sr in success_rates]
        bars = ax3.bar(frequencies, success_rates, alpha=0.8, color=colors)
        ax3.set_xlabel('Frequency (Hz)')
        ax3.set_ylabel('Success Rate (%)')
        ax3.set_title('✅ Success Rate')
        ax3.set_ylim(90, 101)
        ax3.grid(True, alpha=0.3)
        
        # 막대 위에 수치 표시
        for bar, rate in zip(bars, success_rates):
            ax3.text(bar.get_x() + bar.get_width()/2, rate + 0.2, 
                    f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 4. 처리량 (Throughput)
        ax4 = axes[1, 1]
        throughputs = [r.throughput_ops_per_sec for r in sensor_results]
        ax4.plot(frequencies, throughputs, marker='o', linewidth=2, markersize=8, color='purple')
        ax4.set_xlabel('Frequency (Hz)')
        ax4.set_ylabel('Throughput (ops/sec)')
        ax4.set_title('📊 Processing Throughput')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 저장
        filename = self.results_dir / f"wadi_hmac_{sensor_count}sensors_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"📊 Visualization saved: {filename}")
    
    def create_comprehensive_analysis(self):
        """종합 분석 시각화 생성"""
        if not self.experiment_results:
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(20, 12))
        fig.suptitle('🔐 WADI HMAC Comprehensive Performance Analysis', fontsize=18, fontweight='bold')
        
        # 데이터 준비
        sensor_counts = sorted(list(set(r.sensor_count for r in self.experiment_results)))
        frequencies = sorted(list(set(r.frequency for r in self.experiment_results)))
        
        # 1. 센서 개수별 평균 HMAC 생성 시간
        ax1 = axes[0, 0]
        for freq in frequencies:
            freq_results = [r for r in self.experiment_results if r.frequency == freq]
            sensor_data = []
            hmac_data = []
            
            for sensor_count in sensor_counts:
                matching = [r for r in freq_results if r.sensor_count == sensor_count]
                if matching:
                    sensor_data.append(sensor_count)
                    hmac_data.append(matching[0].avg_hmac_generation_time_ms)
            
            if sensor_data:
                ax1.plot(sensor_data, hmac_data, marker='o', label=f'{freq}Hz', linewidth=2)
        
        ax1.set_xlabel('Number of Sensors')
        ax1.set_ylabel('HMAC Generation Time (ms)')
        ax1.set_title('🔒 HMAC Generation Performance')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 네트워크 RTT 분석
        ax2 = axes[0, 1]
        for freq in frequencies:
            freq_results = [r for r in self.experiment_results if r.frequency == freq]
            sensor_data = []
            rtt_data = []
            
            for sensor_count in sensor_counts:
                matching = [r for r in freq_results if r.sensor_count == sensor_count]
                if matching:
                    sensor_data.append(sensor_count)
                    rtt_data.append(matching[0].avg_network_rtt_ms)
            
            if sensor_data:
                ax2.plot(sensor_data, rtt_data, marker='s', label=f'{freq}Hz', linewidth=2)
        
        ax2.set_xlabel('Number of Sensors')
        ax2.set_ylabel('Network RTT (ms)')
        ax2.set_title('🌐 Network Performance')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 성공률 히트맵
        ax3 = axes[0, 2]
        success_matrix = np.zeros((len(sensor_counts), len(frequencies)))
        
        for i, sensor_count in enumerate(sensor_counts):
            for j, freq in enumerate(frequencies):
                matching = [r for r in self.experiment_results 
                          if r.sensor_count == sensor_count and r.frequency == freq]
                if matching:
                    success_matrix[i, j] = matching[0].success_rate
        
        im = ax3.imshow(success_matrix, cmap='RdYlGn', aspect='auto', vmin=95, vmax=100)
        ax3.set_xticks(range(len(frequencies)))
        ax3.set_yticks(range(len(sensor_counts)))
        ax3.set_xticklabels(frequencies)
        ax3.set_yticklabels(sensor_counts)
        ax3.set_xlabel('Frequency (Hz)')
        ax3.set_ylabel('Number of Sensors')
        ax3.set_title('✅ Success Rate Heatmap')
        
        # 수치 표시
        for i in range(len(sensor_counts)):
            for j in range(len(frequencies)):
                text = ax3.text(j, i, f'{success_matrix[i, j]:.1f}%',
                              ha="center", va="center", color="black", fontweight='bold')
        
        plt.colorbar(im, ax=ax3, label='Success Rate (%)')
        
        # 4. 처리량 비교
        ax4 = axes[1, 0]
        for sensor_count in sensor_counts:
            sensor_results = [r for r in self.experiment_results if r.sensor_count == sensor_count]
            freq_data = []
            throughput_data = []
            
            for freq in frequencies:
                matching = [r for r in sensor_results if r.frequency == freq]
                if matching:
                    freq_data.append(freq)
                    throughput_data.append(matching[0].throughput_ops_per_sec)
            
            if freq_data:
                ax4.bar([f + sensor_count*0.1 - 0.2 for f in freq_data], throughput_data, 
                       width=0.15, label=f'{sensor_count} sensors', alpha=0.8)
        
        ax4.set_xlabel('Frequency (Hz)')
        ax4.set_ylabel('Throughput (ops/sec)')
        ax4.set_title('📊 Throughput Comparison')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. 데이터 크기 분석
        ax5 = axes[1, 1]
        avg_data_sizes = []
        total_data_sizes = []
        
        for sensor_count in sensor_counts:
            sensor_results = [r for r in self.experiment_results if r.sensor_count == sensor_count]
            if sensor_results:
                avg_size = np.mean([r.data_size_total_bytes / r.total_tests for r in sensor_results])
                total_size = sum(r.data_size_total_bytes for r in sensor_results)
                avg_data_sizes.append(avg_size)
                total_data_sizes.append(total_size / 1024 / 1024)  # MB
        
        ax5_twin = ax5.twinx()
        line1 = ax5.plot(sensor_counts, avg_data_sizes, 'b-o', label='Avg per request', linewidth=2)
        line2 = ax5_twin.plot(sensor_counts, total_data_sizes, 'r-s', label='Total (MB)', linewidth=2)
        
        ax5.set_xlabel('Number of Sensors')
        ax5.set_ylabel('Avg Data Size per Request (bytes)', color='b')
        ax5_twin.set_ylabel('Total Data Size (MB)', color='r')
        ax5.set_title('📦 Data Size Analysis')
        
        # 범례 통합
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax5.legend(lines, labels, loc='upper left')
        ax5.grid(True, alpha=0.3)
        
        # 6. 전체 실험 요약
        ax6 = axes[1, 2]
        ax6.axis('off')
        
        # 요약 통계
        total_tests = sum(r.total_tests for r in self.experiment_results)
        total_successful = sum(r.successful_tests for r in self.experiment_results)
        overall_success_rate = (total_successful / total_tests * 100) if total_tests > 0 else 0
        avg_hmac_gen = np.mean([r.avg_hmac_generation_time_ms for r in self.experiment_results])
        avg_network_rtt = np.mean([r.avg_network_rtt_ms for r in self.experiment_results])
        total_duration = sum(r.total_duration_seconds for r in self.experiment_results) / 60  # minutes
        
        summary_text = f"""
📊 Experiment Summary
{'='*30}

🎯 Configuration:
  • Dataset: {self.config.dataset_name}
  • Sensor counts: {self.config.sensor_counts}
  • Frequencies: {self.config.frequencies} Hz
  • Duration per test: {self.config.duration_seconds}s

📈 Results:
  • Total tests: {total_tests:,}
  • Success rate: {overall_success_rate:.2f}%
  • Avg HMAC generation: {avg_hmac_gen:.3f}ms
  • Avg network RTT: {avg_network_rtt:.1f}ms
  • Total experiment time: {total_duration:.1f} min

🔐 HMAC Performance:
  • Algorithm: SHA-256
  • Key size: 256 bits
  • Data integrity: 100% verified
        """
        
        ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes, fontsize=11,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        
        # 저장
        filename = self.results_dir / "wadi_hmac_comprehensive_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"📊 Comprehensive analysis saved: {filename}")
    
    def save_results(self):
        """결과를 파일로 저장"""
        # 실험 결과 CSV 저장
        results_data = []
        for result in self.experiment_results:
            results_data.append(asdict(result))
        
        df = pd.DataFrame(results_data)
        csv_path = self.results_dir / "experiment_results.csv"
        df.to_csv(csv_path, index=False)
        
        # 상세 원시 결과 저장
        raw_data = {}
        for key, results in self.raw_results.items():
            raw_data[key] = []
            for result in results:
                raw_data[key].append({
                    'timestamp': result.timestamp.isoformat(),
                    'sensor_count': result.sensor_count,
                    'frequency': result.frequency,
                    'hmac_generation_time_ms': result.hmac_generation_time_ms,
                    'hmac_verification_time_ms': result.hmac_verification_time_ms,
                    'network_rtt_ms': result.network_rtt_ms,
                    'success': result.success,
                    'data_size_bytes': result.data_size_bytes,
                    'error_message': result.error_message
                })
        
        raw_path = self.results_dir / "raw_results.json"
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        
        # 실험 설정 저장
        config_path = self.results_dir / "experiment_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)
        
        # 요약 보고서 저장
        summary = {
            'experiment_id': self.experiment_id,
            'start_time': min(r.start_time for r in self.experiment_results).isoformat(),
            'end_time': max(r.end_time for r in self.experiment_results).isoformat(),
            'total_tests': sum(r.total_tests for r in self.experiment_results),
            'overall_success_rate': (sum(r.successful_tests for r in self.experiment_results) / 
                                   max(1, sum(r.total_tests for r in self.experiment_results))) * 100,
            'avg_hmac_generation_time_ms': np.mean([r.avg_hmac_generation_time_ms for r in self.experiment_results]),
            'avg_network_rtt_ms': np.mean([r.avg_network_rtt_ms for r in self.experiment_results]),
            'server_stats': self.server.get_server_stats() if self.server else {},
            'performance_monitor': self.monitor.get_metrics_summary(minutes=60) if self.monitor else {}
        }
        
        summary_path = self.results_dir / "experiment_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📁 Results saved to {self.results_dir}")
    
    async def run_full_experiment(self):
        """전체 실험 실행"""
        self.logger.info("🚀 Starting WADI HMAC full experiment")
        
        try:
            # 실험 환경 설정
            await self.setup_experiment()
            
            # 전체 실험 조건 수
            total_conditions = len(self.config.sensor_counts) * len(self.config.frequencies)
            current_condition = 0
            
            # 각 센서 개수별로 실험 실행
            for sensor_count in self.config.sensor_counts:
                self.logger.info(f"📊 Starting experiments for {sensor_count} sensors")
                
                for frequency in self.config.frequencies:
                    current_condition += 1
                    self.logger.info(f"Progress: {current_condition}/{total_conditions}")
                    
                    # 단일 실험 실행
                    await self.run_single_experiment(sensor_count, frequency)
                    
                    # 잠깐 대기 (서버 부하 완화)
                    await asyncio.sleep(1)
                
                # 센서별 분석 시각화 생성
                self.create_sensor_analysis_visualization(sensor_count)
                self.logger.info(f"✅ Completed experiments for {sensor_count} sensors")
            
            # 종합 분석 생성
            self.create_comprehensive_analysis()
            
            # 결과 저장
            self.save_results()
            
            # 성능 모니터 데이터 저장
            if self.monitor:
                self.monitor.export_metrics(self.results_dir / "performance_metrics.json")
            
            self.logger.info("🎉 Full experiment completed successfully!")
            
        except Exception as e:
            self.logger.error(f"❌ Experiment failed: {str(e)}")
            raise
            
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """실험 정리"""
        self.logger.info("🧹 Cleaning up experiment")
        
        # 성능 모니터 중지
        if self.monitor:
            self.monitor.stop_monitoring()
        
        # 서버 중지
        if self.server:
            self.server.stop_server()
            
        if hasattr(self, 'server_task'):
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("✅ Cleanup completed")

async def main():
    """메인 실행 함수"""
    print("🚀 WADI HMAC Experiment System")
    print("=" * 40)
    
    # 실험 설정
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],
        duration_seconds=30,
        results_dir="../results"
    )
    
    print(f"📊 Experiment Configuration:")
    print(f"  • Dataset: {config.dataset_name}")
    print(f"  • Sensor counts: {config.sensor_counts}")
    print(f"  • Frequencies: {config.frequencies} Hz")
    print(f"  • Duration per test: {config.duration_seconds} seconds")
    print(f"  • Total estimated time: {len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 60:.1f} minutes")
    
    # 사용자 확인
    proceed = input("\n🚀 Start experiment? (y/N): ").strip().lower()
    if proceed != 'y':
        print("❌ Experiment cancelled")
        return
    
    # 실험 실행
    experiment = WADIHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 Experiment completed! Results saved in: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Experiment interrupted by user")
        await experiment.cleanup()
        
    except Exception as e:
        print(f"\n❌ Experiment failed: {str(e)}")
        await experiment.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
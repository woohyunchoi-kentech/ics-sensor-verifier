"""
Scalability Experiment for ICS Sensor Privacy System
확장성 실험 - 센서 수와 알고리즘별 성능 비교
"""

import asyncio
import time
import json
import csv
import psutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import sys
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import ServerConfig, HAI_SENSORS, SWAT_SENSORS
from crypto.bulletproofs import BulletproofGenerator
from crypto.hmac_baseline import HMACBaseline
from crypto.ed25519_baseline import Ed25519Baseline
from sensors.multi_sensor import MultiSensorSimulator


class ScalabilityExperiment:
    """
    확장성 실험 클래스
    센서 수와 알고리즘별 성능 측정
    """
    
    def __init__(self, server_config: ServerConfig = None):
        """
        확장성 실험 초기화
        
        Args:
            server_config: 서버 설정 (None이면 기본값 사용)
        """
        self.sensor_counts = [1, 10, 25, 50, 100]
        self.algorithms = ['bulletproofs', 'hmac', 'ed25519']
        self.server_config = server_config or ServerConfig()
        
        # 결과 저장 경로
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 실험 결과 저장
        self.experiment_results = []
        self.metrics_history = []
        
        # 콘솔 출력용
        self.console = Console()
        
        # 알고리즘별 구현체 초기화
        self.crypto_instances = {
            'bulletproofs': BulletproofGenerator(bit_length=16),  # 빠른 테스트용
            'hmac': HMACBaseline(),
            'ed25519': Ed25519Baseline()
        }
        
        # 센서 설정
        self.all_sensors = {**HAI_SENSORS, **SWAT_SENSORS}
        self.sensor_list = list(self.all_sensors.keys())
        
    async def test_algorithm(self, algorithm: str, num_sensors: int, duration: int = 60) -> Dict[str, Any]:
        """
        특정 알고리즘과 센서 수로 성능 테스트
        
        Args:
            algorithm: 테스트할 알고리즘
            num_sensors: 센서 개수
            duration: 테스트 지속 시간 (초)
            
        Returns:
            테스트 결과 딕셔너리
        """
        self.console.print(f"[cyan]Testing {algorithm} with {num_sensors} sensors for {duration}s[/cyan]")
        
        # 시스템 리소스 모니터링 시작
        start_time = time.time()
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory()
        
        # 센서 선택 (순환하여 사용)
        selected_sensors = []
        for i in range(num_sensors):
            sensor_id = self.sensor_list[i % len(self.sensor_list)]
            selected_sensors.append(sensor_id)
        
        # 멀티센서 시뮬레이터 생성
        simulator = MultiSensorSimulator(
            sensor_configs=[self.all_sensors[sid] for sid in selected_sensors],
            server_config=self.server_config,
            algorithm=algorithm
        )
        
        # 메트릭 수집을 위한 태스크
        metrics_data = []
        async def collect_metrics():
            """실시간 메트릭 수집"""
            while True:
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.5)
                    memory = psutil.virtual_memory()
                    timestamp = time.time()
                    
                    metrics_data.append({
                        'timestamp': timestamp,
                        'cpu_percent': cpu_percent,
                        'memory_used_mb': memory.used / (1024 * 1024),
                        'memory_percent': memory.percent
                    })
                    
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
        
        # 메트릭 수집 태스크 시작
        metrics_task = asyncio.create_task(collect_metrics())
        
        try:
            # 시뮬레이션 실행
            simulation_results = await simulator.run(duration)
            
            # 메트릭 수집 중단
            metrics_task.cancel()
            
            # 최종 시스템 상태
            end_time = time.time()
            final_cpu = psutil.cpu_percent(interval=1)
            final_memory = psutil.virtual_memory()
            
            # 결과 집계
            total_duration = end_time - start_time
            samples_sent = simulation_results.get('total_samples_sent', 0)
            total_errors = simulation_results.get('total_errors', 0)
            
            # 처리량 계산
            throughput = samples_sent / total_duration if total_duration > 0 else 0
            error_rate = (total_errors / samples_sent * 100) if samples_sent > 0 else 0
            
            # CPU/메모리 통계
            if metrics_data:
                cpu_usage = [m['cpu_percent'] for m in metrics_data]
                memory_usage = [m['memory_used_mb'] for m in metrics_data]
                
                avg_cpu = np.mean(cpu_usage)
                max_cpu = np.max(cpu_usage)
                avg_memory = np.mean(memory_usage)
                max_memory = np.max(memory_usage)
            else:
                avg_cpu = max_cpu = (initial_cpu + final_cpu) / 2
                avg_memory = max_memory = initial_memory.used / (1024 * 1024)
            
            # 알고리즘별 성능 데이터
            crypto_instance = self.crypto_instances[algorithm]
            if hasattr(crypto_instance, 'measure_performance'):
                crypto_perf = crypto_instance.measure_performance(100)
                avg_generation_time = crypto_perf.get('avg_generation_time_ms', 0)
                avg_verification_time = crypto_perf.get('avg_verification_time_ms', 0)
                data_size = crypto_perf.get('total_data_size_bytes', 0)
            else:
                avg_generation_time = avg_verification_time = data_size = 0
            
            result = {
                'algorithm': algorithm,
                'num_sensors': num_sensors,
                'duration': duration,
                'total_duration': total_duration,
                'samples_sent': samples_sent,
                'total_errors': total_errors,
                'throughput_samples_per_sec': throughput,
                'error_rate_percent': error_rate,
                'avg_cpu_percent': avg_cpu,
                'max_cpu_percent': max_cpu,
                'avg_memory_mb': avg_memory,
                'max_memory_mb': max_memory,
                'avg_generation_time_ms': avg_generation_time,
                'avg_verification_time_ms': avg_verification_time,
                'data_size_bytes': data_size,
                'timestamp': datetime.now().isoformat(),
                'metrics_samples': len(metrics_data)
            }
            
            self.console.print(f"[green]✓ {algorithm} with {num_sensors} sensors completed[/green]")
            self.console.print(f"  Throughput: {throughput:.2f} samples/sec")
            self.console.print(f"  Avg CPU: {avg_cpu:.1f}%, Max Memory: {max_memory:.1f}MB")
            
            return result
            
        except Exception as e:
            metrics_task.cancel()
            self.console.print(f"[red]✗ Error testing {algorithm} with {num_sensors} sensors: {e}[/red]")
            return {
                'algorithm': algorithm,
                'num_sensors': num_sensors,
                'duration': duration,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def run(self, test_duration: int = 60) -> Dict[str, Any]:
        """
        전체 확장성 실험 실행
        
        Args:
            test_duration: 각 테스트의 지속 시간 (초)
            
        Returns:
            전체 실험 결과
        """
        self.console.print("[bold blue]🚀 ICS Sensor Privacy Scalability Experiment Started[/bold blue]")
        self.console.print(f"Server: {self.server_config.url}")
        self.console.print(f"Algorithms: {', '.join(self.algorithms)}")
        self.console.print(f"Sensor counts: {self.sensor_counts}")
        self.console.print(f"Test duration per configuration: {test_duration}s")
        self.console.print("-" * 60)
        
        # 총 테스트 수 계산
        total_tests = len(self.algorithms) * len(self.sensor_counts)
        
        # 진행상황 표시
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task("Overall Progress", total=total_tests)
            
            # 각 알고리즘별로 실험 실행
            for algorithm in self.algorithms:
                algorithm_results = []
                
                # 각 센서 수별로 테스트
                for sensor_count in self.sensor_counts:
                    test_desc = f"Testing {algorithm} ({sensor_count} sensors)"
                    test_task = progress.add_task(test_desc, total=1)
                    
                    try:
                        # 테스트 실행
                        result = await self.test_algorithm(algorithm, sensor_count, test_duration)
                        algorithm_results.append(result)
                        self.experiment_results.append(result)
                        
                        progress.update(test_task, advance=1)
                        progress.update(main_task, advance=1)
                        
                        # 잠시 대기 (시스템 안정화)
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        self.console.print(f"[red]Error in {test_desc}: {e}[/red]")
                        progress.update(test_task, advance=1)
                        progress.update(main_task, advance=1)
                
                self.console.print(f"[cyan]Completed all tests for {algorithm}[/cyan]")
        
        # 결과 저장
        await self.save_results()
        
        # 결과 표시
        self.display_results_table()
        
        # 그래프 생성
        self.plot_results()
        
        experiment_summary = {
            'total_tests': total_tests,
            'completed_tests': len(self.experiment_results),
            'algorithms_tested': self.algorithms,
            'sensor_counts_tested': self.sensor_counts,
            'test_duration_per_config': test_duration,
            'results_saved_to': str(self.results_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        self.console.print("[bold green]✅ Scalability Experiment Completed![/bold green]")
        return experiment_summary
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        현재 시스템 메트릭 수집
        
        Returns:
            시스템 메트릭 딕셔너리
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        metrics = {
            'timestamp': time.time(),
            'cpu_percent': cpu_percent,
            'memory_used_mb': memory.used / (1024 * 1024),
            'memory_available_mb': memory.available / (1024 * 1024),
            'memory_percent': memory.percent
        }
        
        self.metrics_history.append(metrics)
        return metrics
    
    async def save_results(self) -> None:
        """
        실험 결과를 JSON 및 CSV 파일로 저장
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = self.results_dir / f"scalability_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'experiment_config': {
                    'sensor_counts': self.sensor_counts,
                    'algorithms': self.algorithms,
                    'server_config': self.server_config.__dict__
                },
                'results': self.experiment_results,
                'metrics_history': self.metrics_history
            }, f, indent=2, ensure_ascii=False)
        
        # CSV 저장 (분석용)
        if self.experiment_results:
            csv_file = self.results_dir / f"scalability_results_{timestamp}.csv"
            df = pd.DataFrame(self.experiment_results)
            df.to_csv(csv_file, index=False, encoding='utf-8')
        
        self.console.print(f"[green]Results saved to:[/green]")
        self.console.print(f"  JSON: {json_file}")
        if self.experiment_results:
            self.console.print(f"  CSV: {csv_file}")
    
    def display_results_table(self) -> None:
        """
        실험 결과를 테이블 형태로 표시
        """
        if not self.experiment_results:
            self.console.print("[yellow]No results to display[/yellow]")
            return
        
        # 알고리즘별로 그룹화
        for algorithm in self.algorithms:
            algo_results = [r for r in self.experiment_results if r.get('algorithm') == algorithm]
            
            if not algo_results:
                continue
            
            table = Table(title=f"{algorithm.upper()} Performance Results")
            table.add_column("Sensors", style="cyan")
            table.add_column("Throughput\n(samples/sec)", style="green")
            table.add_column("Avg CPU\n(%)", style="yellow")
            table.add_column("Max Memory\n(MB)", style="red")
            table.add_column("Gen Time\n(ms)", style="blue")
            table.add_column("Verify Time\n(ms)", style="magenta")
            table.add_column("Error Rate\n(%)", style="red")
            
            for result in sorted(algo_results, key=lambda x: x.get('num_sensors', 0)):
                if 'error' in result:
                    continue
                    
                table.add_row(
                    str(result.get('num_sensors', 0)),
                    f"{result.get('throughput_samples_per_sec', 0):.2f}",
                    f"{result.get('avg_cpu_percent', 0):.1f}",
                    f"{result.get('max_memory_mb', 0):.1f}",
                    f"{result.get('avg_generation_time_ms', 0):.3f}",
                    f"{result.get('avg_verification_time_ms', 0):.3f}",
                    f"{result.get('error_rate_percent', 0):.2f}"
                )
            
            self.console.print(table)
            self.console.print()
    
    def plot_results(self) -> None:
        """
        확장성 그래프 생성 및 저장
        """
        if not self.experiment_results:
            self.console.print("[yellow]No results to plot[/yellow]")
            return
        
        # 데이터프레임 생성
        df = pd.DataFrame([r for r in self.experiment_results if 'error' not in r])
        
        if df.empty:
            self.console.print("[yellow]No valid results to plot[/yellow]")
            return
        
        # 그래프 스타일 설정
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 서브플롯 생성
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('ICS Sensor Privacy System - Scalability Analysis', fontsize=16, fontweight='bold')
        
        # 1. 처리량 vs 센서 수
        ax1 = axes[0, 0]
        for algorithm in self.algorithms:
            algo_data = df[df['algorithm'] == algorithm]
            if not algo_data.empty:
                ax1.plot(algo_data['num_sensors'], algo_data['throughput_samples_per_sec'], 
                        marker='o', linewidth=2, markersize=6, label=algorithm.upper())
        
        ax1.set_xlabel('Number of Sensors')
        ax1.set_ylabel('Throughput (samples/sec)')
        ax1.set_title('Throughput vs Number of Sensors')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. CPU 사용률 vs 센서 수
        ax2 = axes[0, 1]
        for algorithm in self.algorithms:
            algo_data = df[df['algorithm'] == algorithm]
            if not algo_data.empty:
                ax2.plot(algo_data['num_sensors'], algo_data['avg_cpu_percent'], 
                        marker='s', linewidth=2, markersize=6, label=algorithm.upper())
        
        ax2.set_xlabel('Number of Sensors')
        ax2.set_ylabel('Average CPU Usage (%)')
        ax2.set_title('CPU Usage vs Number of Sensors')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 메모리 사용량 vs 센서 수
        ax3 = axes[1, 0]
        for algorithm in self.algorithms:
            algo_data = df[df['algorithm'] == algorithm]
            if not algo_data.empty:
                ax3.plot(algo_data['num_sensors'], algo_data['max_memory_mb'], 
                        marker='^', linewidth=2, markersize=6, label=algorithm.upper())
        
        ax3.set_xlabel('Number of Sensors')
        ax3.set_ylabel('Max Memory Usage (MB)')
        ax3.set_title('Memory Usage vs Number of Sensors')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 처리 시간 비교 (생성 + 검증)
        ax4 = axes[1, 1]
        for algorithm in self.algorithms:
            algo_data = df[df['algorithm'] == algorithm]
            if not algo_data.empty:
                total_time = algo_data['avg_generation_time_ms'] + algo_data['avg_verification_time_ms']
                ax4.plot(algo_data['num_sensors'], total_time, 
                        marker='d', linewidth=2, markersize=6, label=algorithm.upper())
        
        ax4.set_xlabel('Number of Sensors')
        ax4.set_ylabel('Total Processing Time (ms)')
        ax4.set_title('Total Processing Time vs Number of Sensors')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.set_yscale('log')  # 로그 스케일로 차이 명확히 표시
        
        plt.tight_layout()
        
        # 그래프 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_file = self.results_dir / f"scalability_plots_{timestamp}.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        self.console.print(f"[green]Scalability plots saved to: {plot_file}[/green]")


# 실행 예제
if __name__ == "__main__":
    async def main():
        print("🔬 ICS Sensor Privacy Scalability Experiment")
        print("=" * 60)
        
        # 서버 설정
        server_config = ServerConfig(host="localhost", port=8084)
        
        # 실험 생성
        experiment = ScalabilityExperiment(server_config)
        
        try:
            # 실험 실행 (각 설정당 30초씩 테스트)
            results = await experiment.run(test_duration=30)
            
            print(f"\n✅ Experiment completed successfully!")
            print(f"Total tests: {results['completed_tests']}/{results['total_tests']}")
            print(f"Results saved to: {results['results_saved_to']}")
            
        except KeyboardInterrupt:
            print("\n⚠️ Experiment interrupted by user")
        except Exception as e:
            print(f"\n❌ Experiment failed: {e}")
    
    # 실험 실행
    asyncio.run(main())
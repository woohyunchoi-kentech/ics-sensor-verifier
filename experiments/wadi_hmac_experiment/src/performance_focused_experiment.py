#!/usr/bin/env python3
"""
성능 측정 중심 WADI HMAC 실험
=============================

외부 서버 검증 대신 HMAC 성능 측정에 집중
"""

import asyncio
import json
import time
import hmac
import hashlib
import base64
import logging
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass

from experiment_runner import ExperimentConfig
from hmac_client import ClientResult

# 서버 HMAC 키 (제공된 키 사용)
SERVER_KEY = base64.b64decode("jlbAU8PyY1wTVvQBgZH/qcDIwjN24sluCCDOEJXJsCs=")

@dataclass
class PerformanceMetrics:
    """성능 측정 결과"""
    timestamp: datetime
    sensor_count: int
    frequency: int
    hmac_generation_time_ms: float
    data_serialization_time_ms: float
    network_simulation_time_ms: float
    cpu_usage_percent: float
    memory_usage_mb: float
    data_size_bytes: int
    throughput_mbps: float

class PerformanceFocusedClient:
    """성능 측정 중심 HMAC 클라이언트"""
    
    def __init__(self):
        self.key = SERVER_KEY
        
        # WADI 데이터 로더
        from wadi_data_loader import WADIDataLoader
        self.data_loader = WADIDataLoader()
        self.data_loader.load_data()
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        print(f"🔑 HMAC 성능 측정 클라이언트 초기화")
        print(f"   키 길이: {len(self.key)} 바이트")
        print(f"📊 성능 측정 모드: HMAC 생성 + 데이터 직렬화 + 시뮬레이션")
    
    def calculate_hmac_performance(self, sensor_value: float, timestamp: int) -> tuple:
        """
        HMAC 계산 성능 측정
        Returns: (hmac_hex, generation_time_ms)
        """
        # 메시지 형식: sensor_value:timestamp
        message = f"{sensor_value}:{timestamp}".encode('utf-8')
        
        # HMAC 생성 시간 측정
        start_time = time.perf_counter()
        signature = hmac.new(self.key, message, hashlib.sha256).digest()
        hmac_hex = signature.hex()
        end_time = time.perf_counter()
        
        generation_time_ms = (end_time - start_time) * 1000
        
        return hmac_hex, generation_time_ms
    
    async def simulate_data_processing(self, data: Dict[str, Any]) -> PerformanceMetrics:
        """
        데이터 처리 성능 시뮬레이션
        """
        start_time = time.perf_counter()
        
        # CPU/메모리 사용률 측정
        cpu_before = psutil.cpu_percent()
        memory_before = psutil.virtual_memory()
        
        try:
            # 센서 값 추출
            sensor_values = data.get('sensor_values', {})
            if sensor_values:
                first_sensor_value = float(list(sensor_values.values())[0])
                sensor_id = str(list(sensor_values.keys())[0])
            else:
                first_sensor_value = 2.45
                sensor_id = "WADI_TEST"
            
            # 타임스탬프 생성
            timestamp = int(time.time())
            
            # HMAC 생성 성능 측정
            hmac_hex, hmac_generation_time = self.calculate_hmac_performance(
                first_sensor_value, timestamp
            )
            
            # 데이터 직렬화 시간 측정
            serialization_start = time.perf_counter()
            
            request_payload = {
                "sensor_value": first_sensor_value,
                "timestamp": timestamp,
                "received_mac": hmac_hex,
                "sensor_id": sensor_id
            }
            
            json_data = json.dumps(request_payload)
            data_size = len(json_data.encode('utf-8'))
            
            serialization_end = time.perf_counter()
            serialization_time = (serialization_end - serialization_start) * 1000
            
            # 네트워크 시뮬레이션 (실제 전송 없이 대기만)
            network_start = time.perf_counter()
            # 실제 네트워크 대기 시뮬레이션 (1-10ms)
            await asyncio.sleep(np.random.uniform(0.001, 0.01))
            network_end = time.perf_counter()
            network_time = (network_end - network_start) * 1000
            
            # CPU/메모리 사용률 측정
            cpu_after = psutil.cpu_percent()
            memory_after = psutil.virtual_memory()
            
            cpu_usage = max(cpu_after, cpu_before)  # 더 높은 값 사용
            memory_usage_mb = memory_after.used / (1024 * 1024)
            
            # 처리량 계산 (MB/s)
            total_time_s = (time.perf_counter() - start_time)
            throughput_mbps = (data_size / (1024 * 1024)) / max(total_time_s, 0.001)
            
            return PerformanceMetrics(
                timestamp=datetime.now(),
                sensor_count=len(data.get('sensor_values', {})),
                frequency=data.get('frequency', 1),
                hmac_generation_time_ms=hmac_generation_time,
                data_serialization_time_ms=serialization_time,
                network_simulation_time_ms=network_time,
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory_usage_mb,
                data_size_bytes=data_size,
                throughput_mbps=throughput_mbps
            )
            
        except Exception as e:
            self.logger.error(f"Performance measurement failed: {str(e)}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                sensor_count=0,
                frequency=1,
                hmac_generation_time_ms=0.0,
                data_serialization_time_ms=0.0,
                network_simulation_time_ms=0.0,
                cpu_usage_percent=0.0,
                memory_usage_mb=0.0,
                data_size_bytes=0,
                throughput_mbps=0.0
            )
    
    async def run_streaming_performance_test(self, sensor_count: int, frequency: int, duration: int = 1000) -> List[PerformanceMetrics]:
        """
        스트리밍 성능 테스트 실행
        """
        self.logger.info(f"Starting performance test: {sensor_count} sensors, {frequency}Hz, {duration}s")
        
        # 센서 선택
        selected_sensors = self.data_loader.select_sensors(sensor_count)
        
        # 스트리밍 데이터 생성
        streaming_data = self.data_loader.get_streaming_data(
            sensors=selected_sensors,
            frequency=frequency,
            duration=duration
        )
        
        results = []
        total_requests = len(streaming_data)
        
        # 전송 시작
        start_time = time.time()
        interval = 1.0 / frequency
        
        for i, data_point in enumerate(streaming_data):
            # 정확한 타이밍 유지
            target_time = start_time + (i * interval)
            current_time = time.time()
            
            if current_time < target_time:
                await asyncio.sleep(target_time - current_time)
            
            # 성능 측정
            metrics = await self.simulate_data_processing(data_point)
            results.append(metrics)
            
            # 진행 상황 로깅 (100개마다)
            if (i + 1) % 100 == 0:
                avg_hmac_time = np.mean([r.hmac_generation_time_ms for r in results[-100:]])
                avg_throughput = np.mean([r.throughput_mbps for r in results[-100:]])
                self.logger.info(f"Progress: {i+1}/{total_requests}, Avg HMAC: {avg_hmac_time:.3f}ms, Throughput: {avg_throughput:.1f}MB/s")
        
        avg_hmac_time = np.mean([r.hmac_generation_time_ms for r in results])
        self.logger.info(f"Performance test completed: {len(results)} samples, Avg HMAC time: {avg_hmac_time:.3f}ms")
        return results

class PerformanceHMACExperiment:
    """성능 중심 HMAC 실험"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.client = PerformanceFocusedClient()
        self.results_dir = Path(config.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 실험 ID
        self.experiment_id = f"wadi_hmac_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
    async def run_full_experiment(self):
        """전체 실험 실행"""
        self.logger.info(f"Starting full performance experiment: {self.experiment_id}")
        
        all_results = {}
        
        for sensor_count in self.config.sensor_counts:
            self.logger.info(f"Testing sensor count: {sensor_count}")
            sensor_results = {}
            
            for frequency in self.config.frequencies:
                self.logger.info(f"Testing frequency: {frequency}Hz")
                
                # 성능 테스트 실행
                results = await self.client.run_streaming_performance_test(
                    sensor_count=sensor_count,
                    frequency=frequency,
                    duration=self.config.duration_seconds
                )
                
                sensor_results[frequency] = results
            
            all_results[sensor_count] = sensor_results
            
            # 센서 수별 결과 저장 및 시각화
            await self.save_and_visualize_results(sensor_count, sensor_results)
        
        # 전체 결과 저장
        await self.save_comprehensive_results(all_results)
        
        self.logger.info(f"Experiment completed! Results saved to: {self.results_dir}")
    
    async def save_and_visualize_results(self, sensor_count: int, results: Dict[int, List[PerformanceMetrics]]):
        """결과 저장 및 시각화"""
        
        # CSV 저장
        csv_filename = self.results_dir / f"performance_sensors_{sensor_count}.csv"
        
        all_data = []
        for frequency, metrics_list in results.items():
            for metrics in metrics_list:
                data_row = {
                    'timestamp': metrics.timestamp,
                    'sensor_count': metrics.sensor_count,
                    'frequency': metrics.frequency,
                    'hmac_generation_time_ms': metrics.hmac_generation_time_ms,
                    'data_serialization_time_ms': metrics.data_serialization_time_ms,
                    'network_simulation_time_ms': metrics.network_simulation_time_ms,
                    'cpu_usage_percent': metrics.cpu_usage_percent,
                    'memory_usage_mb': metrics.memory_usage_mb,
                    'data_size_bytes': metrics.data_size_bytes,
                    'throughput_mbps': metrics.throughput_mbps
                }
                all_data.append(data_row)
        
        df = pd.DataFrame(all_data)
        df.to_csv(csv_filename, index=False)
        
        # 시각화
        await self.create_performance_visualizations(sensor_count, results)
    
    async def create_performance_visualizations(self, sensor_count: int, results: Dict[int, List[PerformanceMetrics]]):
        """성능 시각화 생성"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'WADI HMAC Performance - {sensor_count} Sensors', fontsize=16)
        
        frequencies = sorted(results.keys())
        
        # 1. HMAC 생성 시간
        hmac_times = []
        for freq in frequencies:
            times = [m.hmac_generation_time_ms for m in results[freq]]
            hmac_times.append(np.mean(times))
        
        ax1.plot(frequencies, hmac_times, 'b-o', linewidth=2, markersize=8)
        ax1.set_xlabel('Frequency (Hz)')
        ax1.set_ylabel('HMAC Generation Time (ms)')
        ax1.set_title('Average HMAC Generation Time')
        ax1.grid(True)
        ax1.set_xscale('log')
        
        # 2. 처리량
        throughputs = []
        for freq in frequencies:
            tps = [m.throughput_mbps for m in results[freq]]
            throughputs.append(np.mean(tps))
        
        ax2.plot(frequencies, throughputs, 'g-o', linewidth=2, markersize=8)
        ax2.set_xlabel('Frequency (Hz)')
        ax2.set_ylabel('Throughput (MB/s)')
        ax2.set_title('Average Throughput')
        ax2.grid(True)
        ax2.set_xscale('log')
        
        # 3. CPU 사용률
        cpu_usages = []
        for freq in frequencies:
            cpus = [m.cpu_usage_percent for m in results[freq]]
            cpu_usages.append(np.mean(cpus))
        
        ax3.plot(frequencies, cpu_usages, 'r-o', linewidth=2, markersize=8)
        ax3.set_xlabel('Frequency (Hz)')
        ax3.set_ylabel('CPU Usage (%)')
        ax3.set_title('Average CPU Usage')
        ax3.grid(True)
        ax3.set_xscale('log')
        
        # 4. 메모리 사용량
        memory_usages = []
        for freq in frequencies:
            mems = [m.memory_usage_mb for m in results[freq]]
            memory_usages.append(np.mean(mems))
        
        ax4.plot(frequencies, memory_usages, 'm-o', linewidth=2, markersize=8)
        ax4.set_xlabel('Frequency (Hz)')
        ax4.set_ylabel('Memory Usage (MB)')
        ax4.set_title('Average Memory Usage')
        ax4.grid(True)
        ax4.set_xscale('log')
        
        plt.tight_layout()
        
        # 저장
        plot_filename = self.results_dir / f"performance_plot_sensors_{sensor_count}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📊 Performance visualization saved: {plot_filename}")
    
    async def save_comprehensive_results(self, all_results: Dict[int, Dict[int, List[PerformanceMetrics]]]):
        """종합 결과 저장"""
        
        # 종합 통계 계산
        summary_data = []
        
        for sensor_count, freq_results in all_results.items():
            for frequency, metrics_list in freq_results.items():
                avg_metrics = {
                    'sensor_count': sensor_count,
                    'frequency': frequency,
                    'total_samples': len(metrics_list),
                    'avg_hmac_generation_ms': np.mean([m.hmac_generation_time_ms for m in metrics_list]),
                    'std_hmac_generation_ms': np.std([m.hmac_generation_time_ms for m in metrics_list]),
                    'avg_serialization_ms': np.mean([m.data_serialization_time_ms for m in metrics_list]),
                    'avg_network_simulation_ms': np.mean([m.network_simulation_time_ms for m in metrics_list]),
                    'avg_cpu_usage': np.mean([m.cpu_usage_percent for m in metrics_list]),
                    'avg_memory_mb': np.mean([m.memory_usage_mb for m in metrics_list]),
                    'avg_throughput_mbps': np.mean([m.throughput_mbps for m in metrics_list]),
                    'total_data_processed_mb': sum([m.data_size_bytes for m in metrics_list]) / (1024 * 1024)
                }
                summary_data.append(avg_metrics)
        
        # 종합 CSV 저장
        summary_df = pd.DataFrame(summary_data)
        summary_filename = self.results_dir / f"{self.experiment_id}_summary.csv"
        summary_df.to_csv(summary_filename, index=False)
        
        print(f"📄 Comprehensive results saved: {summary_filename}")

async def main():
    """메인 성능 실험"""
    print("🔑 WADI HMAC 성능 측정 실험")
    print("=" * 60)
    print("🎯 목표: HMAC 생성 성능, 처리량, 시스템 자원 사용률 측정")
    print("📊 방식: 외부 서버 검증 없이 순수 성능 측정")
    
    # 실험 설정
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],
        duration_seconds=1000,
        server_host="localhost",  # 사용하지 않음
        server_port=0,  # 사용하지 않음
        results_dir="../results"
    )
    
    print(f"🎯 실험 설정:")
    print(f"  • 센서: {config.sensor_counts}")
    print(f"  • 주파수: {config.frequencies} Hz")
    print(f"  • 시간: {config.duration_seconds}초/조건")
    print(f"  • 결과 저장: {config.results_dir}")
    
    total_conditions = len(config.sensor_counts) * len(config.frequencies)
    total_time_hours = total_conditions * config.duration_seconds / 3600
    print(f"  • 총 조건: {total_conditions}개")
    print(f"  • 예상 시간: {total_time_hours:.1f}시간")
    
    print("\n🚀 성능 측정 실험 시작!")
    
    experiment = PerformanceHMACExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 실험 완료! 결과: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 중단됨")
        
    except Exception as e:
        print(f"\n❌ 실패: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
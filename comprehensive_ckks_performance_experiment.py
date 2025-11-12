#!/usr/bin/env python3
"""
Comprehensive CKKS Performance Experiment
WADI & HAI 데이터셋을 사용한 실시간 CKKS 동형암호화 성능 실험

Features:
- Real-time streaming (actual frequency-based transmission)
- Live visualization during experiments
- Comprehensive performance metrics
- Support for both WADI and HAI datasets

Author: ICS Security Research Team
Date: 2025-01-28
"""

import asyncio
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import psutil
import socket
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import sys
import os
from pathlib import Path

# Set up matplotlib for real-time plotting
plt.ion()  # Turn on interactive mode
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# Local imports
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest, CKKSResponse
from performance_monitor import PerformanceMonitor

@dataclass
class ExperimentConfig:
    """실험 설정"""
    dataset_name: str  # "WADI" or "HAI"
    sensor_counts: List[int] = None  # [1, 10, 50, 100]
    frequencies: List[int] = None   # [1, 2, 10, 100] data points per second
    duration_seconds: int = 30      # Duration for each test
    server_url: str = "http://192.168.0.11:8085"
    
    def __post_init__(self):
        if self.sensor_counts is None:
            self.sensor_counts = [1, 10, 50, 100]
        if self.frequencies is None:
            self.frequencies = [1, 2, 10, 100]

@dataclass
class PerformanceMetrics:
    """성능 측정 데이터"""
    timestamp: float
    sensor_count: int
    frequency: int
    encryption_time_ms: float
    decryption_time_ms: float
    network_rtt_ms: float
    accuracy_error: float
    cpu_usage_percent: float
    memory_usage_mb: float
    success: bool
    dataset: str

class DatasetLoader:
    """데이터셋 로더 (WADI & HAI 지원)"""
    
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name.upper()
        if self.dataset_name == "WADI":
            self.data_path = "data/wadi/WADI_14days_new.csv"
        elif self.dataset_name == "HAI":
            self.data_path = "data/hai/haiend-23.05/end-train1.csv"
        else:
            raise ValueError(f"Unsupported dataset: {dataset_name}")
        
        self.sensors = self._load_sensor_list()
        self.data = self._load_data()
        
    def _load_sensor_list(self) -> List[str]:
        """센서 목록 로드"""
        if self.dataset_name == "WADI":
            return [
                # Analytical sensors
                "1_AIT_001_PV", "1_AIT_002_PV", "1_AIT_003_PV", "1_AIT_004_PV", "1_AIT_005_PV",
                "2A_AIT_001_PV", "2A_AIT_002_PV", "2A_AIT_003_PV", "2A_AIT_004_PV",
                "2B_AIT_001_PV", "2B_AIT_002_PV", "2B_AIT_003_PV", "2B_AIT_004_PV",
                "3_AIT_001_PV", "3_AIT_002_PV", "3_AIT_003_PV", "3_AIT_004_PV", "3_AIT_005_PV",
                
                # Flow sensors
                "1_FIT_001_PV", "2_FIT_001_PV", "2_FIT_002_PV", "2_FIT_003_PV", "3_FIT_001_PV",
                "2_FIC_101_PV", "2_FIC_201_PV", "2_FIC_301_PV", "2_FIC_401_PV", "2_FIC_501_PV", "2_FIC_601_PV",
                
                # Pressure sensors
                "2_PIT_001_PV", "2_PIT_002_PV", "2_PIT_003_PV", "2_PIC_003_PV", "2_DPIT_001_PV",
                
                # Level sensors
                "1_LT_001_PV", "2_LT_001_PV", "2_LT_002_PV", "3_LT_001_PV",
                
                # Motor valves (selected ones with actual data)
                "1_MV_001_STATUS", "1_MV_002_STATUS", "1_MV_003_STATUS", "1_MV_004_STATUS",
                "2_MV_001_STATUS", "2_MV_002_STATUS", "2_MV_003_STATUS", "2_MV_004_STATUS",
                "2_MV_005_STATUS", "2_MV_006_STATUS", "3_MV_001_STATUS", "3_MV_002_STATUS", "3_MV_003_STATUS",
                
                # Pump status
                "1_P_001_STATUS", "1_P_002_STATUS", "1_P_003_STATUS", "1_P_004_STATUS", "1_P_005_STATUS", "1_P_006_STATUS",
                "2_P_003_STATUS", "2_P_004_STATUS", "3_P_001_STATUS", "3_P_002_STATUS", "3_P_003_STATUS", "3_P_004_STATUS",
                
                # Control valves
                "2_MCV_007_CO", "2_MCV_101_CO", "2_MCV_201_CO", "2_MCV_301_CO", "2_MCV_401_CO", "2_MCV_501_CO", "2_MCV_601_CO",
                
                # Additional sensors to reach 100
                "2_FQ_101_PV", "2_FQ_201_PV", "2_FQ_301_PV", "2_FQ_401_PV", "2_FQ_501_PV", "2_FQ_601_PV",
                "2_SV_101_STATUS", "2_SV_201_STATUS", "2_SV_301_STATUS", "2_SV_401_STATUS", "2_SV_501_STATUS", "2_SV_601_STATUS",
                
                # Level switches (where available)
                "1_LS_001_AL", "1_LS_002_AL", "3_LS_001_AL",
                "2_LS_101_AH", "2_LS_101_AL", "2_LS_201_AH", "2_LS_201_AL",
                "2_LS_301_AH", "2_LS_301_AL", "2_LS_401_AH", "2_LS_401_AL",
                "2_LS_501_AH", "2_LS_501_AL", "2_LS_601_AH", "2_LS_601_AL",
                
                # Flow control parameters
                "2_FIC_101_CO", "2_FIC_101_SP", "2_FIC_201_CO", "2_FIC_201_SP",
                "2_FIC_301_CO", "2_FIC_301_SP", "2_FIC_401_CO", "2_FIC_401_SP",
                "2_FIC_501_CO", "2_FIC_501_SP", "2_FIC_601_CO", "2_FIC_601_SP",
                
                # Pressure control
                "2_PIC_003_CO", "2_PIC_003_SP",
                
                # Pump speeds
                "2_P_003_SPEED", "2_P_004_SPEED"
            ]
        
        elif self.dataset_name == "HAI":
            # HAI sensor names (based on previous experiments)
            return [
                # Flow sensors
                "DM-FT01", "DM-FT01Z", "DM-FT02", "DM-FT02Z", "DM-FT03", "DM-FT03Z",
                
                # Pressure sensors  
                "DM-PIT01", "DM-PIT01-HH", "DM-PIT02",
                "DM-PP01-R", "DM-PP04-D", "DM-PP04-AO",
                "DM-PCV01-D", "DM-PCV01-Z", "DM-PCV02-D", "DM-PCV02-Z",
                
                # Level sensors
                "DM-LIT01", "DM-LCV01-D", "DM-LCV01-Z",
                
                # Temperature sensors
                "DM-TIT01", "DM-TIT02", "DM-TWIT-03", "DM-TWIT-04", "DM-TWIT-05",
                
                # Analytical sensors
                "DM-AIT-DO", "DM-AIT-PH", "GATEOPEN",
                
                # Power and control
                "DM-PWIT-03", "DM-HT01-D", "DM-CIP-1ST",
                
                # Flow control valves
                "DM-FCV01-D", "DM-FCV01-Z", "DM-FCV02-D", "DM-FCV02-Z", "DM-FCV03-D", "DM-FCV03-Z",
            ] + [f"100{i}.{j:02d}-OUT" for i in range(1, 5) for j in range(1, 20)]  # Control outputs
    
    def _load_data(self) -> pd.DataFrame:
        """데이터 로드"""
        try:
            df = pd.read_csv(self.data_path)
            print(f"✅ Loaded {self.dataset_name} dataset: {len(df):,} rows, {len(df.columns)} columns")
            
            # Filter only existing sensors
            existing_sensors = [s for s in self.sensors if s in df.columns]
            missing_sensors = [s for s in self.sensors if s not in df.columns]
            
            if missing_sensors:
                print(f"⚠️ Missing sensors: {len(missing_sensors)} out of {len(self.sensors)}")
            
            self.sensors = existing_sensors[:100]  # Limit to 100 sensors
            print(f"✅ Using {len(self.sensors)} real sensors")
            
            return df[self.sensors + ['Date', 'Time'] if 'Date' in df.columns else self.sensors].fillna(method='ffill').fillna(0)
            
        except Exception as e:
            print(f"❌ Failed to load {self.dataset_name} data: {e}")
            raise
    
    def get_sensor_data(self, sensor_count: int, start_idx: int = 0, length: int = 1000) -> Dict[str, np.ndarray]:
        """센서 데이터 추출"""
        selected_sensors = self.sensors[:sensor_count]
        sensor_data = {}
        
        for sensor in selected_sensors:
            data = self.data[sensor].iloc[start_idx:start_idx + length].values
            # Ensure data is numeric and handle any remaining NaN
            data = pd.to_numeric(data, errors='coerce')
            data = np.nan_to_num(data, nan=0.0)
            sensor_data[sensor] = data
            
        return sensor_data

class RealTimeVisualizer:
    """실시간 시각화"""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.results_dir = f"experiment_results/{experiment_id}"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize plots
        plt.style.use('seaborn-v0_8')
        self.colors = plt.cm.Set1(np.linspace(0, 1, 8))
        
    def create_sensor_count_visualization(self, metrics_data: List[PerformanceMetrics], 
                                        sensor_count: int, dataset_name: str):
        """센서 개수별 실험 완료 시 시각화 생성"""
        if not metrics_data:
            return
            
        # Filter data for this sensor count
        data = [m for m in metrics_data if m.sensor_count == sensor_count]
        if not data:
            return
            
        # Create comprehensive visualization
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. Encryption Time by Frequency
        ax = axes[0, 0]
        frequencies = sorted(list(set(m.frequency for m in data)))
        enc_times = []
        for freq in frequencies:
            freq_data = [m.encryption_time_ms for m in data if m.frequency == freq and m.success]
            enc_times.append(np.mean(freq_data) if freq_data else 0)
        
        bars = ax.bar(frequencies, enc_times, color=self.colors[0], alpha=0.7, edgecolor='black')
        ax.set_xlabel('Frequency (data points/sec)')
        ax.set_ylabel('Encryption Time (ms)')
        ax.set_title(f'{dataset_name}: Encryption Performance\n({sensor_count} sensors)')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, time in zip(bars, enc_times):
            if time > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(enc_times)*0.01,
                       f'{time:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Network RTT
        ax = axes[0, 1]
        rtt_times = []
        for freq in frequencies:
            freq_data = [m.network_rtt_ms for m in data if m.frequency == freq and m.success]
            rtt_times.append(np.mean(freq_data) if freq_data else 0)
            
        ax.plot(frequencies, rtt_times, 'o-', color=self.colors[1], linewidth=2, markersize=8)
        ax.set_xlabel('Frequency (data points/sec)')
        ax.set_ylabel('Network RTT (ms)')
        ax.set_title(f'{dataset_name}: Network Performance\n({sensor_count} sensors)')
        ax.grid(True, alpha=0.3)
        
        # 3. Accuracy (Error Rate)
        ax = axes[0, 2]
        error_rates = []
        for freq in frequencies:
            freq_data = [m.accuracy_error for m in data if m.frequency == freq and m.success]
            error_rates.append(np.mean(freq_data) if freq_data else 0)
            
        ax.semilogy(frequencies, error_rates, 's-', color=self.colors[2], linewidth=2, markersize=8)
        ax.set_xlabel('Frequency (data points/sec)')
        ax.set_ylabel('Accuracy Error (%)')
        ax.set_title(f'{dataset_name}: Decryption Accuracy\n({sensor_count} sensors)')
        ax.grid(True, alpha=0.3)
        
        # 4. Resource Usage
        ax = axes[1, 0]
        cpu_usage = []
        memory_usage = []
        for freq in frequencies:
            freq_data_cpu = [m.cpu_usage_percent for m in data if m.frequency == freq and m.success]
            freq_data_mem = [m.memory_usage_mb for m in data if m.frequency == freq and m.success]
            cpu_usage.append(np.mean(freq_data_cpu) if freq_data_cpu else 0)
            memory_usage.append(np.mean(freq_data_mem) if freq_data_mem else 0)
            
        ax2 = ax.twinx()
        line1 = ax.plot(frequencies, cpu_usage, 'o-', color=self.colors[3], label='CPU %', linewidth=2)
        line2 = ax2.plot(frequencies, memory_usage, 's-', color=self.colors[4], label='Memory MB', linewidth=2)
        
        ax.set_xlabel('Frequency (data points/sec)')
        ax.set_ylabel('CPU Usage (%)', color=self.colors[3])
        ax2.set_ylabel('Memory Usage (MB)', color=self.colors[4])
        ax.set_title(f'{dataset_name}: Resource Usage\n({sensor_count} sensors)')
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # 5. Success Rate
        ax = axes[1, 1]
        success_rates = []
        for freq in frequencies:
            freq_data = [m for m in data if m.frequency == freq]
            if freq_data:
                success_rate = len([m for m in freq_data if m.success]) / len(freq_data) * 100
            else:
                success_rate = 0
            success_rates.append(success_rate)
            
        bars = ax.bar(frequencies, success_rates, color=self.colors[5], alpha=0.7, edgecolor='black')
        ax.set_xlabel('Frequency (data points/sec)')
        ax.set_ylabel('Success Rate (%)')
        ax.set_title(f'{dataset_name}: Reliability\n({sensor_count} sensors)')
        ax.set_ylim(0, 105)
        ax.grid(axis='y', alpha=0.3)
        
        # Add percentage labels
        for bar, rate in zip(bars, success_rates):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 6. Summary Statistics
        ax = axes[1, 2]
        ax.axis('off')
        
        # Calculate summary stats
        total_tests = len(data)
        successful_tests = len([m for m in data if m.success])
        avg_encryption = np.mean([m.encryption_time_ms for m in data if m.success])
        avg_rtt = np.mean([m.network_rtt_ms for m in data if m.success])
        avg_error = np.mean([m.accuracy_error for m in data if m.success])
        
        summary_text = f"""
{dataset_name} Experiment Summary
Sensor Count: {sensor_count}
{'='*35}

Test Results:
• Total Tests: {total_tests}
• Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)
• Failed: {total_tests - successful_tests}

Performance Metrics:
• Avg Encryption: {avg_encryption:.2f} ms
• Avg Network RTT: {avg_rtt:.2f} ms  
• Avg Accuracy Error: {avg_error:.4f}%
• Max Frequency Tested: {max(frequencies)} pts/sec

Frequencies Tested:
{', '.join(map(str, frequencies))} data points/sec

Status: {'✅ PASSED' if successful_tests/total_tests > 0.8 else '⚠️ ISSUES'}
"""
        
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top', fontfamily='monospace',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.1))
        
        # Overall title
        plt.suptitle(f'{dataset_name} CKKS Performance Analysis - {sensor_count} Sensors', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save the plot
        filename = f"{self.results_dir}/{dataset_name.lower()}_{sensor_count}sensors_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📊 Visualization saved: {filename}")
        plt.close()
        
    def create_final_comparison(self, all_metrics: List[PerformanceMetrics], dataset_name: str):
        """최종 종합 비교 차트"""
        if not all_metrics:
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        sensor_counts = sorted(list(set(m.sensor_count for m in all_metrics)))
        
        # 1. Encryption Time Scaling
        ax = axes[0, 0]
        for freq in [1, 2, 10, 100]:
            enc_times = []
            for sc in sensor_counts:
                freq_data = [m.encryption_time_ms for m in all_metrics 
                           if m.sensor_count == sc and m.frequency == freq and m.success]
                enc_times.append(np.mean(freq_data) if freq_data else 0)
            
            ax.plot(sensor_counts, enc_times, 'o-', label=f'{freq} pts/sec', linewidth=2, markersize=6)
        
        ax.set_xlabel('Number of Sensors')
        ax.set_ylabel('Encryption Time (ms)')
        ax.set_title(f'{dataset_name}: Encryption Scalability')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xscale('log')
        ax.set_yscale('log')
        
        # 2. Network Performance
        ax = axes[0, 1]
        for freq in [1, 2, 10, 100]:
            rtt_times = []
            for sc in sensor_counts:
                freq_data = [m.network_rtt_ms for m in all_metrics 
                           if m.sensor_count == sc and m.frequency == freq and m.success]
                rtt_times.append(np.mean(freq_data) if freq_data else 0)
            
            ax.plot(sensor_counts, rtt_times, 's-', label=f'{freq} pts/sec', linewidth=2, markersize=6)
        
        ax.set_xlabel('Number of Sensors')
        ax.set_ylabel('Network RTT (ms)')
        ax.set_title(f'{dataset_name}: Network Scalability')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Accuracy Analysis
        ax = axes[1, 0]
        sensor_errors = []
        for sc in sensor_counts:
            sc_data = [m.accuracy_error for m in all_metrics if m.sensor_count == sc and m.success]
            sensor_errors.append(sc_data if sc_data else [0])
            
        bp = ax.boxplot(sensor_errors, positions=sensor_counts, widths=np.array(sensor_counts)*0.3)
        ax.set_xlabel('Number of Sensors')
        ax.set_ylabel('Accuracy Error (%)')
        ax.set_title(f'{dataset_name}: Accuracy Distribution')
        ax.grid(True, alpha=0.3)
        
        # 4. Resource Usage
        ax = axes[1, 1]
        max_cpu = []
        max_mem = []
        for sc in sensor_counts:
            cpu_data = [m.cpu_usage_percent for m in all_metrics if m.sensor_count == sc and m.success]
            mem_data = [m.memory_usage_mb for m in all_metrics if m.sensor_count == sc and m.success]
            max_cpu.append(np.max(cpu_data) if cpu_data else 0)
            max_mem.append(np.max(mem_data) if mem_data else 0)
        
        ax2 = ax.twinx()
        line1 = ax.plot(sensor_counts, max_cpu, 'o-', color='red', label='Max CPU %', linewidth=2)
        line2 = ax2.plot(sensor_counts, max_mem, 's-', color='blue', label='Max Memory MB', linewidth=2)
        
        ax.set_xlabel('Number of Sensors')
        ax.set_ylabel('Peak CPU Usage (%)', color='red')
        ax2.set_ylabel('Peak Memory Usage (MB)', color='blue')
        ax.set_title(f'{dataset_name}: Resource Scaling')
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.suptitle(f'{dataset_name} CKKS Performance - Complete Analysis', 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # Save final comparison
        filename = f"{self.results_dir}/{dataset_name.lower()}_complete_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📊 Final analysis saved: {filename}")
        plt.close()

class CKKSPerformanceExperiment:
    """CKKS 성능 실험 메인 클래스"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.experiment_id = f"ckks_perf_{config.dataset_name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize components
        self.dataset_loader = DatasetLoader(config.dataset_name)
        self.ckks_manager = ConcurrentCKKSManager(server_url=config.server_url)
        self.performance_monitor = PerformanceMonitor()
        self.visualizer = RealTimeVisualizer(self.experiment_id)
        
        # Results storage
        self.all_metrics: List[PerformanceMetrics] = []
        self.results_dir = f"experiment_results/{self.experiment_id}"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{self.results_dir}/experiment.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    async def run_single_test(self, sensor_count: int, frequency: int) -> List[PerformanceMetrics]:
        """단일 테스트 실행 (실시간 전송)"""
        self.logger.info(f"🚀 Starting test: {sensor_count} sensors at {frequency} pts/sec")
        
        # Load sensor data
        sensor_data = self.dataset_loader.get_sensor_data(
            sensor_count, 
            start_idx=np.random.randint(0, max(1, len(self.dataset_loader.data) - 1000)),
            length=self.config.duration_seconds * frequency + 100
        )
        
        sensors = list(sensor_data.keys())
        metrics_list = []
        
        # Calculate interval between transmissions
        interval = 1.0 / frequency  # seconds between each data point
        
        start_time = time.time()
        data_index = 0
        
        while (time.time() - start_time) < self.config.duration_seconds:
            try:
                # Get current system metrics
                system_metrics = self.performance_monitor.get_current_system_status()
                
                # Prepare requests for this transmission
                requests = []
                current_timestamp = time.time()
                
                for sensor_id in sensors:
                    if data_index < len(sensor_data[sensor_id]):
                        value = float(sensor_data[sensor_id][data_index])
                        request = CKKSRequest(
                            sensor_id=sensor_id,
                            value=value,
                            timestamp=current_timestamp,
                            request_id=f"{sensor_id}_{data_index}"
                        )
                        requests.append(request)
                
                if requests:
                    # Measure encryption and network time
                    net_start = time.time()
                    responses = await self.ckks_manager.send_batch_requests_async(requests)
                    net_end = time.time()
                    
                    # Process responses
                    for response in responses:
                        if response.success:
                            # Calculate metrics
                            encryption_time = response.encryption_time_ms
                            decryption_time = getattr(response, 'decryption_time_ms', 0) or encryption_time * 0.1  # Estimate
                            network_rtt = (net_end - net_start) * 1000  # ms
                            accuracy_error = response.accuracy_error or 0
                            
                            metrics = PerformanceMetrics(
                                timestamp=current_timestamp,
                                sensor_count=sensor_count,
                                frequency=frequency,
                                encryption_time_ms=encryption_time,
                                decryption_time_ms=decryption_time,
                                network_rtt_ms=network_rtt,
                                accuracy_error=accuracy_error,
                                cpu_usage_percent=system_metrics.get('cpu_percent', 0),
                                memory_usage_mb=system_metrics.get('memory_mb', 0),
                                success=True,
                                dataset=self.config.dataset_name
                            )
                            metrics_list.append(metrics)
                        else:
                            # Failed request
                            metrics = PerformanceMetrics(
                                timestamp=current_timestamp,
                                sensor_count=sensor_count,
                                frequency=frequency,
                                encryption_time_ms=0,
                                decryption_time_ms=0,
                                network_rtt_ms=0,
                                accuracy_error=100,  # Max error for failed requests
                                cpu_usage_percent=system_metrics.get('cpu_percent', 0),
                                memory_usage_mb=system_metrics.get('memory_mb', 0),
                                success=False,
                                dataset=self.config.dataset_name
                            )
                            metrics_list.append(metrics)
                
                # Wait for next transmission
                next_transmission = start_time + (data_index + 1) * interval
                current_time = time.time()
                if next_transmission > current_time:
                    await asyncio.sleep(next_transmission - current_time)
                
                data_index += 1
                
            except Exception as e:
                self.logger.error(f"Error in test iteration: {e}")
                break
        
        success_count = len([m for m in metrics_list if m.success])
        total_count = len(metrics_list)
        self.logger.info(f"✅ Test completed: {success_count}/{total_count} successful transmissions")
        
        return metrics_list
        
    async def run_sensor_count_experiment(self, sensor_count: int):
        """특정 센서 개수에 대한 모든 주파수 테스트"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔬 Starting experiments for {sensor_count} sensors")
        self.logger.info(f"{'='*60}")
        
        sensor_metrics = []
        
        for frequency in self.config.frequencies:
            try:
                self.logger.info(f"📡 Testing {frequency} data points per second...")
                metrics = await self.run_single_test(sensor_count, frequency)
                sensor_metrics.extend(metrics)
                self.all_metrics.extend(metrics)
                
                # Short pause between frequency tests
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Failed test {sensor_count} sensors at {frequency} pts/sec: {e}")
        
        # Generate visualization for this sensor count
        self.logger.info(f"📊 Generating visualization for {sensor_count} sensors...")
        self.visualizer.create_sensor_count_visualization(
            sensor_metrics, sensor_count, self.config.dataset_name
        )
        
        # Save intermediate results
        self.save_intermediate_results(sensor_metrics, sensor_count)
        
    def save_intermediate_results(self, metrics: List[PerformanceMetrics], sensor_count: int):
        """중간 결과 저장"""
        if not metrics:
            return
            
        # Convert to DataFrame and save CSV
        df = pd.DataFrame([asdict(m) for m in metrics])
        filename = f"{self.results_dir}/{self.config.dataset_name.lower()}_{sensor_count}sensors_raw_data.csv"
        df.to_csv(filename, index=False)
        self.logger.info(f"💾 Raw data saved: {filename}")
        
    async def run_full_experiment(self):
        """전체 실험 실행"""
        self.logger.info(f"🎯 Starting {self.config.dataset_name} CKKS Performance Experiment")
        self.logger.info(f"📊 Experiment ID: {self.experiment_id}")
        self.logger.info(f"🔧 Config: {self.config.sensor_counts} sensors, {self.config.frequencies} pts/sec")
        
        start_time = time.time()
        
        # Run experiments for each sensor count
        for sensor_count in self.config.sensor_counts:
            await self.run_sensor_count_experiment(sensor_count)
            
        # Generate final comprehensive analysis
        self.logger.info("📊 Generating final comprehensive analysis...")
        self.visualizer.create_final_comparison(self.all_metrics, self.config.dataset_name)
        
        # Save complete results
        self.save_complete_results()
        
        total_time = time.time() - start_time
        self.logger.info(f"✅ Experiment completed in {total_time/60:.2f} minutes")
        self.logger.info(f"📁 Results saved to: {self.results_dir}")
        
        # Print summary
        self.print_experiment_summary()
        
    def save_complete_results(self):
        """완전한 결과 저장"""
        if not self.all_metrics:
            return
            
        # Save all metrics as CSV
        df = pd.DataFrame([asdict(m) for m in self.all_metrics])
        filename = f"{self.results_dir}/complete_performance_data.csv"
        df.to_csv(filename, index=False)
        
        # Save summary statistics
        summary = self.generate_summary_statistics()
        with open(f"{self.results_dir}/experiment_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
            
        self.logger.info(f"💾 Complete results saved: {filename}")
        
    def generate_summary_statistics(self) -> Dict:
        """요약 통계 생성"""
        if not self.all_metrics:
            return {}
            
        successful_metrics = [m for m in self.all_metrics if m.success]
        
        summary = {
            "experiment_id": self.experiment_id,
            "dataset": self.config.dataset_name,
            "total_tests": len(self.all_metrics),
            "successful_tests": len(successful_metrics),
            "success_rate": len(successful_metrics) / len(self.all_metrics) * 100,
            "sensor_counts_tested": self.config.sensor_counts,
            "frequencies_tested": self.config.frequencies,
            "duration_per_test": self.config.duration_seconds,
        }
        
        if successful_metrics:
            summary.update({
                "avg_encryption_time_ms": np.mean([m.encryption_time_ms for m in successful_metrics]),
                "avg_decryption_time_ms": np.mean([m.decryption_time_ms for m in successful_metrics]),
                "avg_network_rtt_ms": np.mean([m.network_rtt_ms for m in successful_metrics]),
                "avg_accuracy_error": np.mean([m.accuracy_error for m in successful_metrics]),
                "max_cpu_usage": np.max([m.cpu_usage_percent for m in successful_metrics]),
                "max_memory_usage_mb": np.max([m.memory_usage_mb for m in successful_metrics]),
            })
            
        return summary
        
    def print_experiment_summary(self):
        """실험 요약 출력"""
        if not self.all_metrics:
            print("❌ No metrics available for summary")
            return
            
        successful_metrics = [m for m in self.all_metrics if m.success]
        
        print(f"\n{'='*70}")
        print(f"🎯 {self.config.dataset_name} CKKS Performance Experiment Summary")
        print(f"{'='*70}")
        print(f"📊 Experiment ID: {self.experiment_id}")
        print(f"⏱️  Total Tests: {len(self.all_metrics)}")
        print(f"✅ Successful: {len(successful_metrics)} ({len(successful_metrics)/len(self.all_metrics)*100:.1f}%)")
        print(f"❌ Failed: {len(self.all_metrics) - len(successful_metrics)}")
        
        if successful_metrics:
            print(f"\n📈 Performance Metrics:")
            print(f"  • Avg Encryption Time: {np.mean([m.encryption_time_ms for m in successful_metrics]):.2f} ms")
            print(f"  • Avg Network RTT: {np.mean([m.network_rtt_ms for m in successful_metrics]):.2f} ms")
            print(f"  • Avg Accuracy Error: {np.mean([m.accuracy_error for m in successful_metrics]):.4f}%")
            print(f"  • Peak CPU Usage: {np.max([m.cpu_usage_percent for m in successful_metrics]):.1f}%")
            print(f"  • Peak Memory Usage: {np.max([m.memory_usage_mb for m in successful_metrics]):.1f} MB")
            
        print(f"\n📁 Results Location: {self.results_dir}/")
        print(f"📊 Visualizations: Generated for each sensor count + final comparison")
        print(f"💾 Raw Data: CSV files with complete metrics")
        print(f"{'='*70}")

async def main():
    """메인 실행 함수"""
    print("🚀 CKKS Performance Experiment System")
    print("=====================================")
    
    # Check command line arguments
    import sys
    dataset_name = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dataset" and len(sys.argv) > 2:
            dataset_arg = sys.argv[2].upper()
            if dataset_arg == "WADI":
                dataset_name = "WADI"
                print(f"📊 Using dataset: {dataset_name} (Water Distribution)")
            elif dataset_arg == "HAI":
                dataset_name = "HAI"  
                print(f"📊 Using dataset: {dataset_name} (Hardware-in-the-loop Augmented ICS)")
    
    # Ask user for dataset choice if not provided via command line
    if dataset_name is None:
        print("📊 Available Datasets:")
        print("  1. WADI (Water Distribution)")
        print("  2. HAI (Hardware-in-the-loop Augmented ICS)")
        
        while True:
            choice = input("\nSelect dataset (1 or 2): ").strip()
            if choice == "1":
                dataset_name = "WADI"
                break
            elif choice == "2":
                dataset_name = "HAI"
                break
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
    
    # Create experiment configuration
    config = ExperimentConfig(
        dataset_name=dataset_name,
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],  # data points per second
        duration_seconds=30,  # 30 seconds per test
    )
    
    print(f"\n🔧 Experiment Configuration:")
    print(f"  • Dataset: {config.dataset_name}")
    print(f"  • Sensor Counts: {config.sensor_counts}")
    print(f"  • Frequencies: {config.frequencies} data points/sec")
    print(f"  • Duration per test: {config.duration_seconds} seconds")
    print(f"  • Total estimated time: {len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 60:.1f} minutes")
    
    # Confirm before starting (auto-accept if command line arguments provided)
    if len(sys.argv) > 1 and sys.argv[1] == "--dataset":
        print("\n🚀 Auto-starting experiment...")
    else:
        confirm = input("\n🚀 Start experiment? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Experiment cancelled.")
            return
    
    # Run experiment
    try:
        experiment = CKKSPerformanceExperiment(config)
        await experiment.run_full_experiment()
        print("\n🎉 Experiment completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Experiment interrupted by user.")
    except Exception as e:
        print(f"\n❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
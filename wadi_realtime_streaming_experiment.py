#!/usr/bin/env python3
"""
WADI Real-time Streaming CKKS Experiment
실제 주파수로 스트리밍 전송하는 실시간 부하 테스트

Author: ICS Security Research Team
Date: 2025-01-28
"""

import asyncio
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import threading

# Local imports
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest
from performance_monitor import PerformanceMonitor

class WADIRealtimeStreamingExperiment:
    """WADI 실시간 스트리밍 실험"""
    
    def __init__(self):
        self.setup_logging()
        
        # 실험 메타데이터
        self.experiment_start_time = datetime.now()
        self.experiment_id = f"wadi_realtime_streaming_{self.experiment_start_time.strftime('%Y%m%d')}"
        
        # WADI 데이터 경로
        self.wadi_data_path = "data/wadi/WADI_14days_new.csv"
        
        # 테스트 센서 정의
        self.test_sensors = [
            {"sensor_id": "1_AIT_001_PV", "type": "analytical", "criticality": "critical"},
            {"sensor_id": "1_AIT_002_PV", "type": "analytical", "criticality": "critical"},
            {"sensor_id": "2_FIC_101_PV", "type": "flow_control", "criticality": "critical"},
            {"sensor_id": "2_PIT_001_PV", "type": "pressure", "criticality": "critical"},
            {"sensor_id": "2_LT_001_PV", "type": "level", "criticality": "important"},
            {"sensor_id": "1_LT_001_PV", "type": "level", "criticality": "important"},
            {"sensor_id": "1_P_001_STATUS", "type": "pump", "criticality": "normal"},
            {"sensor_id": "1_P_002_STATUS", "type": "pump", "criticality": "normal"},
            {"sensor_id": "1_MV_001_STATUS", "type": "valve", "criticality": "important"},
            {"sensor_id": "1_MV_002_STATUS", "type": "valve", "criticality": "important"}
        ]
        
        # 실시간 스트리밍 실험 매트릭스
        self.experiment_matrix = {
            "single_realtime": {
                "sensor_count": 1,
                "frequencies": [1, 2],     # Hz - 실제 주파수
                "duration_seconds": 10,    # 10초간 실행
                "selected_sensors": self.test_sensors[:1],
                "purpose": "단일 센서 실시간 스트리밍"
            },
            "small_group_realtime": {
                "sensor_count": 2,
                "frequencies": [1],        # Hz - 실제 주파수
                "duration_seconds": 10,    # 10초간 실행
                "selected_sensors": self.test_sensors[:2],
                "purpose": "소규모 그룹 실시간 스트리밍"
            }
        }
        
        # 컴포넌트 초기화
        self.ckks_manager = ConcurrentCKKSManager()
        self.performance_monitor = PerformanceMonitor()
        
        # 결과 저장 경로
        self.results_dir = f"experiment_results/{self.experiment_id}"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 스트리밍 상태 추적
        self.streaming_stats = {}
        self.active_streams = {}
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/wadi_realtime_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_wadi_data(self, sensor_ids: List[str]) -> Dict[str, np.ndarray]:
        """WADI 데이터 로드"""
        try:
            # 더 많은 데이터 로드 (스트리밍용)
            df = pd.read_csv(self.wadi_data_path, nrows=2000)
            
            sensor_data = {}
            for sensor_id in sensor_ids:
                if sensor_id in df.columns:
                    data = df[sensor_id].values
                    data = np.nan_to_num(data, nan=np.nanmean(data))
                    sensor_data[sensor_id] = data
                else:
                    self.logger.warning(f"Sensor {sensor_id} not found, using simulated data")
                    # 더 현실적인 센서 데이터 시뮬레이션
                    base_value = np.random.uniform(10, 100)
                    noise = np.random.normal(0, base_value * 0.05, 2000)
                    trend = np.sin(np.linspace(0, 4*np.pi, 2000)) * base_value * 0.1
                    sensor_data[sensor_id] = base_value + noise + trend
            
            return sensor_data
            
        except Exception as e:
            self.logger.error(f"Failed to load WADI data: {e}")
            # 폴백: 고품질 시뮬레이션 데이터
            sensor_data = {}
            for sensor_id in sensor_ids:
                base_value = np.random.uniform(20, 80)
                noise = np.random.normal(0, base_value * 0.03, 2000)
                trend = np.sin(np.linspace(0, 6*np.pi, 2000)) * base_value * 0.05
                sensor_data[sensor_id] = base_value + noise + trend
            return sensor_data
    
    async def sensor_stream_worker(self, sensor: Dict, frequency: int, duration: int, 
                                 sensor_data: np.ndarray, stream_id: str) -> List[Dict]:
        """개별 센서 스트리밍 워커"""
        stream_results = []
        interval = 1.0 / frequency  # 전송 간격 (초)
        
        self.logger.info(f"Starting stream for {sensor['sensor_id']} at {frequency}Hz (interval: {interval:.3f}s)")
        
        start_time = time.time()
        data_index = 0
        request_count = 0
        
        while (time.time() - start_time) < duration and data_index < len(sensor_data):
            try:
                # 현재 시간 기록
                send_time = time.time()
                
                # 센서 값 가져오기
                sensor_value = float(sensor_data[data_index])
                
                # CKKS 요청 생성
                request = CKKSRequest(
                    request_id=f"{stream_id}_{sensor['sensor_id']}_{request_count}",
                    sensor_id=sensor["sensor_id"],
                    value=sensor_value,
                    timestamp=send_time
                )
                
                # 개별 전송 (실시간)
                response_start = time.time()
                responses = await self.ckks_manager.send_batch_requests_async([request])
                response_end = time.time()
                
                # 결과 기록
                if responses and len(responses) > 0:
                    response = responses[0]
                    result = {
                        "timestamp": send_time,
                        "sensor_id": sensor["sensor_id"],
                        "request_id": request.request_id,
                        "original_value": sensor_value,
                        "success": response.success,
                        "processing_time_ms": (response_end - response_start) * 1000,
                        "response_time_ms": (response_end - send_time) * 1000,
                        "expected_interval_ms": interval * 1000,
                        "data_index": data_index
                    }
                    stream_results.append(result)
                
                # 다음 전송을 위한 대기
                next_send_time = start_time + (request_count + 1) * interval
                current_time = time.time()
                
                if next_send_time > current_time:
                    await asyncio.sleep(next_send_time - current_time)
                else:
                    # 지연 발생 - 로그 기록
                    delay = current_time - next_send_time
                    if delay > interval * 0.1:  # 10% 이상 지연시에만 로그
                        self.logger.warning(f"{sensor['sensor_id']}: Delayed by {delay*1000:.1f}ms")
                
                request_count += 1
                data_index += 1
                
            except Exception as e:
                self.logger.error(f"Stream error for {sensor['sensor_id']}: {e}")
                break
        
        self.logger.info(f"Completed stream for {sensor['sensor_id']}: {len(stream_results)} requests in {time.time() - start_time:.1f}s")
        return stream_results
    
    async def run_realtime_streaming_test(self, condition: str, sensors: List[Dict], 
                                        frequency: int, duration: int) -> Dict:
        """실시간 스트리밍 테스트"""
        self.logger.info(f"Starting realtime streaming: {condition} with {len(sensors)} sensors at {frequency}Hz for {duration}s")
        
        # 성능 모니터링 시작
        initial_metrics = self.performance_monitor.get_current_system_status()
        test_start_time = time.time()
        
        # 센서 데이터 로드
        sensor_ids = [s["sensor_id"] for s in sensors]
        sensor_data_dict = self.load_wadi_data(sensor_ids)
        
        # 스트림 ID 생성
        stream_id = f"{condition}_{frequency}Hz_{int(test_start_time)}"
        
        # 각 센서별로 병렬 스트리밍 시작
        streaming_tasks = []
        for sensor in sensors:
            sensor_data = sensor_data_dict[sensor["sensor_id"]]
            task = self.sensor_stream_worker(
                sensor, frequency, duration, sensor_data, stream_id
            )
            streaming_tasks.append(task)
        
        # 모든 스트리밍 완료 대기
        self.logger.info(f"Waiting for {len(streaming_tasks)} streams to complete...")
        stream_results_list = await asyncio.gather(*streaming_tasks, return_exceptions=True)
        
        # 결과 집계
        all_results = []
        for results in stream_results_list:
            if isinstance(results, list):
                all_results.extend(results)
            else:
                self.logger.error(f"Stream failed: {results}")
        
        # 성능 메트릭 수집
        final_metrics = self.performance_monitor.get_current_system_status()
        test_end_time = time.time()
        total_duration = test_end_time - test_start_time
        
        # 통계 계산
        successful_requests = [r for r in all_results if r["success"]]
        failed_requests = [r for r in all_results if not r["success"]]
        
        # 타이밍 분석
        if successful_requests:
            processing_times = [r["processing_time_ms"] for r in successful_requests]
            response_times = [r["response_time_ms"] for r in successful_requests]
            
            # 주파수 준수율 계산
            expected_interval = 1000 / frequency  # ms
            actual_intervals = []
            for i in range(1, len(all_results)):
                if all_results[i]["sensor_id"] == all_results[i-1]["sensor_id"]:
                    interval = (all_results[i]["timestamp"] - all_results[i-1]["timestamp"]) * 1000
                    actual_intervals.append(interval)
            
            frequency_compliance = 0
            if actual_intervals:
                compliant_intervals = [i for i in actual_intervals 
                                     if abs(i - expected_interval) <= expected_interval * 0.1]
                frequency_compliance = len(compliant_intervals) / len(actual_intervals) * 100
        else:
            processing_times = response_times = actual_intervals = [0]
            frequency_compliance = 0
        
        # 실시간 성능 지표
        expected_total_requests = len(sensors) * frequency * duration
        actual_total_requests = len(all_results)
        throughput_compliance = (actual_total_requests / expected_total_requests * 100) if expected_total_requests > 0 else 0
        
        result = {
            "condition": condition,
            "frequency_hz": frequency,
            "duration_seconds": duration,
            "sensor_count": len(sensors),
            "expected_requests": expected_total_requests,
            "actual_requests": actual_total_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(all_results) * 100 if all_results else 0,
            "throughput_compliance": throughput_compliance,
            "frequency_compliance": frequency_compliance,
            "timing_metrics": {
                "total_duration_s": total_duration,
                "avg_processing_time_ms": np.mean(processing_times),
                "max_processing_time_ms": np.max(processing_times),
                "min_processing_time_ms": np.min(processing_times),
                "avg_response_time_ms": np.mean(response_times),
                "max_response_time_ms": np.max(response_times),
                "avg_actual_interval_ms": np.mean(actual_intervals) if actual_intervals else 0,
                "expected_interval_ms": expected_interval
            },
            "performance_metrics": {
                "cpu_usage_before": initial_metrics.get("cpu_percent", 0),
                "cpu_usage_after": final_metrics.get("cpu_percent", 0),
                "memory_usage_before": initial_metrics.get("memory_percent", 0),
                "memory_usage_after": final_metrics.get("memory_percent", 0)
            },
            "realtime_metrics": {
                "actual_rps": len(successful_requests) / total_duration if total_duration > 0 else 0,
                "expected_rps": len(sensors) * frequency,
                "load_factor": (len(successful_requests) / total_duration) / (len(sensors) * frequency) if total_duration > 0 else 0,
                "max_concurrent_load": len(sensors) * frequency
            },
            "sensors_used": [s["sensor_id"] for s in sensors],
            "detailed_results": all_results  # 상세 스트리밍 데이터
        }
        
        self.logger.info(f"Completed {condition}: {result['success_rate']:.1f}% success, "
                        f"Throughput: {result['throughput_compliance']:.1f}%, "
                        f"Frequency compliance: {result['frequency_compliance']:.1f}%")
        
        return result
    
    async def run_condition_tests(self, condition_name: str, config: Dict) -> List[Dict]:
        """조건별 테스트 실행"""
        results = []
        
        for frequency in config["frequencies"]:
            try:
                result = await self.run_realtime_streaming_test(
                    condition_name,
                    config["selected_sensors"],
                    frequency,
                    config["duration_seconds"]
                )
                results.append(result)
                
                # 테스트 간 대기 (시스템 안정화)
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Test failed for {condition_name} at {frequency}Hz: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return results
    
    async def run_full_experiment(self) -> Dict:
        """전체 실시간 스트리밍 실험 실행"""
        self.logger.info(f"Starting WADI Realtime Streaming Experiment: {self.experiment_id}")
        
        all_results = []
        experiment_summary = {
            "experiment_id": self.experiment_id,
            "start_time": self.experiment_start_time.isoformat(),
            "dataset": "WADI",
            "experiment_type": "Realtime Streaming with Load Testing",
            "conditions": []
        }
        
        # 각 조건별 실험 실행
        for condition_name, config in self.experiment_matrix.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Starting {condition_name}: {config['purpose']}")
            self.logger.info(f"Sensors: {config['sensor_count']}, Frequencies: {config['frequencies']}, Duration: {config['duration_seconds']}s")
            
            condition_results = await self.run_condition_tests(condition_name, config)
            all_results.extend(condition_results)
            
            # 조건별 요약
            if condition_results:
                condition_summary = {
                    "name": condition_name,
                    "sensor_count": config["sensor_count"],
                    "test_count": len(condition_results),
                    "avg_success_rate": np.mean([r["success_rate"] for r in condition_results]),
                    "avg_throughput_compliance": np.mean([r["throughput_compliance"] for r in condition_results]),
                    "avg_frequency_compliance": np.mean([r["frequency_compliance"] for r in condition_results]),
                    "total_requests": sum(r["actual_requests"] for r in condition_results),
                    "total_expected_requests": sum(r["expected_requests"] for r in condition_results)
                }
                experiment_summary["conditions"].append(condition_summary)
        
        # 전체 실험 요약
        experiment_summary["end_time"] = datetime.now().isoformat()
        experiment_summary["total_duration_minutes"] = (datetime.now() - self.experiment_start_time).total_seconds() / 60
        experiment_summary["total_tests"] = len(all_results)
        
        if all_results:
            experiment_summary["overall_success_rate"] = np.mean([r["success_rate"] for r in all_results])
            experiment_summary["overall_throughput_compliance"] = np.mean([r["throughput_compliance"] for r in all_results])
            experiment_summary["overall_frequency_compliance"] = np.mean([r["frequency_compliance"] for r in all_results])
            experiment_summary["total_streaming_requests"] = sum(r["actual_requests"] for r in all_results)
            experiment_summary["total_expected_requests"] = sum(r["expected_requests"] for r in all_results)
        
        # 결과 저장
        self.save_results(all_results, experiment_summary)
        
        return {
            "summary": experiment_summary,
            "detailed_results": all_results
        }
    
    def save_results(self, results: List[Dict], summary: Dict):
        """결과 저장"""
        # 상세 결과 JSON
        with open(f"{self.results_dir}/realtime_streaming_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # 실험 요약 JSON
        with open(f"{self.results_dir}/streaming_experiment_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # CSV 변환 (메인 결과)
        csv_data = []
        for result in results:
            timing = result["timing_metrics"]
            realtime = result["realtime_metrics"]
            csv_row = {
                "condition": result["condition"],
                "frequency_hz": result["frequency_hz"],
                "duration_seconds": result["duration_seconds"],
                "sensor_count": result["sensor_count"],
                "expected_requests": result["expected_requests"],
                "actual_requests": result["actual_requests"],
                "success_rate": result["success_rate"],
                "throughput_compliance": result["throughput_compliance"],
                "frequency_compliance": result["frequency_compliance"],
                "avg_processing_time_ms": timing["avg_processing_time_ms"],
                "max_processing_time_ms": timing["max_processing_time_ms"],
                "avg_response_time_ms": timing["avg_response_time_ms"],
                "actual_rps": realtime["actual_rps"],
                "expected_rps": realtime["expected_rps"],
                "load_factor": realtime["load_factor"]
            }
            csv_data.append(csv_row)
        
        df = pd.DataFrame(csv_data)
        df.to_csv(f"{self.results_dir}/realtime_streaming_results.csv", index=False)
        
        # 상세 스트리밍 데이터 CSV (모든 개별 요청)
        all_detailed_data = []
        for result in results:
            for detail in result.get("detailed_results", []):
                detail_row = detail.copy()
                detail_row["condition"] = result["condition"]
                detail_row["frequency_hz"] = result["frequency_hz"]
                all_detailed_data.append(detail_row)
        
        if all_detailed_data:
            detailed_df = pd.DataFrame(all_detailed_data)
            detailed_df.to_csv(f"{self.results_dir}/streaming_detailed_requests.csv", index=False)
        
        self.logger.info(f"Results saved to {self.results_dir}/")
    
    def print_summary(self, summary: Dict):
        """요약 출력"""
        print("\n" + "="*70)
        print("🎯 WADI Realtime Streaming Experiment Summary")
        print("="*70)
        print(f"📊 Experiment ID: {summary['experiment_id']}")
        print(f"⏱️  Duration: {summary['total_duration_minutes']:.2f} minutes")
        print(f"📈 Total Tests: {summary['total_tests']}")
        
        if 'overall_success_rate' in summary:
            print(f"✅ Overall Success Rate: {summary['overall_success_rate']:.1f}%")
            print(f"🔐 Total Streaming Requests: {summary['total_streaming_requests']:,}")
            print(f"📋 Expected Requests: {summary['total_expected_requests']:,}")
            print(f"📊 Throughput Compliance: {summary['overall_throughput_compliance']:.1f}%")
            print(f"⏰ Frequency Compliance: {summary['overall_frequency_compliance']:.1f}%")
        
        print("\n📋 Condition Results:")
        for condition in summary['conditions']:
            print(f"  • {condition['name']}:")
            print(f"    - Success: {condition['avg_success_rate']:.1f}%")
            print(f"    - Throughput: {condition['avg_throughput_compliance']:.1f}%") 
            print(f"    - Frequency: {condition['avg_frequency_compliance']:.1f}%")
            print(f"    - Requests: {condition['total_requests']:,}/{condition['total_expected_requests']:,}")
        print("="*70)

async def main():
    """메인 실행 함수"""
    experiment = WADIRealtimeStreamingExperiment()
    
    try:
        # 전체 실험 실행
        results = await experiment.run_full_experiment()
        
        # 요약 출력
        experiment.print_summary(results["summary"])
        
        print(f"\n✅ Realtime streaming experiment completed successfully!")
        print(f"📁 Results saved to: {experiment.results_dir}/")
        
    except Exception as e:
        print(f"\n❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
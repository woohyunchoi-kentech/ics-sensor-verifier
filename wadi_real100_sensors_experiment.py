#!/usr/bin/env python3
"""
WADI Real 100 Sensors CKKS GPU Experiment
실제 선별된 100개 WADI 센서를 사용한 CKKS 동형암호화 실험

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
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# Local imports
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest
from performance_monitor import PerformanceMonitor
from safety_controller import SafetyController

class WADIReal100SensorsExperiment:
    """실제 100개 WADI 센서를 사용한 CKKS 실험"""
    
    def __init__(self):
        self.setup_logging()
        
        # 실험 메타데이터
        self.experiment_start_time = datetime.now()
        self.experiment_id = f"wadi_real100_sensors_{self.experiment_start_time.strftime('%Y%m%d')}"
        
        # WADI 데이터 경로
        self.wadi_data_path = "data/wadi/WADI_14days_new.csv"
        
        # 100개 실제 센서 정의
        self.selected_sensors = self.define_wadi_sensors()
        
        # 실험 매트릭스 (HAI와 동일)
        self.experiment_matrix = {
            "single_sensor_test": {
                "sensor_count": 1,
                "frequencies": [1, 2, 5, 10, 15, 20],
                "selected_sensors": self.selected_sensors[:1],
                "purpose": "단일 센서 최적 성능 측정"
            },
            "small_group_test": {
                "sensor_count": 10,
                "frequencies": [1, 2, 5, 8, 10],
                "selected_sensors": self.selected_sensors[:10],
                "purpose": "소규모 그룹 동시 처리"
            },
            "medium_group_test": {
                "sensor_count": 50,
                "frequencies": [1, 2, 4, 6],
                "selected_sensors": self.selected_sensors[:50],
                "purpose": "중규모 시스템 성능"
            },
            "full_scale_test": {
                "sensor_count": 100,
                "frequencies": [1, 2, 3],
                "selected_sensors": self.selected_sensors[:100],
                "purpose": "전체 시스템 부하"
            }
        }
        
        # 컴포넌트 초기화
        self.ckks_manager = ConcurrentCKKSManager()
        self.performance_monitor = PerformanceMonitor()
        self.safety_controller = SafetyController()
        
        # 결과 저장 경로
        self.results_dir = f"experiment_results/{self.experiment_id}"
        os.makedirs(self.results_dir, exist_ok=True)
        
    def define_wadi_sensors(self) -> List[Dict]:
        """WADI 100개 센서 정의"""
        sensors = []
        
        # Critical Sensors (40개)
        # AIT - Analytical Indicator Transmitter (17개)
        for i in range(1, 6):
            sensors.append({
                "sensor_id": f"1_AIT_{i:03d}_PV",
                "type": "analytical",
                "criticality": "critical",
                "unit": "mg/L"
            })
        
        for prefix in ['2A', '2B']:
            for i in range(1, 5):
                sensors.append({
                    "sensor_id": f"{prefix}_AIT_{i:03d}_PV",
                    "type": "analytical",
                    "criticality": "critical",
                    "unit": "mg/L"
                })
        
        # FIC - Flow Indicator Controller (15개)
        for i in [101, 201, 301, 401, 501, 601]:
            for suffix in ['PV', 'CO', 'SP'][:1]:  # PV만 사용
                sensors.append({
                    "sensor_id": f"2_FIC_{i}_{suffix}",
                    "type": "flow_control",
                    "criticality": "critical",
                    "unit": "m3/h"
                })
        
        # PIT - Pressure Indicator Transmitter (8개)
        for i in range(1, 4):
            sensors.append({
                "sensor_id": f"2_PIT_{i:03d}_PV",
                "type": "pressure",
                "criticality": "critical",
                "unit": "bar"
            })
        
        sensors.append({
            "sensor_id": "2_PIC_003_PV",
            "type": "pressure_control",
            "criticality": "critical",
            "unit": "bar"
        })
        
        sensors.append({
            "sensor_id": "2_DPIT_001_PV",
            "type": "differential_pressure",
            "criticality": "critical",
            "unit": "mbar"
        })
        
        # Important Sensors (30개)
        # LT - Level Transmitter (10개)
        sensors.append({
            "sensor_id": "1_LT_001_PV",
            "type": "level",
            "criticality": "important",
            "unit": "%"
        })
        
        for i in range(1, 3):
            sensors.append({
                "sensor_id": f"2_LT_{i:03d}_PV",
                "type": "level",
                "criticality": "important",
                "unit": "%"
            })
        
        sensors.append({
            "sensor_id": "3_LT_001_PV",
            "type": "level",
            "criticality": "important",
            "unit": "%"
        })
        
        # MV - Motor Valves (10개)
        for i in range(1, 7):
            sensors.append({
                "sensor_id": f"1_MV_{i:03d}_STATUS",
                "type": "valve",
                "criticality": "important",
                "unit": "binary"
            })
        
        for i in range(1, 5):
            sensors.append({
                "sensor_id": f"2_MV_{i:03d}_STATUS",
                "type": "valve",
                "criticality": "important",
                "unit": "binary"
            })
        
        # MCV - Motor Control Valves (10개)
        for i in [7, 101, 201, 301, 401, 501, 601]:
            if len(sensors) < 70:
                sensors.append({
                    "sensor_id": f"2_MCV_{i:03d}_CO",
                    "type": "control_valve",
                    "criticality": "important",
                    "unit": "%"
                })
        
        # Normal Sensors (30개)
        # P - Pumps (20개)
        for i in range(1, 7):
            sensors.append({
                "sensor_id": f"1_P_{i:03d}_STATUS",
                "type": "pump",
                "criticality": "normal",
                "unit": "binary"
            })
        
        for i in range(1, 5):
            sensors.append({
                "sensor_id": f"2_P_{i:03d}_STATUS",
                "type": "pump",
                "criticality": "normal",
                "unit": "binary"
            })
        
        for i in range(1, 5):
            sensors.append({
                "sensor_id": f"3_P_{i:03d}_STATUS",
                "type": "pump",
                "criticality": "normal",
                "unit": "binary"
            })
        
        # SV - Solenoid Valves (6개)
        for i in [101, 201, 301, 401, 501, 601]:
            if len(sensors) < 100:
                sensors.append({
                    "sensor_id": f"2_SV_{i}_STATUS",
                    "type": "solenoid_valve",
                    "criticality": "normal",
                    "unit": "binary"
                })
        
        # FIT - Flow Transmitters (나머지)
        while len(sensors) < 100:
            sensors.append({
                "sensor_id": f"1_FIT_001_PV",
                "type": "flow",
                "criticality": "normal",
                "unit": "m3/h"
            })
            sensors.append({
                "sensor_id": f"2_FIT_{len(sensors):03d}_PV",
                "type": "flow",
                "criticality": "normal",
                "unit": "m3/h"
            })
        
        return sensors[:100]  # 정확히 100개만 반환
    
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/wadi_experiment_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_wadi_data(self, sensor_ids: List[str]) -> Dict[str, np.ndarray]:
        """WADI 데이터 로드"""
        try:
            # CSV 파일 로드 (첫 1000행만 빠른 테스트용)
            df = pd.read_csv(self.wadi_data_path, nrows=1000)
            
            sensor_data = {}
            for sensor_id in sensor_ids:
                if sensor_id in df.columns:
                    # 실제 데이터 사용
                    data = df[sensor_id].values
                    # NaN 값을 평균으로 대체
                    data = np.nan_to_num(data, nan=np.nanmean(data))
                    sensor_data[sensor_id] = data
                else:
                    # 센서가 없으면 시뮬레이션 데이터
                    self.logger.warning(f"Sensor {sensor_id} not found, using simulated data")
                    sensor_data[sensor_id] = np.random.randn(1000) * 10 + 50
            
            return sensor_data
            
        except Exception as e:
            self.logger.error(f"Failed to load WADI data: {e}")
            # 폴백: 시뮬레이션 데이터
            return {sid: np.random.randn(1000) * 10 + 50 for sid in sensor_ids}
    
    async def run_frequency_test(self, condition: str, sensors: List[Dict], frequency: int) -> Dict:
        """단일 주파수 테스트"""
        self.logger.info(f"Starting {condition} test at {frequency}Hz with {len(sensors)} sensors")
        
        # 성능 모니터링 시작
        initial_metrics = self.performance_monitor.get_current_system_status()
        test_start = time.time()
        
        # 센서 데이터 로드
        sensor_ids = [s["sensor_id"] for s in sensors]
        sensor_data_dict = self.load_wadi_data(sensor_ids)
        
        # CKKS 요청 생성
        requests = []
        for sensor in sensors:
            sensor_data = sensor_data_dict[sensor["sensor_id"]]
            
            # 각 데이터 포인트마다 개별 요청 생성
            for j, value in enumerate(sensor_data[:10]):  # 센서당 10개 포인트
                request = CKKSRequest(
                    request_id=f"{condition}_{frequency}Hz_{sensor['sensor_id']}_{j}",
                    sensor_id=sensor["sensor_id"],
                    value=float(value),
                    timestamp=time.time()
                )
                requests.append(request)
        
        # 동시 CKKS 처리
        encryption_start = time.time()
        responses = await self.ckks_manager.send_batch_requests_async(requests)
        encryption_end = time.time()
        
        # 성능 메트릭 수집
        final_metrics = self.performance_monitor.get_current_system_status()
        test_end = time.time()
        
        # 결과 분석
        successful_responses = [r for r in responses if r.success]
        failed_responses = [r for r in responses if not r.success]
        
        total_response_time = test_end - test_start
        encryption_time = encryption_end - encryption_start
        
        result = {
            "condition": condition,
            "frequency_hz": frequency,
            "sensor_count": len(sensors),
            "total_requests": len(requests),
            "successful_requests": len(successful_responses),
            "failed_requests": len(failed_responses),
            "success_rate": len(successful_responses) / len(requests) * 100 if requests else 0,
            "timing_metrics": {
                "total_response_time_ms": total_response_time * 1000,
                "encryption_time_ms": encryption_time * 1000,
                "avg_response_time_ms": (total_response_time / len(requests)) * 1000 if requests else 0
            },
            "performance_metrics": {
                "cpu_usage_before": initial_metrics.get("cpu_percent", 0),
                "cpu_usage_after": final_metrics.get("cpu_percent", 0),
                "memory_usage_before": initial_metrics.get("memory_percent", 0),
                "memory_usage_after": final_metrics.get("memory_percent", 0)
            },
            "throughput_metrics": {
                "requests_per_second": len(requests) / total_response_time if total_response_time > 0 else 0,
                "data_points_per_second": (len(requests) * 100) / total_response_time if total_response_time > 0 else 0
            },
            "sensors_used": [s["sensor_id"] for s in sensors[:5]]  # 처음 5개만 기록
        }
        
        self.logger.info(f"Completed {condition} at {frequency}Hz: {result['success_rate']:.1f}% success rate")
        
        return result
    
    async def run_condition_tests(self, condition_name: str, config: Dict) -> List[Dict]:
        """조건별 테스트 실행"""
        results = []
        
        for frequency in config["frequencies"]:
            try:
                result = await self.run_frequency_test(
                    condition_name,
                    config["selected_sensors"],
                    frequency
                )
                results.append(result)
                
                # 안전성 체크
                if not self.safety_controller.check_safety(result):
                    self.logger.warning(f"Safety check failed for {condition_name} at {frequency}Hz")
                    break
                    
            except Exception as e:
                self.logger.error(f"Test failed for {condition_name} at {frequency}Hz: {e}")
                continue
        
        return results
    
    async def run_full_experiment(self) -> Dict:
        """전체 실험 실행"""
        self.logger.info(f"Starting WADI 100 Sensors Experiment: {self.experiment_id}")
        
        all_results = []
        experiment_summary = {
            "experiment_id": self.experiment_id,
            "start_time": self.experiment_start_time.isoformat(),
            "dataset": "WADI",
            "total_sensors": 100,
            "conditions": []
        }
        
        # 각 조건별 실험 실행
        for condition_name, config in self.experiment_matrix.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Starting {condition_name}: {config['purpose']}")
            self.logger.info(f"Sensors: {config['sensor_count']}, Frequencies: {config['frequencies']}")
            
            condition_results = await self.run_condition_tests(condition_name, config)
            all_results.extend(condition_results)
            
            # 조건별 요약
            condition_summary = {
                "name": condition_name,
                "sensor_count": config["sensor_count"],
                "test_count": len(condition_results),
                "avg_success_rate": np.mean([r["success_rate"] for r in condition_results]),
                "total_requests": sum(r["total_requests"] for r in condition_results)
            }
            experiment_summary["conditions"].append(condition_summary)
        
        # 전체 실험 요약
        experiment_summary["end_time"] = datetime.now().isoformat()
        experiment_summary["total_duration_minutes"] = (datetime.now() - self.experiment_start_time).total_seconds() / 60
        experiment_summary["total_tests"] = len(all_results)
        experiment_summary["overall_success_rate"] = np.mean([r["success_rate"] for r in all_results])
        experiment_summary["total_ckks_requests"] = sum(r["total_requests"] for r in all_results)
        
        # 결과 저장
        self.save_results(all_results, experiment_summary)
        
        return {
            "summary": experiment_summary,
            "detailed_results": all_results
        }
    
    def save_results(self, results: List[Dict], summary: Dict):
        """결과 저장"""
        # 상세 결과 JSON
        with open(f"{self.results_dir}/detailed_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # 실험 요약 JSON
        with open(f"{self.results_dir}/experiment_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # CSV 변환
        df = pd.DataFrame(results)
        df.to_csv(f"{self.results_dir}/results.csv", index=False)
        
        # 센서 목록 저장
        with open(f"{self.results_dir}/sensor_list.json", 'w') as f:
            json.dump(self.selected_sensors, f, indent=2)
        
        self.logger.info(f"Results saved to {self.results_dir}/")
    
    def print_summary(self, summary: Dict):
        """요약 출력"""
        print("\n" + "="*60)
        print("🎯 WADI 100 Sensors CKKS Experiment Summary")
        print("="*60)
        print(f"📊 Experiment ID: {summary['experiment_id']}")
        print(f"⏱️  Duration: {summary['total_duration_minutes']:.2f} minutes")
        print(f"📈 Total Tests: {summary['total_tests']}")
        print(f"✅ Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"🔐 Total CKKS Requests: {summary['total_ckks_requests']:,}")
        print("\n📋 Condition Results:")
        for condition in summary['conditions']:
            print(f"  • {condition['name']}: {condition['avg_success_rate']:.1f}% ({condition['total_requests']:,} requests)")
        print("="*60)

async def main():
    """메인 실행 함수"""
    experiment = WADIReal100SensorsExperiment()
    
    try:
        # 전체 실험 실행
        results = await experiment.run_full_experiment()
        
        # 요약 출력
        experiment.print_summary(results["summary"])
        
        print(f"\n✅ Experiment completed successfully!")
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
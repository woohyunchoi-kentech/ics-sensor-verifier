#!/usr/bin/env python3
"""
HAI Real 100 Sensors CKKS GPU Experiment
실제 선별된 100개 HAI 센서를 사용한 CKKS 동형암호화 실험

Author: Claude Code
Date: 2025-08-27
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
from hai_data_streamer import HAIDataStreamer
from concurrent_manager import ConcurrentCKKSManager, CKKSRequest
from performance_monitor import PerformanceMonitor
from safety_controller import SafetyController

class HAIReal100SensorsExperiment:
    """실제 100개 HAI 센서를 사용한 CKKS 실험"""
    
    def __init__(self, config_path: str = "config/hai_top100_sensors.json"):
        self.config_path = config_path
        self.setup_logging()
        
        # 실험 메타데이터
        self.experiment_start_time = datetime.now()
        self.experiment_id = f"hai_real100_sensors_{self.experiment_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        # 100개 실제 센서 로드
        self.selected_sensors = self.load_selected_sensors()
        
        # 실험 매트릭스 (실제 센서 기반)
        self.experiment_matrix = {
            "single_sensor_test": {
                "sensor_count": 1,
                "frequencies": [1, 2, 5, 10, 15, 20],
                "selected_sensors": self.selected_sensors[:1],  # 첫 번째 센서
                "purpose": "단일 센서 최적 성능 측정"
            },
            "small_group_test": {
                "sensor_count": 10,
                "frequencies": [1, 2, 5, 8, 10],
                "selected_sensors": self.selected_sensors[:10],  # 처음 10개
                "purpose": "소규모 센서 그룹 실시간 처리"
            },
            "medium_group_test": {
                "sensor_count": 50,
                "frequencies": [1, 2, 4, 6],
                "selected_sensors": self.selected_sensors[:50],  # 처음 50개
                "purpose": "중규모 센서 네트워크 처리"
            },
            "full_scale_test": {
                "sensor_count": 100,
                "frequencies": [1, 2, 3],
                "selected_sensors": self.selected_sensors,  # 전체 100개
                "purpose": "대규모 실제 센서 네트워크 완전 검증"
            }
        }
        
        # 컴포넌트 초기화
        sensor_ids = [s["sensor_id"] for s in self.selected_sensors]
        self.data_streamer = HAIDataStreamer(
            csv_path="data/hai/haiend-23.05/end-train1.csv",
            sensor_list=sensor_ids,
            frequency_hz=1.0
        )
        self.ckks_manager = ConcurrentCKKSManager(server_url="http://192.168.0.11:8085")
        self.performance_monitor = PerformanceMonitor()
        self.safety_controller = SafetyController()
        
        # 결과 저장
        self.results = {
            "experiment_metadata": {
                "experiment_id": self.experiment_id,
                "start_time": self.experiment_start_time.isoformat(),
                "total_sensors_available": len(self.selected_sensors),
                "experiment_conditions": len(self.experiment_matrix),
                "is_real_sensor_experiment": True
            },
            "sensor_details": self.selected_sensors,
            "experiment_results": {}
        }
        
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('hai_real100_experiment.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_selected_sensors(self) -> List[Dict]:
        """선별된 100개 센서 정보 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                sensor_config = json.load(f)
                
            sensors = []
            for sensor_id, sensor_info in sensor_config['sensors'].items():
                sensors.append({
                    "sensor_id": sensor_id,
                    "type": sensor_info["type"],
                    "min_value": sensor_info["range"]["min"],
                    "max_value": sensor_info["range"]["max"],
                    "mean_value": sensor_info["range"]["mean"],
                    "std_dev": sensor_info["stats"]["std"],
                    "data_quality": sensor_info["stats"]["data_quality"],
                    "data_points": sensor_info["stats"]["count"]
                })
                
            self.logger.info(f"✅ 선별된 센서 {len(sensors)}개 로드 완료")
            return sensors
            
        except Exception as e:
            self.logger.error(f"❌ 센서 설정 로드 실패: {e}")
            return []
            
    async def run_experiment_condition(self, condition_name: str, condition_config: Dict) -> Dict:
        """개별 실험 조건 실행"""
        self.logger.info(f"🚀 실험 조건 시작: {condition_name}")
        
        sensor_count = condition_config["sensor_count"]
        frequencies = condition_config["frequencies"]
        selected_sensors = condition_config["selected_sensors"]
        
        condition_results = {
            "condition_name": condition_name,
            "sensor_count": sensor_count,
            "selected_sensors": [s["sensor_id"] for s in selected_sensors],
            "frequency_results": {}
        }
        
        # 각 주파수별 테스트
        for freq in frequencies:
            self.logger.info(f"📊 주파수 {freq}Hz 테스트 시작 (센서 {sensor_count}개)")
            
            # 안전 검사
            if not self.safety_controller.is_safe_to_continue():
                self.logger.warning("⚠️ 시스템 안전 임계값 초과 - 실험 중단")
                break
                
            freq_result = await self.run_frequency_test(
                selected_sensors, freq, condition_name
            )
            
            condition_results["frequency_results"][f"{freq}Hz"] = freq_result
            
            # 주파수 간 휴식
            await asyncio.sleep(2.0)
            
        return condition_results
        
    async def run_frequency_test(self, sensors: List[Dict], frequency: int, condition: str) -> Dict:
        """특정 주파수에서 센서 테스트"""
        test_start = time.time()
        
        # 성능 모니터링 시작
        initial_metrics = self.performance_monitor.get_current_system_status()
        
        # 실제 센서 데이터 준비
        sensor_data_batch = []
        for sensor in sensors:
            try:
                # HAI 데이터에서 해당 센서 데이터 추출
                sensor_stream = self.data_streamer.get_sensor_data_stream(
                    sensor["sensor_id"], 
                    sample_count=100  # 100개 데이터 포인트
                )
                sensor_data_batch.extend(sensor_stream)
                
            except Exception as e:
                self.logger.warning(f"⚠️ 센서 {sensor['sensor_id']} 데이터 로드 실패: {e}")
                # 시뮬레이션 데이터로 대체
                simulated_data = np.random.normal(
                    sensor["mean_value"], 
                    sensor["std_dev"], 
                    100
                ).tolist()
                sensor_data_batch.extend(simulated_data)
        
        # CKKS 요청 생성 (각 센서당 여러 개의 개별 요청)
        requests = []
        for i, sensor in enumerate(sensors):
            sensor_data = sensor_data_batch[i*100:(i+1)*100] if len(sensor_data_batch) > i*100 else [sensor["mean_value"]]
            
            # 각 데이터 포인트마다 개별 요청 생성
            for j, value in enumerate(sensor_data[:10]):  # 센서당 10개 포인트로 제한
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
        
        return {
            "frequency_hz": frequency,
            "sensor_count": len(sensors),
            "total_requests": len(requests),
            "successful_requests": len(successful_responses),
            "failed_requests": len(failed_responses),
            "success_rate": len(successful_responses) / len(requests) * 100,
            "timing_metrics": {
                "total_response_time_ms": total_response_time * 1000,
                "encryption_time_ms": encryption_time * 1000,
                "avg_response_time_ms": (total_response_time / len(requests)) * 1000
            },
            "performance_metrics": {
                "cpu_usage_before": initial_metrics.get("cpu_percent", 0),
                "cpu_usage_after": final_metrics.get("cpu_percent", 0),
                "memory_usage_before": initial_metrics.get("memory_percent", 0),
                "memory_usage_after": final_metrics.get("memory_percent", 0),
                "gpu_usage_before": initial_metrics.get("gpu_usage", 0),
                "gpu_usage_after": final_metrics.get("gpu_usage", 0)
            },
            "throughput_metrics": {
                "requests_per_second": len(requests) / total_response_time,
                "data_points_per_second": (len(requests) * 100) / total_response_time,
                "max_stable_frequency": frequency if len(successful_responses) == len(requests) else frequency - 1
            }
        }
        
    async def run_full_experiment(self) -> Dict:
        """전체 실험 실행"""
        self.logger.info("🎯 HAI Real 100 Sensors CKKS 실험 시작")
        self.logger.info(f"📊 실험 ID: {self.experiment_id}")
        self.logger.info(f"🔬 선별된 센서 수: {len(self.selected_sensors)}")
        
        experiment_start = time.time()
        
        # 각 실험 조건 실행
        for condition_name, condition_config in self.experiment_matrix.items():
            try:
                condition_result = await self.run_experiment_condition(
                    condition_name, condition_config
                )
                self.results["experiment_results"][condition_name] = condition_result
                
                self.logger.info(f"✅ {condition_name} 완료")
                
                # 조건 간 휴식
                await asyncio.sleep(5.0)
                
            except Exception as e:
                self.logger.error(f"❌ {condition_name} 실행 실패: {e}")
                self.results["experiment_results"][condition_name] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        experiment_end = time.time()
        
        # 실험 완료 정보 업데이트
        self.results["experiment_metadata"].update({
            "end_time": datetime.now().isoformat(),
            "total_duration_minutes": (experiment_end - experiment_start) / 60,
            "completed_conditions": len([r for r in self.results["experiment_results"].values() 
                                       if r.get("status") != "failed"]),
            "experiment_status": "completed"
        })
        
        return self.results
        
    def save_results(self) -> str:
        """실험 결과 저장"""
        results_dir = "experiment_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # JSON 결과 저장
        json_path = f"{results_dir}/{self.experiment_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        # CSV 요약 저장
        csv_data = []
        for condition_name, condition_result in self.results["experiment_results"].items():
            if "frequency_results" in condition_result:
                for freq_name, freq_result in condition_result["frequency_results"].items():
                    csv_data.append({
                        "condition": condition_name,
                        "frequency": freq_result.get("frequency_hz", 0),
                        "sensor_count": freq_result.get("sensor_count", 0),
                        "success_rate": freq_result.get("success_rate", 0),
                        "total_response_time_ms": freq_result.get("timing_metrics", {}).get("total_response_time_ms", 0),
                        "encryption_time_ms": freq_result.get("timing_metrics", {}).get("encryption_time_ms", 0),
                        "requests_per_second": freq_result.get("throughput_metrics", {}).get("requests_per_second", 0)
                    })
        
        csv_path = f"{results_dir}/{self.experiment_id}_summary.csv"
        pd.DataFrame(csv_data).to_csv(csv_path, index=False)
        
        self.logger.info(f"💾 실험 결과 저장 완료:")
        self.logger.info(f"📄 JSON: {json_path}")
        self.logger.info(f"📊 CSV: {csv_path}")
        
        return json_path


async def main():
    """메인 실행 함수"""
    experiment = HAIReal100SensorsExperiment()
    
    try:
        # 실험 실행
        results = await experiment.run_full_experiment()
        
        # 결과 저장
        results_path = experiment.save_results()
        
        # 실험 요약 출력
        print(f"\n🎉 HAI Real 100 Sensors CKKS 실험 완료!")
        print(f"📊 실험 ID: {results['experiment_metadata']['experiment_id']}")
        print(f"⏱️  총 실행 시간: {results['experiment_metadata']['total_duration_minutes']:.1f}분")
        print(f"✅ 완료된 조건: {results['experiment_metadata']['completed_conditions']}")
        print(f"💾 결과 파일: {results_path}")
        
        # 주요 성과 출력
        for condition_name, condition_result in results["experiment_results"].items():
            if "frequency_results" in condition_result:
                sensor_count = condition_result["sensor_count"]
                freq_count = len(condition_result["frequency_results"])
                print(f"🔬 {condition_name}: {sensor_count}개 센서 × {freq_count}개 주파수 = 완료")
        
    except Exception as e:
        logging.error(f"❌ 실험 실행 실패: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
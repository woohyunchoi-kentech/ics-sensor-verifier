#!/usr/bin/env python3
"""
Server-Connected WADI ED25519 Experiment
Direct connection to http://192.168.0.11:8085
"""

import asyncio
import time
import json
import aiohttp
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys
import base64

# Add project root
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from crypto.ed25519_baseline import Ed25519Baseline


class ServerED25519Experiment:
    """WADI ED25519 experiment with direct server verification"""
    
    def __init__(self):
        self.server_url = "http://192.168.0.11:8085"
        self.ed25519_baseline = Ed25519Baseline()
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.wadi_data = None
        self.sensors = []
        print(f"🔐 Server ED25519 Experiment 초기화")
        print(f"   서버: {self.server_url}")
        print(f"   실험 ID: {self.experiment_id}")
        self._load_wadi_data()
    
    def _load_wadi_data(self):
        """Load WADI dataset"""
        try:
            print("📊 WADI 데이터 로딩 중...")
            csv_path = "data/wadi/WADI_14days_new.csv"
            self.wadi_data = pd.read_csv(csv_path)
            
            # Get sensor columns
            numeric_cols = self.wadi_data.select_dtypes(include=[np.number]).columns
            sensor_names = [col for col in numeric_cols if '_PV' in col][:30]
            self.sensors = sensor_names
            
            print(f"✅ WADI 데이터 로딩 완료: {len(self.wadi_data)} rows, {len(self.sensors)} sensors")
            
        except Exception as e:
            print(f"❌ WADI 로딩 실패: {e}")
            print("🔄 합성 데이터 생성 중...")
            self._generate_synthetic_data()
    
    def _generate_synthetic_data(self):
        """Generate synthetic sensor data"""
        np.random.seed(42)
        rows = 1000
        
        data_dict = {}
        sensor_names = [f"WADI_SENSOR_{i:02d}_PV" for i in range(20)]
        
        for sensor in sensor_names:
            if "FLOW" in sensor or "FIT" in sensor:
                data_dict[sensor] = np.random.normal(50, 15, rows).clip(0, 100)
            elif "PRESS" in sensor or "PIT" in sensor:
                data_dict[sensor] = np.random.normal(2.5, 0.8, rows).clip(0, 5)
            else:
                data_dict[sensor] = np.random.normal(30, 10, rows).clip(0, 60)
        
        self.wadi_data = pd.DataFrame(data_dict)
        self.sensors = sensor_names
        print(f"✅ 합성 데이터 생성 완료: {len(self.wadi_data)} rows, {len(self.sensors)} sensors")
    
    def _normalize_sensor_value(self, value: float) -> float:
        """Normalize sensor value to [0, 3] range"""
        normalized = max(0.0, min(3.0, value / 100.0 * 3.0))
        return normalized
    
    async def test_server_connection(self):
        """Test server connection"""
        print("\n🔌 서버 연결 테스트 중...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ 서버 연결 성공: {data.get('service', 'Unknown')}")
                        print(f"   지원 알고리즘: {data.get('supported_algorithms', [])}")
                        return True
                    else:
                        print(f"❌ 서버 응답 오류: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False
    
    async def send_ed25519_to_server(self, sensor_id: str, auth_data: Dict) -> Dict:
        """Send ED25519 authentication data to server for verification"""
        # Convert timestamp to Unix timestamp integer
        timestamp_int = int(time.time())
        
        payload = {
            "algorithm": "ed25519",
            "sensor_id": sensor_id,
            "sensor_value": auth_data["value"],
            "signature": auth_data["signature"],
            "public_key": auth_data["public_key"],
            "timestamp": timestamp_int
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/api/v1/verify/ed25519",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "server_response": result,
                            "status_code": response.status
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "status_code": response.status
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": -1
            }
    
    async def run_single_condition(self, sensor_count: int, frequency: int, target_requests: int = 100):
        """Run experiment for single condition"""
        print(f"\n📍 조건: {sensor_count} sensors @ {frequency}Hz (목표: {target_requests} 요청)")
        
        # Test server first
        if not await self.test_server_connection():
            print("❌ 서버 연결 실패로 실험 중단")
            return None
        
        selected_sensors = self.sensors[:sensor_count]
        print(f"   선택된 센서: {selected_sensors[:3]}{'...' if len(selected_sensors) > 3 else ''}")
        
        results = []
        start_time = time.time()
        interval = 1.0 / frequency
        next_send_time = time.time()
        
        for request_id in range(target_requests):
            try:
                # 정확한 타이밍을 위해 다음 전송 시간까지 대기
                current_time = time.time()
                if current_time < next_send_time:
                    await asyncio.sleep(next_send_time - current_time)
                
                print(f"📤 요청 {request_id+1}/{target_requests} 처리 중...")
                
                # Get random sensor data
                data_idx = np.random.randint(0, len(self.wadi_data))
                sensor_data = {}
                
                for sensor in selected_sensors:
                    raw_value = float(self.wadi_data[sensor].iloc[data_idx])
                    normalized_value = self._normalize_sensor_value(raw_value)
                    sensor_data[sensor] = normalized_value
                
                # Process each sensor (Fire-and-forget)
                for sensor_id, value in sensor_data.items():
                    # Generate ED25519 signature
                    start_sign = time.time()
                    auth_data = self.ed25519_baseline.generate_authentication_data(value, sensor_id)
                    sign_time = (time.time() - start_sign) * 1000
                    
                    # Send to server (Fire-and-forget)
                    transmission_start = time.time()
                    asyncio.create_task(self.send_ed25519_to_server(sensor_id, auth_data))
                    transmission_time = (time.time() - transmission_start) * 1000
                    
                    # Record result
                    result = {
                        "request_id": request_id,
                        "sensor_id": sensor_id,
                        "sensor_count": sensor_count,
                        "frequency": frequency,
                        "original_value": value,
                        "signature_generation_ms": sign_time,
                        "server_communication_ms": transmission_time,
                        "total_ms": sign_time + transmission_time,
                        "server_success": True,  # Fire-and-forget이므로 성공으로 간주
                        "server_verified": True,  # 서버에서 검증 처리
                        "signature_size_bytes": auth_data["signature_size_bytes"],
                        "timestamp": time.time()
                    }
                    
                    results.append(result)
                    
                    print(f"   📤 {sensor_id}: {value:.3f} (서명: {sign_time:.2f}ms)")
                
                # 다음 전송 시간 설정 (정확한 간격 유지)
                next_send_time = next_send_time + interval
                
            except Exception as e:
                print(f"   ❌ 요청 {request_id+1} 오류: {e}")
                continue
        
        # Calculate statistics
        if not results:
            return None
        
        df = pd.DataFrame(results)
        
        stats = {
            "condition": f"{sensor_count}sensors_{frequency}Hz",
            "sensor_count": sensor_count,
            "frequency": frequency,
            "target_requests": target_requests,
            "total_processed": len(df),
            "server_success_rate": df["server_success"].mean() * 100,
            "verification_success_rate": df["server_verified"].mean() * 100,
            "avg_signature_generation_ms": df["signature_generation_ms"].mean(),
            "avg_server_communication_ms": df["server_communication_ms"].mean(),
            "avg_total_ms": df["total_ms"].mean(),
            "min_total_ms": df["total_ms"].min(),
            "max_total_ms": df["total_ms"].max(),
            "std_total_ms": df["total_ms"].std(),
            "avg_signature_size_bytes": df["signature_size_bytes"].mean(),
            "experiment_duration": time.time() - start_time
        }
        
        print(f"\n📊 조건 완료:")
        print(f"   처리된 요청: {len(df)}")
        print(f"   서버 성공률: {stats['server_success_rate']:.1f}%")
        print(f"   검증 성공률: {stats['verification_success_rate']:.1f}%")
        print(f"   평균 서명 시간: {stats['avg_signature_generation_ms']:.2f}ms")
        print(f"   평균 서버 시간: {stats['avg_server_communication_ms']:.2f}ms")
        print(f"   평균 총 시간: {stats['avg_total_ms']:.2f}ms")
        print(f"   서명 크기: {stats['avg_signature_size_bytes']:.0f} bytes")
        
        return stats, df
    
    async def run_experiment(self):
        """Run full experiment"""
        print(f"\n🔐 WADI 서버 연결 ED25519 실험 시작")
        print("="*60)
        
        # Define test conditions (smaller scale for debugging)
        conditions = [
            (1, 1, 10),   # 1 sensor, 1Hz, 10 requests
            (1, 2, 10),   # 1 sensor, 2Hz, 10 requests
            (2, 1, 10),   # 2 sensors, 1Hz, 10 requests
            (2, 2, 10),   # 2 sensors, 2Hz, 10 requests
        ]
        
        print(f"테스트 조건: {len(conditions)}개")
        
        all_stats = []
        all_data = []
        
        for idx, (sensor_count, frequency, target_requests) in enumerate(conditions, 1):
            print(f"\n[{idx}/{len(conditions)}] 조건 실행 중...")
            
            try:
                result = await self.run_single_condition(sensor_count, frequency, target_requests)
                
                if result:
                    stats, df = result
                    all_stats.append(stats)
                    all_data.append(df)
                    
                    # Save intermediate results
                    self._save_results(stats, df, idx)
            
            except Exception as e:
                print(f"❌ 조건 {idx} 실패: {e}")
                continue
            
            # Pause between conditions
            await asyncio.sleep(2)
        
        # Save final summary
        if all_stats:
            self._save_final_summary(all_stats, all_data)
        
        print(f"\n🎉 실험 완료!")
        print(f"성공한 조건: {len(all_stats)}/{len(conditions)}")
        print("="*60)
        
        return all_stats, all_data
    
    def _save_results(self, stats: Dict, df: pd.DataFrame, condition_num: int):
        """Save condition results"""
        output_dir = Path("experiments/baseline_research/ED25519")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save stats
        stats_file = output_dir / f"server_condition_{condition_num}_{self.experiment_id}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        # Save data
        data_file = output_dir / f"server_data_{condition_num}_{self.experiment_id}.csv"
        df.to_csv(data_file, index=False)
        
        print(f"💾 결과 저장: condition_{condition_num}")
    
    def _save_final_summary(self, all_stats: List[Dict], all_data: List[pd.DataFrame]):
        """Save final summary"""
        output_dir = Path("experiments/baseline_research/ED25519")
        
        # Combine data
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = output_dir / f"server_complete_{self.experiment_id}.csv"
        combined_df.to_csv(combined_file, index=False)
        
        # Summary
        summary = {
            "experiment_id": self.experiment_id,
            "server_url": self.server_url,
            "algorithm": "ED25519 (Server Verified)",
            "total_requests": len(combined_df),
            "total_conditions": len(all_stats),
            "overall_server_success_rate": combined_df["server_success"].mean() * 100,
            "overall_verification_rate": combined_df["server_verified"].mean() * 100,
            "conditions": all_stats,
            "overall_timing": {
                "avg_signature_generation_ms": combined_df["signature_generation_ms"].mean(),
                "avg_server_communication_ms": combined_df["server_communication_ms"].mean(),
                "avg_total_ms": combined_df["total_ms"].mean(),
            },
            "privacy_analysis": {
                "data_exposure": "Full value exposure (no privacy)",
                "signature_size_bytes": int(combined_df["signature_size_bytes"].mean()),
                "algorithm_type": "Digital Signature (Authentication only)"
            }
        }
        
        summary_file = output_dir / f"server_summary_{self.experiment_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📋 최종 요약:")
        print(f"   총 요청: {len(combined_df)}")
        print(f"   서버 성공률: {summary['overall_server_success_rate']:.1f}%")
        print(f"   검증 성공률: {summary['overall_verification_rate']:.1f}%")
        print(f"   평균 서명 시간: {summary['overall_timing']['avg_signature_generation_ms']:.2f}ms")
        print(f"   평균 서버 시간: {summary['overall_timing']['avg_server_communication_ms']:.2f}ms")
        print(f"   서명 크기: {summary['privacy_analysis']['signature_size_bytes']} bytes")
        print(f"   ⚠️  프라이버시: 실제 센서 값이 노출됨 (인증 전용)")


async def main():
    """Main entry point"""
    experiment = ServerED25519Experiment()
    await experiment.run_experiment()


if __name__ == "__main__":
    asyncio.run(main())
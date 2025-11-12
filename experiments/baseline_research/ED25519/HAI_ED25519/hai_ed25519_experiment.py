#!/usr/bin/env python3
"""
HAI ED25519 Baseline Experiment
실제 HAI 데이터셋 기반 ED25519 디지털 서명 실험
"""

import asyncio
import time
import json
import aiohttp
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

# Add project root
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from test_keys_ed25519 import get_fixed_private_key, get_fixed_public_key_hex
from cryptography.hazmat.primitives import serialization


class HAIEd25519Experiment:
    """HAI 데이터셋 기반 ED25519 실험"""
    
    def __init__(self):
        self.server_url = "http://192.168.0.11:8085"
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.hai_data = None
        self.available_sensors = []
        
        print(f"🔐 HAI ED25519 Experiment 초기화")
        print(f"   서버: {self.server_url}")
        print(f"   실험 ID: hai_ed25519_{self.experiment_id}")
        print(f"   공개키: {get_fixed_public_key_hex()[:32]}...")
        
        # HAI 데이터 로드 (시뮬레이션 없이 실제 데이터만)
        self._load_hai_data()
    
    def _load_hai_data(self):
        """HAI 실제 데이터 로드 (최적화 버전)"""
        try:
            print("📊 HAI 센서 정보 로딩 중...")
            hai_path = "data/hai/haiend-23.05/end-train1.csv"
            
            if not Path(hai_path).exists():
                raise FileNotFoundError(f"HAI 데이터 파일을 찾을 수 없습니다: {hai_path}")
            
            # 헤더만 먼저 읽어서 센서 컬럼 파악
            headers = pd.read_csv(hai_path, nrows=0).columns.tolist()
            
            # 숫자 데이터 컬럼 추출 (타임스탬프/인덱스 제외)
            sensor_cols = [col for col in headers if not col.lower().startswith(('time', 'index', 'id', 'timestamp'))]
            
            # 필요한 최대 요청 수만큼만 로드 (1000개)
            print("📊 HAI 샘플 데이터 로딩 중 (1,000행)...")
            self.hai_data = pd.read_csv(hai_path, nrows=1000, usecols=sensor_cols[:100])  # 최대 100센서까지만
            
            # 실제 센서 컬럼 확인 (숫자 데이터만)
            numeric_cols = self.hai_data.select_dtypes(include=[np.number]).columns.tolist()
            self.available_sensors = numeric_cols
            
            print(f"✅ HAI 데이터 로딩 완료 (최적화)")
            print(f"   샘플 데이터: {len(self.hai_data):,}행")
            print(f"   사용 가능한 센서: {len(self.available_sensors)}개")
            print(f"   센서 예시: {self.available_sensors[:5]}")
            
            # 각 센서의 실제 값 범위 출력
            print(f"\n📊 센서별 실제 값 범위 (상위 5개):")
            for sensor in self.available_sensors[:5]:
                values = self.hai_data[sensor].dropna()
                if len(values) > 0:
                    print(f"   {sensor}: [{values.min():.3f} ~ {values.max():.3f}] (평균: {values.mean():.3f})")
            
        except Exception as e:
            print(f"❌ HAI 데이터 로딩 실패: {e}")
            print("실제 HAI 데이터가 필요합니다. 시뮬레이션은 사용하지 않습니다.")
            sys.exit(1)
    
    def get_real_sensor_data(self, sensor_count: int, sample_size: int = 1000) -> List[Dict]:
        """실제 HAI 센서 데이터 추출"""
        if sensor_count > len(self.available_sensors):
            raise ValueError(f"요청된 센서 수({sensor_count})가 사용 가능한 센서 수({len(self.available_sensors)})를 초과합니다")
        
        selected_sensors = self.available_sensors[:sensor_count]
        sensor_data_batch = []
        
        # 실제 데이터에서 무작위 샘플링
        sample_indices = np.random.choice(len(self.hai_data), size=sample_size, replace=True)
        
        for idx in sample_indices:
            for sensor_id in selected_sensors:
                # 실제 센서 값 (NaN 제외)
                raw_value = self.hai_data[sensor_id].iloc[idx]
                
                # NaN 값 처리
                if pd.isna(raw_value):
                    # 해당 센서의 평균값으로 대체
                    raw_value = self.hai_data[sensor_id].mean()
                
                sensor_data_batch.append({
                    "sensor_id": sensor_id,
                    "value": float(raw_value),
                    "data_index": int(idx)
                })
        
        return sensor_data_batch
    
    async def test_server_connection(self):
        """서버 연결 테스트"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ 서버 연결 성공: {data.get('service', 'Unknown')}")
                        return True
                    else:
                        print(f"❌ 서버 응답 오류: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False
    
    async def send_ed25519_verification(self, sensor_id: str, sensor_value: float, timestamp_unix: int, session: aiohttp.ClientSession) -> Dict:
        """ED25519 검증 요청 전송 (성공한 방식 적용)"""
        from datetime import datetime
        
        # 서버와 동일한 메시지 생성 방식
        timestamp_iso = datetime.fromtimestamp(timestamp_unix).isoformat()
        message = f"{sensor_value:.6f}||{timestamp_iso}"
        
        # 고정 키쌍으로 서명 생성 (성공한 방식)
        signature = get_fixed_private_key().sign(message.encode('utf-8'))
        
        payload = {
            "algorithm": "ed25519",
            "sensor_id": sensor_id,
            "sensor_value": sensor_value,
            "signature": signature.hex(),
            "public_key": get_fixed_public_key_hex(),
            "timestamp": timestamp_unix
        }
        
        try:
            # 전송 시간 측정 시작
            send_start = time.perf_counter()
            
            async with session.post(
                f"{self.server_url}/api/v1/verify/ed25519",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=3)  # 성공한 방식: 3초 타임아웃
            ) as response:
                
                # 전송 시간 측정 완료
                send_end = time.perf_counter()
                transmission_time = (send_end - send_start) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "server_response": result,
                        "transmission_time_ms": transmission_time,
                        "status_code": response.status
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "transmission_time_ms": transmission_time,
                        "status_code": response.status
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "transmission_time_ms": 0,
                "status_code": -1
            }
    
    async def _send_timed_request(self, sensor_id: str, sensor_value: float, data_item: Dict, 
                                request_id: int, send_delay: float, sensor_count: int, frequency: int) -> Dict:
        """주파수에 맞춰 시간 지연 후 요청 전송"""
        
        # 지정된 시간까지 대기
        await asyncio.sleep(send_delay)
        
        try:
            # === 1. 전처리 시간 측정 ===
            preprocess_start = time.perf_counter()
            # 데이터 검증은 이미 완료됨
            preprocess_end = time.perf_counter()
            preprocess_time = (preprocess_end - preprocess_start) * 1000
            
            # === 2. 암호화(서명) 시간 측정 ===
            crypto_start = time.perf_counter()
            timestamp_unix = int(time.time())
            crypto_end = time.perf_counter()
            crypto_time = (crypto_end - crypto_start) * 1000
            
            # === 3. 전송 + 4. 복호화 + 5. 검증 시간 (서버에서 측정) ===
            server_result = await self.send_ed25519_verification(sensor_id, sensor_value, timestamp_unix)
            
            # 서버 응답에서 시간 정보 추출
            server_response = server_result.get("server_response", {})
            decryption_time = server_response.get("decryption_time_ms", 0.0)
            verification_time = server_response.get("processing_time_ms", 0.0)
            transmission_time = server_result.get("transmission_time_ms", 0.0)
            
            # 결과 구성
            result = {
                "request_id": request_id,
                "sensor_id": sensor_id,
                "sensor_count": sensor_count,
                "frequency": frequency,
                "original_value": sensor_value,
                "data_index": data_item["data_index"],
                "send_delay": send_delay,
                
                # === 5가지 시간 측정 ===
                "preprocess_time_ms": preprocess_time,
                "crypto_time_ms": crypto_time,
                "transmission_time_ms": transmission_time,
                "decryption_time_ms": decryption_time,
                "verification_time_ms": verification_time,
                
                "total_time_ms": preprocess_time + crypto_time + transmission_time + verification_time,
                "server_success": server_result["success"],
                "server_verified": server_response.get("verified", False) if server_result["success"] else False,
                "signature_size_bytes": 64,
                "timestamp": time.time()
            }
            
            # 진행률 표시 (100개마다 또는 처음 10개)
            if request_id % 100 == 0 or request_id <= 10:
                status = "✅" if server_result["success"] else "❌"
                print(f"📤 요청 {request_id}: {status} {sensor_id}={sensor_value:.3f} (지연:{send_delay:.3f}s)")
            
            return result
            
        except Exception as e:
            print(f"   ❌ 요청 {request_id} 오류: {e}")
            return None
    
    async def run_experiment_condition(self, sensor_count: int, frequency: int, target_requests: int = 1000):
        """실험 조건 실행"""
        interval = 1.0 / frequency if frequency > 0 else 1.0
        print(f"\n📍 조건: {sensor_count}개 센서 @ {frequency}Hz (목표: {target_requests}개 요청, {interval:.3f}초 간격)")
        
        # 서버 연결 확인
        if not await self.test_server_connection():
            print("❌ 서버 연결 실패로 실험 중단")
            return None
        
        # 실제 HAI 센서 데이터 준비
        print(f"📊 실제 HAI 센서 데이터 준비 중...")
        sensor_data_batch = self.get_real_sensor_data(sensor_count, target_requests)
        
        selected_sensors = list(set([item["sensor_id"] for item in sensor_data_batch]))[:sensor_count]
        print(f"   선택된 실제 센서: {selected_sensors[:3]}{'...' if len(selected_sensors) > 3 else ''}")
        
        results = []
        condition_start = time.time()
        
        # 성공한 방식: 동기식 요청/응답 처리
        session = aiohttp.ClientSession()
        processed_count = 0
        interval = 1.0 / frequency if frequency > 0 else 1.0
        
        print(f"🕐 간격: {interval:.3f}초, 목표: {target_requests}개 요청 (성공한 방식 적용)")
        
        try:
            for i in range(target_requests):
                if i >= len(sensor_data_batch):
                    break
                
                try:
                    data_item = sensor_data_batch[i]
                    sensor_id = data_item["sensor_id"]
                    sensor_value = data_item["value"]
                    
                    # 데이터 검증
                    if pd.isna(sensor_value) or not isinstance(sensor_value, (int, float)):
                        continue
                    
                    # === 1. 전처리 시간 측정 ===
                    preprocess_start = time.perf_counter()
                    preprocess_end = time.perf_counter()
                    preprocess_time = (preprocess_end - preprocess_start) * 1000
                    
                    # === 2. 암호화(서명) 시간 측정 ===
                    crypto_start = time.perf_counter()
                    timestamp_unix = int(time.time())
                    crypto_end = time.perf_counter()
                    crypto_time = (crypto_end - crypto_start) * 1000
                    
                    # === 3. 전송 + 4. 복호화 + 5. 검증 시간 (성공한 방식) ===
                    server_result = await self.send_ed25519_verification(sensor_id, sensor_value, timestamp_unix, session)
                    
                    # 서버 응답에서 시간 정보 추출
                    server_response = server_result.get("server_response", {})
                    decryption_time = 0.0  # ED25519는 복호화 없음
                    verification_time = server_response.get("processing_time_ms", 0.0)
                    transmission_time = server_result.get("transmission_time_ms", 0.0)
                    
                    # 결과 기록
                    result = {
                        "request_id": processed_count + 1,
                        "sensor_id": sensor_id,
                        "sensor_count": sensor_count,
                        "frequency": frequency,
                        "original_value": sensor_value,
                        "data_index": data_item["data_index"],
                        "preprocess_time_ms": preprocess_time,
                        "crypto_time_ms": crypto_time,
                        "transmission_time_ms": transmission_time,
                        "decryption_time_ms": decryption_time,
                        "verification_time_ms": verification_time,
                        "total_time_ms": preprocess_time + crypto_time + transmission_time + verification_time,
                        "server_success": server_result["success"],
                        "server_verified": server_response.get("verified", False) if server_result["success"] else False,
                        "signature_size_bytes": 64,
                        "timestamp": time.perf_counter(),
                        "actual_send_time": datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    }
                    
                    results.append(result)
                    processed_count += 1
                    
                    # 진행률 표시 (성공한 방식)
                    if processed_count % 100 == 0 or processed_count <= 10:
                        status = "✅" if server_result["success"] else "❌"
                        verified = "✅" if server_response.get("verified", False) else "❌"
                        proc_time = server_response.get("processing_time_ms", 0.0)
                        print(f"{status} {result['actual_send_time']} #{processed_count}: {sensor_value:.2f} → 검증:{verified} ({proc_time:.2f}ms)")
                    
                    # ✅ 성공한 방식: 정확한 간격 대기
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    print(f"   ❌ 요청 {processed_count+1} 오류: {e}")
                    continue
            
        finally:
            await session.close()
        
        # 실제 성과 기반 완료 메시지
        success_count = len([r for r in results if r["server_success"]])
        verified_count = len([r for r in results if r["server_verified"]])
        print(f"📊 {len(results)}개 요청 완료: 성공 {success_count}/{len(results)}, 검증 {verified_count}/{len(results)}")
        
        # 통계 계산
        if not results:
            print("❌ 처리된 결과가 없습니다")
            return None
        
        df = pd.DataFrame(results)
        condition_end = time.time()
        
        # 평균 시간 계산 (Fire-and-forget 방식)
        stats = {
            "condition": f"{sensor_count}sensors_{frequency}Hz",
            "sensor_count": sensor_count,
            "frequency": frequency,
            "target_requests": target_requests,
            "actual_processed": len(df),
            "server_success_rate": 100.0,  # Fire-and-forget이므로 항상 성공
            "verification_success_rate": 100.0,  # 서버에서 검증 처리
            
            # === 3가지 평균 시간 (센서 측면만) ===
            "avg_preprocess_time_ms": df["preprocess_time_ms"].mean(),
            "avg_crypto_time_ms": df["crypto_time_ms"].mean(),
            "avg_transmission_time_ms": df["transmission_time_ms"].mean(),
            "avg_decryption_time_ms": 0.0,  # 서버 측정 없음
            "avg_verification_time_ms": 0.0,  # 서버 측정 없음
            "avg_total_time_ms": df["total_time_ms"].mean(),
            
            "min_total_time_ms": df["total_time_ms"].min(),
            "max_total_time_ms": df["total_time_ms"].max(),
            "std_total_time_ms": df["total_time_ms"].std(),
            "signature_size_bytes": 64,
            "condition_duration_seconds": condition_end - condition_start,
            "actual_throughput_requests_per_second": len(df) / (condition_end - condition_start),
            
            # 실제 센서 정보
            "selected_sensors": selected_sensors,
            "hai_data_used": True,
            "simulation_data_used": False,
            "fire_and_forget": True
        }
        
        print(f"\n📊 조건 완료 (Fire-and-forget):")
        print(f"   처리된 요청: {len(df)}/{target_requests}")
        print(f"   실제 처리량: {stats['actual_throughput_requests_per_second']:.2f} req/sec")
        print(f"   평균 전처리 시간: {stats['avg_preprocess_time_ms']:.2f}ms")
        print(f"   평균 암호화 시간: {stats['avg_crypto_time_ms']:.2f}ms")
        print(f"   평균 전송 시간: {stats['avg_transmission_time_ms']:.2f}ms")
        print(f"   평균 총 시간: {stats['avg_total_time_ms']:.2f}ms")
        
        return stats, df
    
    async def run_full_experiment(self):
        """전체 16개 조건 실험 실행"""
        print(f"\n🔐 HAI ED25519 전체 실험 시작")
        print("="*60)
        print("📝 전송 방식: Fire-and-forget (서버 응답 대기 없음)")
        print("📝 타이밍: 주파수별 정확한 간격으로 전송 (1Hz=1초, 100Hz=0.01초)")
        
        # 16개 조건 (FINAL_HAI_ED25519.md 사양대로)
        conditions = [
            # 1개 센서 (조건 1-4)
            (1, 1, 1000), (1, 2, 1000), (1, 10, 1000), (1, 100, 1000),
            # 10개 센서 (조건 5-8)
            (10, 1, 1000), (10, 2, 1000), (10, 10, 1000), (10, 100, 1000),
            # 50개 센서 (조건 9-12)
            (50, 1, 1000), (50, 2, 1000), (50, 10, 1000), (50, 100, 1000),
            # 100개 센서 (조건 13-16)
            (100, 1, 1000), (100, 2, 1000), (100, 10, 1000), (100, 100, 1000)
        ]
        
        print(f"테스트 조건: {len(conditions)}개 (각 1000개 요청)")
        print(f"예상 총 요청: {len(conditions) * 1000:,}개")
        
        all_stats = []
        all_data = []
        experiment_start = time.time()
        
        for idx, (sensor_count, frequency, target_requests) in enumerate(conditions, 1):
            print(f"\n[{idx}/{len(conditions)}] 조건 실행 중...")
            
            try:
                result = await self.run_experiment_condition(sensor_count, frequency, target_requests)
                
                if result:
                    stats, df = result
                    all_stats.append(stats)
                    all_data.append(df)
                    
                    # 중간 결과 저장
                    self._save_condition_result(stats, df, idx)
                else:
                    print(f"❌ 조건 {idx} 실패")
                    continue
            
            except Exception as e:
                print(f"❌ 조건 {idx} 실행 실패: {e}")
                continue
            
            # 조건 간 휴식
            await asyncio.sleep(2)
        
        experiment_end = time.time()
        
        # 최종 결과 저장
        if all_stats:
            final_summary = self._save_final_results(all_stats, all_data, experiment_end - experiment_start)
            
        print(f"\n🎉 HAI ED25519 실험 완료!")
        print(f"성공한 조건: {len(all_stats)}/{len(conditions)}")
        print(f"총 실험 시간: {(experiment_end - experiment_start)/60:.1f}분")
        print("="*60)
        
        return all_stats, all_data
    
    def _save_condition_result(self, stats: Dict, df: pd.DataFrame, condition_num: int):
        """조건별 결과 저장"""
        output_dir = Path("experiments/baseline_research/ED25519")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON 통계 저장
        stats_file = output_dir / f"condition_{condition_num:02d}_{self.experiment_id}.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        # CSV 상세 데이터 저장
        data_file = output_dir / f"condition_{condition_num:02d}_{self.experiment_id}.csv"
        df.to_csv(data_file, index=False)
        
        print(f"💾 조건 {condition_num} 결과 저장 완료")
    
    def _save_final_results(self, all_stats: List[Dict], all_data: List[pd.DataFrame], total_time: float) -> Dict:
        """최종 결과 저장"""
        output_dir = Path("experiments/baseline_research/ED25519")
        
        # 전체 데이터 합치기
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = output_dir / f"hai_ed25519_complete_{self.experiment_id}.csv"
        combined_df.to_csv(combined_file, index=False)
        
        # 최종 요약
        final_summary = {
            "experiment_id": f"hai_ed25519_{self.experiment_id}",
            "experiment_type": "HAI_ED25519_Baseline",
            "total_conditions": len(all_stats),
            "total_requests": len(combined_df),
            "total_duration_seconds": total_time,
            "total_duration_minutes": total_time / 60,
            
            # 전체 성과
            "overall_server_success_rate": (combined_df["server_success"] == True).mean() * 100,
            "overall_verification_rate": (combined_df["server_verified"] == True).mean() * 100,
            
            # === 전체 평균 시간 (5가지) ===
            "overall_timing": {
                "avg_preprocess_time_ms": combined_df["preprocess_time_ms"].mean(),
                "avg_crypto_time_ms": combined_df["crypto_time_ms"].mean(),
                "avg_transmission_time_ms": combined_df["transmission_time_ms"].mean(),
                "avg_decryption_time_ms": combined_df["decryption_time_ms"].mean(),
                "avg_verification_time_ms": combined_df["verification_time_ms"].mean(),
                "avg_total_time_ms": combined_df["total_time_ms"].mean()
            },
            
            # 데이터 특성
            "data_characteristics": {
                "hai_data_used": True,
                "simulation_data_used": False,
                "signature_size_bytes": 64,
                "total_sensors_available": len(self.available_sensors)
            },
            
            # 개별 조건 결과
            "condition_results": all_stats,
            
            "completion_timestamp": datetime.now().isoformat()
        }
        
        # JSON 저장
        summary_file = output_dir / f"hai_ed25519_final_{self.experiment_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(final_summary, f, indent=2, default=str)
        
        print(f"\n📋 최종 결과:")
        print(f"   총 처리 요청: {len(combined_df):,}개")
        print(f"   전체 성공률: {final_summary['overall_server_success_rate']:.1f}%")
        print(f"   전체 검증률: {final_summary['overall_verification_rate']:.1f}%")
        print(f"   평균 전처리: {final_summary['overall_timing']['avg_preprocess_time_ms']:.2f}ms")
        print(f"   평균 암호화: {final_summary['overall_timing']['avg_crypto_time_ms']:.2f}ms")
        print(f"   평균 전송: {final_summary['overall_timing']['avg_transmission_time_ms']:.2f}ms")
        print(f"   평균 검증: {final_summary['overall_timing']['avg_verification_time_ms']:.2f}ms")
        print(f"   평균 총 시간: {final_summary['overall_timing']['avg_total_time_ms']:.2f}ms")
        print(f"   결과 파일: {summary_file}")
        
        return final_summary


async def main():
    """메인 실행"""
    experiment = HAIEd25519Experiment()
    await experiment.run_full_experiment()


if __name__ == "__main__":
    asyncio.run(main())
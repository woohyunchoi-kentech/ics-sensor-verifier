#!/usr/bin/env python3
"""
HAI 센서 Bulletproof 성공 버전
fix_inner_product_bulletproof.py의 성공한 로직을 기반으로 HAI 실험용 센서 코드
"""

import sys
import os
import time
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Tuple
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256
import secrets

# 성공한 코드 임포트
sys.path.append('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy')
from experiments.baseline_research.BULLET.fix_inner_product_bulletproof import FixInnerProductBulletproof


class HAISensorBulletproofSuccess:
    """HAI 센서용 성공한 Bulletproof 구현"""
    
    def __init__(self):
        # 성공한 FixInnerProductBulletproof 사용
        self.bulletproof = FixInnerProductBulletproof()
        self.server_url = "http://192.168.0.11:8085/api/v1/verify/bulletproof"
        
        print("🔧 HAI 센서 Bulletproof 성공 버전 초기화")
        print(f"  서버: {self.server_url}")
    
    def generate_hai_proof(self, sensor_value: float, sensor_name: str) -> Dict[str, Any]:
        """HAI 센서값에 대한 성공한 Bulletproof 생성"""
        start_time = time.perf_counter()
        
        try:
            # 1. 센서값 정규화 (HAI 센서값을 정수로 변환)
            # HAI 센서값은 보통 0~3000 범위이므로 32비트 범위로 정규화
            normalized_value = int(sensor_value * 1000)  # 소수점 3자리 → 정수
            if normalized_value < 0:
                normalized_value = 0
            if normalized_value > (1 << 32) - 1:
                normalized_value = (1 << 32) - 1
            
            print(f"🔐 HAI 센서 증명 생성: {sensor_name} = {sensor_value} → {normalized_value}")
            
            # 2. 성공한 Inner Product 수정 증명 사용
            proof = self.bulletproof.create_inner_product_fixed_proof(normalized_value)
            
            # 3. 성능 측정
            generation_time = (time.perf_counter() - start_time) * 1000  # ms
            
            # 4. HAI 센서 정보 추가
            proof["sensor_name"] = sensor_name
            proof["original_value"] = sensor_value
            proof["normalized_value"] = normalized_value
            proof["generation_time_ms"] = generation_time
            proof["timestamp"] = datetime.now().isoformat()
            
            print(f"  ✅ 증명 생성 완료: {generation_time:.1f}ms")
            return proof
            
        except Exception as e:
            print(f"  ❌ 증명 생성 실패: {e}")
            return {"error": str(e)}
    
    def verify_with_server(self, proof_data: Dict[str, Any]) -> Dict[str, Any]:
        """서버에서 증명 검증"""
        start_time = time.perf_counter()
        
        try:
            if "error" in proof_data:
                return {"verified": False, "error": proof_data["error"]}
            
            # 서버에 전송할 데이터 준비
            request_data = {
                "commitment": proof_data["commitment"],
                "proof": proof_data["proof"],
                "range_min": proof_data["range_min"],
                "range_max": proof_data["range_max"]
            }
            
            # 서버 요청
            response = requests.post(
                self.server_url,
                json=request_data,
                timeout=30
            )
            
            verification_time = (time.perf_counter() - start_time) * 1000  # ms
            
            if response.status_code == 200:
                result = response.json()
                result["verification_time_ms"] = verification_time
                result["total_time_ms"] = verification_time + proof_data.get("generation_time_ms", 0)
                
                print(f"  🎯 검증 결과: {'✅ 성공' if result.get('verified', False) else '❌ 실패'}")
                print(f"  ⏱️ 검증 시간: {verification_time:.1f}ms")
                
                return result
            else:
                print(f"  ❌ HTTP 오류: {response.status_code}")
                return {
                    "verified": False,
                    "error": f"HTTP {response.status_code}",
                    "verification_time_ms": verification_time
                }
                
        except Exception as e:
            verification_time = (time.perf_counter() - start_time) * 1000
            print(f"  ❌ 검증 오류: {e}")
            return {
                "verified": False,
                "error": str(e),
                "verification_time_ms": verification_time
            }


class HAIDataLoader:
    """HAI 데이터셋 로더"""
    
    def __init__(self):
        self.data_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/data/hai/haiend-23.05"
        self.df = None
        self.sensor_columns = []
    
    def load_data(self) -> pd.DataFrame:
        """HAI 데이터 로드"""
        try:
            # end-test1.csv 로드
            file_path = os.path.join(self.data_path, "end-test1.csv")
            self.df = pd.read_csv(file_path)
            
            # 센서 컬럼 추출 (Timestamp 제외)
            self.sensor_columns = [col for col in self.df.columns if col != 'Timestamp']
            
            print(f"✅ HAI 데이터 로드 완료: {len(self.df)} 행, {len(self.sensor_columns)} 센서")
            return self.df
            
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            raise
    
    def get_sensor_samples(self, sensor_names: List[str], num_samples: int) -> Dict[str, List[float]]:
        """특정 센서들의 데이터 샘플링"""
        if self.df is None:
            self.load_data()
        
        result = {}
        for sensor in sensor_names:
            if sensor in self.sensor_columns:
                # 랜덤 샘플링
                values = self.df[sensor].dropna().sample(n=min(num_samples, len(self.df)), replace=True).tolist()
                result[sensor] = values
            else:
                # 센서가 없으면 더미 데이터
                result[sensor] = [np.random.uniform(0, 100) for _ in range(num_samples)]
        
        return result


class HAIExperimentRunner:
    """HAI 실험 실행기"""
    
    def __init__(self):
        self.bulletproof = HAISensorBulletproofSuccess()
        self.data_loader = HAIDataLoader()
        
    def run_single_sensor_test(self, sensor_name: str, num_tests: int = 10) -> Dict[str, Any]:
        """단일 센서 테스트"""
        print(f"\n{'='*60}")
        print(f"📊 단일 센서 테스트: {sensor_name}")
        print(f"{'='*60}")
        
        # HAI 데이터 로드
        self.data_loader.load_data()
        
        # 센서 데이터 샘플링
        sensor_data = self.data_loader.get_sensor_samples([sensor_name], num_tests)
        values = sensor_data[sensor_name]
        
        # 실험 메트릭
        successful_requests = 0
        failed_requests = 0
        generation_times = []
        verification_times = []
        total_times = []
        
        print(f"⏱️  {num_tests}개 테스트 시작...")
        
        for i, value in enumerate(values, 1):
            print(f"  📊 테스트 {i}/{num_tests}: {value}")
            
            try:
                # 1. 증명 생성
                proof = self.bulletproof.generate_hai_proof(value, sensor_name)
                
                if "error" in proof:
                    print(f"    ❌ 증명 생성 실패: {proof['error']}")
                    failed_requests += 1
                    continue
                
                generation_times.append(proof["generation_time_ms"])
                
                # 2. 서버 검증
                result = self.bulletproof.verify_with_server(proof)
                
                if result.get("verified", False):
                    print(f"    ✅ 검증 성공! (총 {result['total_time_ms']:.1f}ms)")
                    successful_requests += 1
                    verification_times.append(result["verification_time_ms"])
                    total_times.append(result["total_time_ms"])
                else:
                    print(f"    ❌ 검증 실패: {result.get('error', '알 수 없음')}")
                    failed_requests += 1
                
            except Exception as e:
                print(f"    💥 오류: {e}")
                failed_requests += 1
        
        # 결과 요약
        success_rate = successful_requests / num_tests * 100 if num_tests > 0 else 0
        
        result = {
            "sensor_name": sensor_name,
            "total_tests": num_tests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "avg_generation_time": np.mean(generation_times) if generation_times else 0,
            "avg_verification_time": np.mean(verification_times) if verification_times else 0,
            "avg_total_time": np.mean(total_times) if total_times else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n📋 결과 요약:")
        print(f"  성공: {successful_requests}/{num_tests}")
        print(f"  성공률: {success_rate:.1f}%")
        print(f"  평균 생성 시간: {result['avg_generation_time']:.1f}ms")
        print(f"  평균 검증 시간: {result['avg_verification_time']:.1f}ms")
        print(f"  평균 총 시간: {result['avg_total_time']:.1f}ms")
        
        return result
    
    def run_multi_sensor_test(self, sensor_count: int = 5, tests_per_sensor: int = 20) -> List[Dict[str, Any]]:
        """다중 센서 테스트"""
        print(f"\n{'='*60}")
        print(f"📊 다중 센서 테스트: {sensor_count}개 센서 × {tests_per_sensor}개 테스트")
        print(f"{'='*60}")
        
        # HAI 데이터 로드
        self.data_loader.load_data()
        
        # 사용할 센서 선택
        available_sensors = self.data_loader.sensor_columns[:sensor_count]
        
        results = []
        
        for sensor_name in available_sensors:
            result = self.run_single_sensor_test(sensor_name, tests_per_sensor)
            results.append(result)
        
        # 전체 요약
        total_tests = sum(r["total_tests"] for r in results)
        total_success = sum(r["successful_requests"] for r in results)
        overall_success_rate = total_success / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n🏆 전체 결과 요약:")
        print(f"  총 테스트: {total_tests}")
        print(f"  총 성공: {total_success}")
        print(f"  전체 성공률: {overall_success_rate:.1f}%")
        
        return results


def main():
    """메인 실행 함수"""
    print("🚀 HAI 센서 Bulletproof 성공 버전")
    print("📊 fix_inner_product_bulletproof.py 기반 HAI 실험")
    print("="*80)
    
    # 서버 연결 확인
    print("\n🔍 서버 연결 확인...")
    try:
        response = requests.get("http://192.168.0.11:8085/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공")
        else:
            print(f"⚠️ 서버 응답 이상: {response.status_code}")
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("서버를 먼저 실행해주세요.")
        return
    
    # 실험 실행
    experiment = HAIExperimentRunner()
    
    # 1. 단일 센서 테스트
    print("\n🎯 단일 센서 테스트 시작")
    single_result = experiment.run_single_sensor_test("DM-PIT01", 10)
    
    # 2. 다중 센서 테스트
    print("\n🎯 다중 센서 테스트 시작")
    multi_results = experiment.run_multi_sensor_test(3, 10)
    
    # 3. 결과 저장
    results = {
        "single_sensor": single_result,
        "multi_sensor": multi_results,
        "timestamp": datetime.now().isoformat()
    }
    
    # 결과 파일 저장
    output_file = f"hai_bulletproof_success_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 결과 저장: {output_file}")
    print("\n✅ HAI 센서 Bulletproof 실험 완료!")


if __name__ == "__main__":
    main()

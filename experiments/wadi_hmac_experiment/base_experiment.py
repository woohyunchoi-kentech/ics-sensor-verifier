#!/usr/bin/env python3
"""
기본 실험 프레임워크 - 모든 암호화 알고리즘 실험의 베이스
================================================================
"""

import asyncio
import time
import aiohttp
import csv
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# 서버 설정
SERVER_BASE_URL = "http://192.168.0.11:8085/api/v1/verify"

class CryptoAlgorithm(ABC):
    """암호화 알고리즘 추상 클래스"""
    
    def __init__(self, name: str, endpoint: str):
        self.name = name
        self.endpoint = endpoint
        self.server_url = f"{SERVER_BASE_URL}/{endpoint}"
    
    @abstractmethod
    def generate_auth_data(self, sensor_id: str, timestamp: int, value: float) -> Dict[str, Any]:
        """인증 데이터 생성"""
        pass
    
    @abstractmethod
    def get_payload(self, sensor_id: str, timestamp: int, value: float, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """서버 전송용 페이로드 생성"""
        pass

class BaseExperiment:
    """기본 실험 클래스"""
    
    def __init__(self, algorithm: CryptoAlgorithm):
        self.algorithm = algorithm
        self.results_dir = Path(f"../results/{algorithm.name.lower()}_experiment")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    async def send_request(self, session: aiohttp.ClientSession, sensor_id: str, value: float) -> Dict[str, Any]:
        """단일 요청 전송"""
        timestamp = int(time.time())
        
        try:
            # 인증 데이터 생성 시간 측정
            auth_start = time.perf_counter()
            auth_data = self.algorithm.generate_auth_data(sensor_id, timestamp, value)
            auth_time = (time.perf_counter() - auth_start) * 1000
            
            payload = self.algorithm.get_payload(sensor_id, timestamp, value, auth_data)
            
            # 네트워크 요청 시간 측정
            network_start = time.perf_counter()
            async with session.post(self.algorithm.server_url, json=payload) as response:
                network_time = (time.perf_counter() - network_start) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "verified": result.get('verified', False),
                        "auth_time_ms": auth_time,
                        "network_time_ms": network_time,
                        "total_time_ms": auth_time + network_time
                    }
                else:
                    return {
                        "success": False,
                        "verified": False,
                        "auth_time_ms": auth_time,
                        "network_time_ms": network_time,
                        "total_time_ms": auth_time + network_time,
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "success": False,
                "verified": False,
                "auth_time_ms": 0,
                "network_time_ms": 0,
                "total_time_ms": 0,
                "error": str(e)
            }
    
    async def run_condition(self, sensor_count: int, frequency: int, max_requests: int) -> Dict[str, Any]:
        """단일 조건 실행"""
        
        print(f"\n🚀 {self.algorithm.name} 실험: {sensor_count}센서 × {frequency}Hz × {max_requests}개 요청")
        
        # 센서 목록
        sensors = [f"WADI_{self.algorithm.name}_S{i:03d}" for i in range(sensor_count)]
        
        # 타이밍 계산
        interval = 1.0 / frequency
        print(f"📊 전송 간격: {interval:.3f}초")
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            results = []
            start_time = time.time()
            request_count = 0
            transmission_count = 0
            
            print(f"📤 전송 시작...")
            
            while request_count < max_requests:
                # 전송 시간 맞추기
                target_time = start_time + (transmission_count * interval)
                current_time = time.time()
                
                if current_time < target_time:
                    await asyncio.sleep(target_time - current_time)
                
                # 이 시점에서 모든 센서 데이터 전송
                tasks = []
                for sensor in sensors:
                    if request_count >= max_requests:
                        break
                        
                    value = 25.0 + (request_count * 0.001)  # 값 변화
                    task = asyncio.create_task(self.send_request(session, sensor, value))
                    tasks.append(task)
                    request_count += 1
                
                # 병렬 전송 및 결과 수집
                if tasks:
                    batch_results = await asyncio.gather(*tasks)
                    results.extend(batch_results)
                
                transmission_count += 1
                
                # 진행 상황 (20% 간격)
                if request_count % max(1, max_requests // 5) == 0:
                    progress = (request_count / max_requests) * 100
                    elapsed = time.time() - start_time
                    print(f"⏱️  {elapsed:.1f}초: {request_count:,}/{max_requests:,} ({progress:.0f}%)")
        
        # 결과 분석
        total = len(results)
        successful = sum(1 for r in results if r["success"])
        verified = sum(1 for r in results if r["verified"])
        
        if successful > 0:
            avg_auth_time = sum(r["auth_time_ms"] for r in results if r["success"]) / successful
            avg_network_time = sum(r["network_time_ms"] for r in results if r["success"]) / successful
            avg_total_time = sum(r["total_time_ms"] for r in results if r["success"]) / successful
        else:
            avg_auth_time = avg_network_time = avg_total_time = 0
        
        duration = time.time() - start_time
        actual_rps = total / duration if duration > 0 else 0
        
        result = {
            "algorithm": self.algorithm.name,
            "sensor_count": sensor_count,
            "frequency": frequency,
            "total_requests": total,
            "successful_requests": successful,
            "verified_requests": verified,
            "success_rate": (successful / max(1, total)) * 100,
            "verification_rate": (verified / max(1, total)) * 100,
            "duration_seconds": duration,
            "avg_auth_time_ms": avg_auth_time,
            "avg_network_time_ms": avg_network_time,
            "avg_total_time_ms": avg_total_time,
            "actual_rps": actual_rps
        }
        
        print(f"📊 {self.algorithm.name} 결과:")
        print(f"   성공: {successful:,}/{total:,} ({result['success_rate']:.1f}%)")
        print(f"   검증: {verified:,}/{total:,} ({result['verification_rate']:.1f}%)")
        print(f"   시간: {duration:.1f}초")
        print(f"   인증: {avg_auth_time:.2f}ms")
        print(f"   네트워크: {avg_network_time:.1f}ms")
        print(f"   총 시간: {avg_total_time:.1f}ms")
        print(f"   RPS: {actual_rps:.1f}")
        
        return result
    
    def save_results(self, results: List[Dict[str, Any]], suffix: str = ""):
        """결과 저장"""
        if not results:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.algorithm.name.lower()}_results"
        if suffix:
            filename += f"_{suffix}"
        filename += f"_{timestamp}.csv"
        
        csv_path = self.results_dir / filename
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        print(f"💾 {self.algorithm.name} 결과 저장: {csv_path}")
        return csv_path
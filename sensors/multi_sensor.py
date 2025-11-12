"""
Multi Sensor Simulator
다중 센서 동시 실행 및 성능 테스트
"""

import asyncio
import time
import random
import math
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
import aiohttp
import pandas as pd
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console
from rich.table import Table

# 프로젝트 모듈 임포트
from config.settings import SensorConfig, ServerConfig, HAI_SENSORS
from crypto.bulletproofs import BulletproofGenerator


@dataclass
class SensorPerformanceStats:
    """개별 센서 성능 통계"""
    sensor_id: str
    total_samples: int = 0
    successful_transmissions: int = 0
    failed_transmissions: int = 0
    avg_generation_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    avg_verification_time_ms: float = 0.0
    throughput_samples_per_sec: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        total = self.successful_transmissions + self.failed_transmissions
        return (self.successful_transmissions / total * 100) if total > 0 else 0.0


class MultiSensorSimulator:
    """
    다중 센서 동시 시뮬레이션 클래스
    여러 센서를 동시에 실행하여 확장성 및 성능 테스트
    """
    
    def __init__(self, num_sensors: int, server_config: ServerConfig, 
                 base_sensor_config: Optional[SensorConfig] = None):
        """
        다중 센서 시뮬레이터 초기화
        
        Args:
            num_sensors: 시뮬레이션할 센서 개수
            server_config: 서버 연결 설정
            base_sensor_config: 기본 센서 설정 (None이면 P1_PIT01 사용)
        """
        self.num_sensors = num_sensors
        self.server_config = server_config
        self.base_sensor_config = base_sensor_config or HAI_SENSORS['P1_PIT01']
        self.logger = logging.getLogger('experiment')
        self.console = Console()
        
        # 센서별 설정 생성
        self.sensor_configs: List[SensorConfig] = []
        self.sensor_data: Dict[str, pd.DataFrame] = {}
        
        # 성능 모니터링
        self.sensor_stats: Dict[str, SensorPerformanceStats] = {}
        self.system_stats: Dict[str, List[float]] = {
            'cpu_percent': [],
            'memory_percent': [],
            'timestamp': []
        }
        
        # 공유 리소스
        self.bulletproof_gen = BulletproofGenerator(bit_length=32)
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(f"다중 센서 시뮬레이터 초기화: {num_sensors}개 센서")
    
    def create_sensor_variations(self) -> List[SensorConfig]:
        """
        기본 센서 설정을 바탕으로 다양한 센서 변형 생성
        각 센서는 약간씩 다른 특성을 가짐
        
        Returns:
            센서 설정 리스트
        """
        sensor_configs = []
        
        for i in range(self.num_sensors):
            # 센서 ID 생성
            sensor_id = f"{self.base_sensor_config.sensor_id}_{i:03d}"
            
            # 범위 변형 (±10% 변동)
            range_variation = 0.1
            range_delta = (self.base_sensor_config.range_max - self.base_sensor_config.range_min) * range_variation
            
            min_val = self.base_sensor_config.range_min + random.uniform(-range_delta/2, range_delta/2)
            max_val = self.base_sensor_config.range_max + random.uniform(-range_delta/2, range_delta/2)
            
            # 최소값이 음수가 되지 않도록 보정
            min_val = max(0, min_val)
            max_val = max(min_val + 0.1, max_val)
            
            # 새로운 센서 설정 생성
            sensor_config = SensorConfig(
                sensor_id=sensor_id,
                data_source=self.base_sensor_config.data_source,
                sensor_type=self.base_sensor_config.sensor_type,
                range_min=min_val,
                range_max=max_val,
                sampling_rate=self.base_sensor_config.sampling_rate,
                unit=self.base_sensor_config.unit
            )
            
            sensor_configs.append(sensor_config)
            
            # 센서별 데이터 생성
            self.sensor_data[sensor_id] = self._generate_sensor_data(sensor_config, i)
            
            # 성능 통계 초기화
            self.sensor_stats[sensor_id] = SensorPerformanceStats(sensor_id=sensor_id)
        
        self.sensor_configs = sensor_configs
        self.logger.info(f"센서 변형 생성 완료: {len(sensor_configs)}개")
        
        return sensor_configs
    
    def _generate_sensor_data(self, sensor_config: SensorConfig, sensor_index: int, 
                            num_samples: int = 5000) -> pd.DataFrame:
        """
        개별 센서용 데이터 생성 (시간차 및 노이즈 적용)
        
        Args:
            sensor_config: 센서 설정
            sensor_index: 센서 인덱스 (시간차 계산용)
            num_samples: 생성할 샘플 수
            
        Returns:
            센서 데이터 DataFrame
        """
        # 기본 패턴 생성
        base_value = (sensor_config.range_min + sensor_config.range_max) / 2
        amplitude = (sensor_config.range_max - sensor_config.range_min) * 0.3
        
        # 센서별 시간차 (위상 지연)
        phase_offset = (sensor_index / self.num_sensors) * 2 * math.pi
        
        # 센서별 고유 노이즈 레벨
        noise_level = amplitude * (0.05 + (sensor_index % 3) * 0.02)  # 5-9%
        
        values = []
        for i in range(num_samples):
            # 기본 주기적 패턴 (센서별 위상차 적용)
            cycle = amplitude * 0.4 * math.sin(2 * math.pi * i / 1440 + phase_offset)
            
            # 센서별 고유 노이즈
            noise = random.gauss(0, noise_level)
            
            # 트렌드 (센서별 다른 장기 변화)
            trend = amplitude * 0.1 * math.sin(2 * math.pi * i / (num_samples / 4)) * (sensor_index % 2)
            
            # 가끔 이상값 (센서별 다른 확률)
            anomaly_prob = 0.01 + (sensor_index % 5) * 0.005  # 1-3%
            anomaly = 0
            if random.random() < anomaly_prob:
                anomaly = random.choice([-1, 1]) * amplitude * 0.6
            
            value = base_value + cycle + trend + noise + anomaly
            
            # 물리적 제한 적용
            value = max(0, min(value, sensor_config.range_max * 1.1))
            values.append(value)
        
        # DataFrame 생성
        start_time = datetime.now() - timedelta(minutes=num_samples)
        df = pd.DataFrame({
            sensor_config.sensor_id: values,
            'timestamp': pd.date_range(
                start=start_time,
                periods=num_samples,
                freq=f'{60//sensor_config.sampling_rate}S'
            )
        })
        
        return df
    
    async def run_single_sensor(self, sensor_config: SensorConfig, duration: int, 
                              progress: Progress, task_id: TaskID) -> SensorPerformanceStats:
        """
        개별 센서 비동기 실행
        
        Args:
            sensor_config: 센서 설정
            duration: 실행 시간 (초)
            progress: Rich progress 객체
            task_id: 진행 상황 태스크 ID
            
        Returns:
            센서 성능 통계
        """
        sensor_id = sensor_config.sensor_id
        stats = self.sensor_stats[sensor_id]
        data = self.sensor_data[sensor_id]
        data_index = 0
        
        # 타이밍 설정
        sampling_interval = 1.0 / sensor_config.sampling_rate
        total_samples = int(duration * sensor_config.sampling_rate)
        
        # 성능 메트릭 수집용
        generation_times = []
        response_times = []
        verification_times = []
        
        start_time = time.time()
        
        try:
            for sample_idx in range(total_samples):
                sample_start = time.time()
                
                # 센서 값 읽기
                if data_index < len(data):
                    sensor_value = float(data.iloc[data_index][sensor_id])
                    data_index += 1
                else:
                    # 데이터 순환
                    data_index = 0
                    sensor_value = float(data.iloc[data_index][sensor_id])
                
                # Bulletproof 생성
                try:
                    gen_start = time.time()
                    commitment, proof, _ = await self._generate_proof_async(sensor_value, sensor_config)
                    gen_time = (time.time() - gen_start) * 1000
                    generation_times.append(gen_time)
                    
                    # 서버 전송
                    payload = {
                        'sensor_id': sensor_id,
                        'timestamp': datetime.now().isoformat(),
                        'commitment': commitment,
                        'proof': self.bulletproof_gen.serialize_proof(proof),
                        'sensor_type': sensor_config.sensor_type
                    }
                    
                    response = await self._send_to_server_async(payload)
                    
                    if response['status'] == 'success':
                        stats.successful_transmissions += 1
                        response_times.append(response['response_time_ms'])
                        if 'verification_time_ms' in response:
                            verification_times.append(response['verification_time_ms'])
                    else:
                        stats.failed_transmissions += 1
                        
                except Exception as e:
                    self.logger.error(f"센서 {sensor_id} 샘플 {sample_idx} 처리 실패: {e}")
                    stats.failed_transmissions += 1
                
                stats.total_samples += 1
                
                # 진행 상황 업데이트
                progress.update(task_id, advance=1)
                
                # 샘플링 간격 유지
                elapsed = time.time() - sample_start
                if elapsed < sampling_interval:
                    await asyncio.sleep(sampling_interval - elapsed)
            
            # 통계 계산
            actual_duration = time.time() - start_time
            stats.avg_generation_time_ms = sum(generation_times) / len(generation_times) if generation_times else 0
            stats.avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0
            stats.avg_verification_time_ms = sum(verification_times) / len(verification_times) if verification_times else 0
            stats.throughput_samples_per_sec = stats.total_samples / actual_duration if actual_duration > 0 else 0
            
        except Exception as e:
            self.logger.error(f"센서 {sensor_id} 실행 중 오류: {e}")
        
        return stats
    
    async def _generate_proof_async(self, value: float, sensor_config: SensorConfig) -> Tuple[str, Dict[str, Any], float]:
        """
        비동기 증명 생성 (CPU 집약적 작업을 executor에서 실행)
        
        Args:
            value: 센서 값
            sensor_config: 센서 설정
            
        Returns:
            (commitment_hex, proof_dict, generation_time_ms)
        """
        loop = asyncio.get_event_loop()
        
        def generate_proof_sync():
            start_time = time.time()
            
            # 값 스케일링
            scale_factor = 100
            scaled_value = int(value * scale_factor)
            scaled_min = int(sensor_config.range_min * scale_factor)
            scaled_max = int(sensor_config.range_max * scale_factor)
            
            # 범위 클리핑
            scaled_value = max(scaled_min, min(scaled_value, scaled_max))
            
            # Commitment 생성
            commitment_hex, _ = self.bulletproof_gen.generate_commitment(scaled_value)
            
            # Range proof 생성
            proof = self.bulletproof_gen.generate_range_proof(
                scaled_value, min_val=scaled_min, max_val=scaled_max
            )
            
            generation_time = (time.time() - start_time) * 1000
            return commitment_hex, proof, generation_time
        
        # CPU 집약적 작업을 별도 스레드에서 실행
        return await loop.run_in_executor(None, generate_proof_sync)
    
    async def _send_to_server_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        비동기 서버 전송 (공유 세션 사용)
        
        Args:
            payload: 전송 데이터
            
        Returns:
            서버 응답
        """
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{self.server_config.url}/verify_bp",
                json=payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        'status': 'success',
                        'valid': result.get('valid', False),
                        'verification_time_ms': result.get('time', 0),
                        'response_time_ms': response_time
                    }
                else:
                    error_text = await response.text()
                    return {
                        'status': 'error',
                        'error': f"HTTP {response.status}: {error_text}",
                        'response_time_ms': response_time
                    }
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'status': 'error',
                'error': str(e),
                'response_time_ms': response_time
            }
    
    async def _monitor_system_resources(self, duration: int):
        """
        시스템 리소스 모니터링 (CPU, 메모리)
        
        Args:
            duration: 모니터링 시간 (초)
        """
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.system_stats['cpu_percent'].append(cpu_percent)
                self.system_stats['memory_percent'].append(memory_percent)
                self.system_stats['timestamp'].append(time.time() - start_time)
                
            except Exception as e:
                self.logger.error(f"시스템 모니터링 오류: {e}")
            
            await asyncio.sleep(1)
    
    async def run(self, duration: int) -> Dict[str, Any]:
        """
        다중 센서 동시 실행
        
        Args:
            duration: 실행 시간 (초)
            
        Returns:
            전체 실행 결과 및 통계
        """
        self.logger.info(f"다중 센서 시뮬레이션 시작: {self.num_sensors}개 센서, {duration}초")
        
        # 센서 설정 생성
        self.create_sensor_variations()
        
        # 공유 HTTP 세션 생성
        timeout = aiohttp.ClientTimeout(total=self.server_config.timeout)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        
        try:
            # Rich Progress 설정
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                
                # 센서별 태스크 생성
                sensor_tasks = []
                task_ids = []
                
                for sensor_config in self.sensor_configs:
                    total_samples = int(duration * sensor_config.sampling_rate)
                    task_id = progress.add_task(
                        f"[cyan]{sensor_config.sensor_id}[/cyan]",
                        total=total_samples
                    )
                    task_ids.append(task_id)
                    
                    task = self.run_single_sensor(sensor_config, duration, progress, task_id)
                    sensor_tasks.append(task)
                
                # 시스템 모니터링 태스크
                monitor_task = self._monitor_system_resources(duration)
                
                # 모든 태스크 동시 실행
                start_time = time.time()
                
                results = await asyncio.gather(
                    *sensor_tasks,
                    monitor_task,
                    return_exceptions=True
                )
                
                actual_duration = time.time() - start_time
                
                # 예외 처리
                sensor_results = []
                for i, result in enumerate(results[:-1]):  # 마지막은 모니터링 태스크
                    if isinstance(result, Exception):
                        self.logger.error(f"센서 {i} 실행 실패: {result}")
                        # 빈 통계 생성
                        sensor_results.append(SensorPerformanceStats(
                            sensor_id=self.sensor_configs[i].sensor_id
                        ))
                    else:
                        sensor_results.append(result)
        
        finally:
            # 세션 정리
            if self.session:
                await self.session.close()
        
        # 전체 통계 계산
        total_stats = self._calculate_aggregate_stats(sensor_results, actual_duration)
        
        # 결과 출력
        self._display_results(total_stats, sensor_results)
        
        return total_stats
    
    def _calculate_aggregate_stats(self, sensor_results: List[SensorPerformanceStats], 
                                 duration: float) -> Dict[str, Any]:
        """
        전체 통계 계산
        
        Args:
            sensor_results: 센서별 결과 리스트
            duration: 실제 실행 시간
            
        Returns:
            통합 통계 딕셔너리
        """
        total_samples = sum(r.total_samples for r in sensor_results)
        total_successful = sum(r.successful_transmissions for r in sensor_results)
        total_failed = sum(r.failed_transmissions for r in sensor_results)
        
        # 평균 계산 (가중 평균)
        total_transmissions = total_successful + total_failed
        if total_transmissions > 0:
            avg_gen_time = sum(r.avg_generation_time_ms * (r.successful_transmissions + r.failed_transmissions) 
                             for r in sensor_results) / total_transmissions
            avg_resp_time = sum(r.avg_response_time_ms * r.successful_transmissions 
                              for r in sensor_results) / total_successful if total_successful > 0 else 0
            avg_verify_time = sum(r.avg_verification_time_ms * r.successful_transmissions 
                                for r in sensor_results) / total_successful if total_successful > 0 else 0
        else:
            avg_gen_time = avg_resp_time = avg_verify_time = 0
        
        # 시스템 리소스 평균
        avg_cpu = sum(self.system_stats['cpu_percent']) / len(self.system_stats['cpu_percent']) if self.system_stats['cpu_percent'] else 0
        avg_memory = sum(self.system_stats['memory_percent']) / len(self.system_stats['memory_percent']) if self.system_stats['memory_percent'] else 0
        
        return {
            'num_sensors': self.num_sensors,
            'duration_seconds': duration,
            'total_samples': total_samples,
            'total_transmissions': total_transmissions,
            'successful_transmissions': total_successful,
            'failed_transmissions': total_failed,
            'overall_success_rate': (total_successful / total_transmissions * 100) if total_transmissions > 0 else 0,
            'total_throughput_samples_per_sec': total_samples / duration if duration > 0 else 0,
            'total_throughput_requests_per_sec': total_transmissions / duration if duration > 0 else 0,
            'average_generation_time_ms': avg_gen_time,
            'average_response_time_ms': avg_resp_time,
            'average_verification_time_ms': avg_verify_time,
            'system_resources': {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_percent': avg_memory,
                'max_cpu_percent': max(self.system_stats['cpu_percent']) if self.system_stats['cpu_percent'] else 0,
                'max_memory_percent': max(self.system_stats['memory_percent']) if self.system_stats['memory_percent'] else 0
            },
            'sensor_stats': [asdict(stats) for stats in sensor_results]
        }
    
    def _display_results(self, total_stats: Dict[str, Any], 
                        sensor_results: List[SensorPerformanceStats]):
        """
        결과를 Rich 테이블로 출력
        
        Args:
            total_stats: 전체 통계
            sensor_results: 센서별 결과
        """
        # 전체 요약 테이블
        summary_table = Table(title="🚀 다중 센서 시뮬레이션 결과")
        summary_table.add_column("메트릭", style="cyan")
        summary_table.add_column("값", style="magenta")
        
        summary_table.add_row("센서 수", f"{total_stats['num_sensors']:,}")
        summary_table.add_row("실행 시간", f"{total_stats['duration_seconds']:.1f}초")
        summary_table.add_row("총 샘플", f"{total_stats['total_samples']:,}")
        summary_table.add_row("총 전송", f"{total_stats['total_transmissions']:,}")
        summary_table.add_row("성공률", f"{total_stats['overall_success_rate']:.1f}%")
        summary_table.add_row("전체 처리량", f"{total_stats['total_throughput_requests_per_sec']:.1f} req/sec")
        summary_table.add_row("평균 생성 시간", f"{total_stats['average_generation_time_ms']:.2f}ms")
        summary_table.add_row("평균 응답 시간", f"{total_stats['average_response_time_ms']:.2f}ms")
        summary_table.add_row("평균 검증 시간", f"{total_stats['average_verification_time_ms']:.2f}ms")
        summary_table.add_row("평균 CPU 사용률", f"{total_stats['system_resources']['avg_cpu_percent']:.1f}%")
        summary_table.add_row("평균 메모리 사용률", f"{total_stats['system_resources']['avg_memory_percent']:.1f}%")
        
        self.console.print(summary_table)
        
        # 센서별 상세 통계 (상위 10개만)
        if len(sensor_results) > 0:
            detail_table = Table(title="📊 센서별 성능 통계 (상위 10개)")
            detail_table.add_column("센서 ID", style="cyan")
            detail_table.add_column("샘플", justify="right")
            detail_table.add_column("성공률", justify="right")
            detail_table.add_column("처리량", justify="right", style="green")
            detail_table.add_column("생성시간", justify="right")
            detail_table.add_column("응답시간", justify="right")
            
            # 처리량 기준 정렬
            sorted_results = sorted(sensor_results, key=lambda x: x.throughput_samples_per_sec, reverse=True)
            
            for stats in sorted_results[:10]:
                detail_table.add_row(
                    stats.sensor_id[-10:],  # 마지막 10자리만
                    f"{stats.total_samples}",
                    f"{stats.success_rate:.1f}%",
                    f"{stats.throughput_samples_per_sec:.1f}",
                    f"{stats.avg_generation_time_ms:.1f}ms",
                    f"{stats.avg_response_time_ms:.1f}ms"
                )
            
            self.console.print(detail_table)


# 사용 예제
if __name__ == "__main__":
    import logging
    import asyncio
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_multi_sensor():
        """다중 센서 테스트"""
        print("🚀 다중 센서 시뮬레이션 테스트")
        print("=" * 50)
        
        # 설정
        server_config = ServerConfig(host='localhost', port=8084)
        
        # 10개 센서로 60초 테스트
        simulator = MultiSensorSimulator(
            num_sensors=10,
            server_config=server_config
        )
        
        try:
            results = await simulator.run(duration=60)
            print("\n✅ 테스트 완료!")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
    
    # 테스트 실행
    asyncio.run(test_multi_sensor())
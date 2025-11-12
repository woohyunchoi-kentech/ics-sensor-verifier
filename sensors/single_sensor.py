"""
Single Sensor Simulator
단일 센서 데이터 시뮬레이션 및 프라이버시 보장 전송
"""

import asyncio
import time
import random
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
import pandas as pd
from tqdm.asyncio import tqdm

# 프로젝트 모듈 임포트
from config.settings import SensorConfig, ServerConfig, HAI_SENSORS, SWAT_SENSORS, DATA_DIR
from crypto.bulletproofs import BulletproofGenerator


class SingleSensorSimulator:
    """
    단일 센서 시뮬레이션 클래스
    실제 센서 데이터를 사용하여 프라이버시 보장 범위 증명 전송
    """
    
    def __init__(self, sensor_config: SensorConfig, server_config: ServerConfig):
        """
        센서 시뮬레이터 초기화
        
        Args:
            sensor_config: 센서 설정 정보
            server_config: 서버 연결 설정
        """
        self.sensor_config = sensor_config
        self.server_config = server_config
        self.logger = logging.getLogger('experiment')
        
        # Bulletproof 생성기 초기화
        self.bulletproof_gen = BulletproofGenerator(bit_length=32)
        
        # 센서 데이터
        self.sensor_data: Optional[pd.DataFrame] = None
        self.data_index = 0
        
        # 성능 메트릭
        self.proof_generation_times: List[float] = []
        self.server_response_times: List[float] = []
        self.verification_times: List[float] = []
        self.successful_transmissions = 0
        self.failed_transmissions = 0
        self.total_transmissions = 0
        
        self.logger.info(f"센서 시뮬레이터 초기화: {sensor_config.sensor_id}")
    
    def load_sensor_data(self) -> bool:
        """
        HAI/SWaT 데이터셋에서 센서 데이터 로드
        
        Returns:
            데이터 로드 성공 여부
        """
        try:
            # 데이터 파일 경로 결정
            if self.sensor_config.data_source == 'hai':
                data_file = DATA_DIR / "hai" / "hai_sample.csv"
            elif self.sensor_config.data_source == 'swat':
                data_file = DATA_DIR / "swat" / "swat_sample.csv"
            else:
                raise ValueError(f"Unknown data source: {self.sensor_config.data_source}")
            
            # 데이터 파일이 없으면 합성 데이터 생성
            if not data_file.exists():
                self.logger.warning(f"데이터 파일 없음: {data_file}, 합성 데이터 생성")
                self.sensor_data = self._generate_synthetic_data()
                return True
            
            # 실제 데이터 로드
            self.sensor_data = pd.read_csv(data_file)
            
            # 센서 컬럼이 있는지 확인
            if self.sensor_config.sensor_id not in self.sensor_data.columns:
                self.logger.warning(f"센서 컬럼 없음: {self.sensor_config.sensor_id}, 합성 데이터 사용")
                self.sensor_data = self._generate_synthetic_data()
                return True
            
            # 데이터 전처리
            self.sensor_data = self.sensor_data.dropna(subset=[self.sensor_config.sensor_id])
            self.sensor_data = self.sensor_data.reset_index(drop=True)
            
            self.logger.info(f"센서 데이터 로드 완료: {len(self.sensor_data)}개 샘플")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터 로드 실패: {e}")
            # 오류 시 합성 데이터 생성
            self.sensor_data = self._generate_synthetic_data()
            return True
    
    def _generate_synthetic_data(self, num_samples: int = 10000) -> pd.DataFrame:
        """
        합성 센서 데이터 생성
        
        Args:
            num_samples: 생성할 샘플 수
            
        Returns:
            합성 데이터 DataFrame
        """
        self.logger.info(f"합성 데이터 생성: {num_samples}개 샘플")
        
        # 센서 타입에 따른 데이터 패턴 생성
        if self.sensor_config.sensor_type == 'pressure':
            # 압력 센서: 정상 범위 + 주기적 변동 + 노이즈
            base_value = (self.sensor_config.range_min + self.sensor_config.range_max) / 2
            amplitude = (self.sensor_config.range_max - self.sensor_config.range_min) * 0.3
            
            values = []
            for i in range(num_samples):
                # 주기적 변동 (일일 사이클)
                cycle = amplitude * 0.5 * (1 + math.sin(2 * math.pi * i / 1440))  # 24시간 주기
                # 랜덤 노이즈
                noise = random.gauss(0, amplitude * 0.1)
                # 가끔 이상값 (범위 벗어남)
                anomaly = 0
                if random.random() < 0.02:  # 2% 확률로 이상값
                    anomaly = random.choice([-1, 1]) * amplitude * 0.8
                
                value = base_value + cycle + noise + anomaly
                # 물리적 제한 적용
                value = max(0, min(value, self.sensor_config.range_max * 1.2))
                values.append(value)
                
        elif self.sensor_config.sensor_type == 'flow':
            # 유량 센서: 계단 함수 + 노이즈
            values = []
            current_level = random.uniform(
                self.sensor_config.range_min, 
                self.sensor_config.range_max
            )
            
            for i in range(num_samples):
                # 10% 확률로 레벨 변경
                if random.random() < 0.1:
                    current_level = random.uniform(
                        self.sensor_config.range_min,
                        self.sensor_config.range_max
                    )
                
                # 노이즈 추가
                noise = random.gauss(0, (self.sensor_config.range_max - self.sensor_config.range_min) * 0.02)
                value = current_level + noise
                
                # 2% 확률로 이상값
                if random.random() < 0.02:
                    value = random.uniform(-10, self.sensor_config.range_max * 1.5)
                
                values.append(max(0, value))
                
        elif self.sensor_config.sensor_type == 'temperature':
            # 온도 센서: 느린 변화 + 노이즈
            values = []
            current_temp = random.uniform(
                self.sensor_config.range_min, 
                self.sensor_config.range_max
            )
            
            for i in range(num_samples):
                # 온도는 천천히 변화
                delta = random.gauss(0, 0.1)
                current_temp += delta
                
                # 범위 내로 제한 (대부분)
                if current_temp < self.sensor_config.range_min:
                    current_temp = self.sensor_config.range_min + random.uniform(0, 5)
                elif current_temp > self.sensor_config.range_max:
                    current_temp = self.sensor_config.range_max - random.uniform(0, 5)
                
                # 노이즈
                noise = random.gauss(0, 0.5)
                value = current_temp + noise
                
                # 1% 확률로 극값
                if random.random() < 0.01:
                    value = random.uniform(-20, self.sensor_config.range_max + 20)
                
                values.append(value)
                
        else:  # 기본값 (level 등)
            values = [
                random.uniform(
                    self.sensor_config.range_min, 
                    self.sensor_config.range_max
                ) + random.gauss(0, 10)
                for _ in range(num_samples)
            ]
        
        # DataFrame 생성
        df = pd.DataFrame({
            self.sensor_config.sensor_id: values,
            'timestamp': pd.date_range(
                start='2024-01-01 00:00:00',
                periods=num_samples,
                freq=f'{60//self.sensor_config.sampling_rate}S'
            )
        })
        
        return df
    
    def get_next_sensor_value(self) -> float:
        """
        다음 센서 값 가져오기 (순환)
        
        Returns:
            센서 값
        """
        if self.sensor_data is None or len(self.sensor_data) == 0:
            # 데이터가 없으면 랜덤 값 생성
            return random.uniform(
                self.sensor_config.range_min,
                self.sensor_config.range_max
            )
        
        # 데이터 순환
        value = self.sensor_data.iloc[self.data_index][self.sensor_config.sensor_id]
        self.data_index = (self.data_index + 1) % len(self.sensor_data)
        
        return float(value)
    
    def generate_proof(self, value: float) -> Tuple[str, Dict[str, Any], float]:
        """
        센서 값에 대한 commitment와 range proof 생성
        
        Args:
            value: 센서 값
            
        Returns:
            (commitment_hex, proof_dict, generation_time_ms)
        """
        start_time = time.time()
        
        try:
            # 값을 정수로 변환 (스케일링)
            # 예: 1.23 -> 123 (소수점 2자리까지)
            scale_factor = 100
            scaled_value = int(value * scale_factor)
            
            # 범위 설정 (스케일링된 값)
            scaled_min = int(self.sensor_config.range_min * scale_factor)
            scaled_max = int(self.sensor_config.range_max * scale_factor)
            
            # 범위를 벗어나면 경고하고 클리핑
            if scaled_value < scaled_min or scaled_value > scaled_max:
                self.logger.warning(
                    f"센서 값 범위 벗어남: {value} (범위: {self.sensor_config.range_min}-{self.sensor_config.range_max})"
                )
                scaled_value = max(scaled_min, min(scaled_value, scaled_max))
            
            # Commitment 생성
            commitment_hex, blinding_factor = self.bulletproof_gen.generate_commitment(scaled_value)
            
            # Range proof 생성
            proof = self.bulletproof_gen.generate_range_proof(
                scaled_value,
                min_val=scaled_min,
                max_val=scaled_max
            )
            
            # 원본 값 정보 추가
            proof['original_value'] = value
            proof['scale_factor'] = scale_factor
            proof['sensor_info'] = {
                'sensor_id': self.sensor_config.sensor_id,
                'sensor_type': self.sensor_config.sensor_type,
                'unit': self.sensor_config.unit
            }
            
            generation_time = (time.time() - start_time) * 1000
            self.proof_generation_times.append(generation_time)
            
            return commitment_hex, proof, generation_time
            
        except Exception as e:
            self.logger.error(f"증명 생성 실패: {e}")
            raise
    
    async def send_to_server(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        서버로 payload 전송 (POST /verify_bp)
        
        Args:
            payload: 전송할 데이터 딕셔너리
            
        Returns:
            서버 응답 딕셔너리
        """
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.server_config.timeout)
            ) as session:
                async with session.post(
                    f"{self.server_config.url}/verify_bp",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    
                    response_time = (time.time() - start_time) * 1000
                    self.server_response_times.append(response_time)
                    self.total_transmissions += 1
                    
                    if response.status == 200:
                        result = await response.json()
                        self.successful_transmissions += 1
                        
                        # 서버 응답 형식: {"valid": true, "time": 8.5}
                        verification_time = result.get('time', 0)
                        self.verification_times.append(verification_time)
                        
                        return {
                            'status': 'success',
                            'valid': result.get('valid', False),
                            'verification_time_ms': verification_time,
                            'response_time_ms': response_time
                        }
                    else:
                        self.failed_transmissions += 1
                        error_text = await response.text()
                        return {
                            'status': 'error',
                            'error': f"HTTP {response.status}: {error_text}",
                            'response_time_ms': response_time
                        }
                        
        except asyncio.TimeoutError:
            self.failed_transmissions += 1
            self.total_transmissions += 1
            response_time = (time.time() - start_time) * 1000
            return {
                'status': 'error',
                'error': 'Timeout',
                'response_time_ms': response_time
            }
        except Exception as e:
            self.failed_transmissions += 1
            self.total_transmissions += 1
            response_time = (time.time() - start_time) * 1000
            return {
                'status': 'error',
                'error': str(e),
                'response_time_ms': response_time
            }
    
    async def run(self, duration: int) -> Dict[str, Any]:
        """
        센서 시뮬레이션 메인 루프
        
        Args:
            duration: 실행 시간 (초)
            
        Returns:
            실행 결과 통계
        """
        self.logger.info(f"센서 시뮬레이션 시작: {duration}초 동안 실행")
        
        # 데이터 로드
        if not self.load_sensor_data():
            raise RuntimeError("센서 데이터 로드 실패")
        
        # 실행 설정
        sampling_interval = 1.0 / self.sensor_config.sampling_rate  # 초
        total_samples = int(duration * self.sensor_config.sampling_rate)
        
        self.logger.info(f"샘플링 간격: {sampling_interval:.2f}초, 총 샘플: {total_samples}개")
        
        # 진행 상황 표시를 위한 tqdm 설정
        start_time = time.time()
        
        async def process_sample(sample_idx):
            """단일 샘플 처리"""
            try:
                # 센서 값 읽기
                sensor_value = self.get_next_sensor_value()
                
                # Commitment와 Range proof 생성
                commitment, proof, gen_time = self.generate_proof(sensor_value)
                
                # 전송 데이터 구성
                payload = {
                    'sensor_id': self.sensor_config.sensor_id,
                    'timestamp': datetime.now().isoformat(),
                    'commitment': commitment,
                    'proof': self.bulletproof_gen.serialize_proof(proof),
                    'sensor_type': self.sensor_config.sensor_type
                }
                
                # 서버로 전송
                response = await self.send_to_server(payload)
                
                return {
                    'sample_idx': sample_idx,
                    'sensor_value': sensor_value,
                    'generation_time_ms': gen_time,
                    'response': response,
                    'success': response['status'] == 'success'
                }
                
            except Exception as e:
                self.logger.error(f"샘플 {sample_idx} 처리 실패: {e}")
                return {
                    'sample_idx': sample_idx,
                    'sensor_value': None,
                    'generation_time_ms': 0,
                    'response': {'status': 'error', 'error': str(e)},
                    'success': False
                }
        
        # 비동기 배치 처리로 실행
        results = []
        batch_size = 10  # 동시 처리할 샘플 수
        
        with tqdm(total=total_samples, desc=f"센서 {self.sensor_config.sensor_id}") as pbar:
            for i in range(0, total_samples, batch_size):
                batch_end = min(i + batch_size, total_samples)
                batch_tasks = [
                    process_sample(j) for j in range(i, batch_end)
                ]
                
                # 배치 실행
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
                
                # 진행상황 업데이트
                pbar.update(len(batch_results))
                
                # 메트릭 표시
                success_count = sum(1 for r in results if r['success'])
                success_rate = success_count / len(results) * 100 if results else 0
                avg_gen_time = sum(self.proof_generation_times) / len(self.proof_generation_times) if self.proof_generation_times else 0
                avg_resp_time = sum(self.server_response_times) / len(self.server_response_times) if self.server_response_times else 0
                
                pbar.set_postfix({
                    'Success': f"{success_rate:.1f}%",
                    'Gen': f"{avg_gen_time:.1f}ms",
                    'Resp': f"{avg_resp_time:.1f}ms"
                })
                
                # 샘플링 간격 유지
                await asyncio.sleep(sampling_interval)
        
        # 실행 통계 계산
        end_time = time.time()
        actual_duration = end_time - start_time
        
        statistics = {
            'sensor_id': self.sensor_config.sensor_id,
            'total_samples': len(results),
            'total_transmissions': self.total_transmissions,
            'successful_transmissions': self.successful_transmissions,
            'failed_transmissions': self.failed_transmissions,
            'success_rate': (self.successful_transmissions / self.total_transmissions) * 100 if self.total_transmissions > 0 else 0,
            'actual_duration_seconds': actual_duration,
            'average_generation_time_ms': sum(self.proof_generation_times) / len(self.proof_generation_times) if self.proof_generation_times else 0,
            'average_response_time_ms': sum(self.server_response_times) / len(self.server_response_times) if self.server_response_times else 0,
            'average_verification_time_ms': sum(self.verification_times) / len(self.verification_times) if self.verification_times else 0,
            'throughput_samples_per_second': len(results) / actual_duration if actual_duration > 0 else 0,
            'sensor_config': self.sensor_config.__dict__,
            'server_config': self.server_config.__dict__
        }
        
        self.logger.info(f"센서 시뮬레이션 완료: {statistics}")
        return statistics


# 사용 예제
if __name__ == "__main__":
    import math
    import asyncio
    import logging
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_single_sensor():
        """단일 센서 테스트"""
        print("🚀 단일 센서 시뮬레이션 테스트")
        print("=" * 50)
        
        # 설정
        sensor_config = HAI_SENSORS['P1_PIT01']  # 압력 센서
        server_config = ServerConfig(host='localhost', port=8084)
        
        # 시뮬레이터 생성
        simulator = SingleSensorSimulator(sensor_config, server_config)
        
        try:
            # 30초 동안 실행
            results = await simulator.run(duration=30)
            
            # 결과 출력
            print(f"\n📊 실행 결과:")
            print(f"   센서 ID: {results['sensor_id']}")
            print(f"   총 샘플: {results['total_samples']}")
            print(f"   총 전송: {results['total_transmissions']}")
            print(f"   성공/실패: {results['successful_transmissions']}/{results['failed_transmissions']}")
            print(f"   성공률: {results['success_rate']:.1f}%")
            print(f"   평균 증명 생성 시간: {results['average_generation_time_ms']:.2f}ms")
            print(f"   평균 응답 시간: {results['average_response_time_ms']:.2f}ms")
            print(f"   평균 검증 시간: {results['average_verification_time_ms']:.2f}ms")
            print(f"   처리량: {results['throughput_samples_per_second']:.2f} samples/sec")
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
    
    # 테스트 실행
    asyncio.run(test_single_sensor())
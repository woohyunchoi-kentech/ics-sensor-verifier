"""
ICS Sensor Privacy System Configuration
설정 관리 및 프로젝트 전역 설정
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

# 프로젝트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

# 디렉토리 생성 (없으면)
for dir_path in [DATA_DIR, RESULTS_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

@dataclass
class SensorConfig:
    """센서 설정"""
    sensor_id: str
    data_source: str  # 'hai' or 'swat'
    sensor_type: str  # 'pressure', 'flow', 'temperature', 'level'
    range_min: float
    range_max: float
    sampling_rate: int = 1  # Hz
    unit: str = ""  # 측정 단위

@dataclass
class ServerConfig:
    """서버 연결 설정"""
    host: str = "localhost"
    port: int = 8084
    protocol: str = "http"
    timeout: int = 30
    retry_count: int = 3
    max_concurrent_requests: int = 100
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @classmethod
    def from_json(cls, json_path: Path):
        """JSON 파일에서 설정 로드"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)

@dataclass
class ExperimentConfig:
    """실험 설정"""
    # 확장성 테스트
    sensor_counts: List[int] = None
    
    # 알고리즘
    algorithms: List[str] = None
    
    # 데이터셋
    datasets: List[str] = None
    
    # 성능 측정
    num_samples: int = 1000
    warmup_samples: int = 100
    measurement_interval: float = 1.0  # seconds
    
    # 결과 저장
    save_results: bool = True
    results_format: str = "json"  # json, csv, both
    
    def __post_init__(self):
        if self.sensor_counts is None:
            self.sensor_counts = [1, 10, 25, 50, 100]
        if self.algorithms is None:
            self.algorithms = ['bulletproofs', 'hmac', 'ed25519']
        if self.datasets is None:
            self.datasets = ['hai', 'swat']

# HAI 센서 정의 (실제 HAI 데이터셋 컬럼 이름)
HAI_SENSORS = {
    'DM-PIT01': SensorConfig(
        sensor_id='DM-PIT01',
        data_source='hai',
        sensor_type='pressure',
        range_min=0.0,
        range_max=50.0,
        sampling_rate=1,
        unit='bar'
    ),
    'DM-PIT02': SensorConfig(
        sensor_id='DM-PIT02',
        data_source='hai',
        sensor_type='pressure',
        range_min=0.0,
        range_max=2.0,
        sampling_rate=1,
        unit='bar'
    ),
    'DM-FT01': SensorConfig(
        sensor_id='DM-FT01',
        data_source='hai',
        sensor_type='flow',
        range_min=0.0,
        range_max=500.0,
        sampling_rate=1,
        unit='L/min'
    ),
    'DM-FT02': SensorConfig(
        sensor_id='DM-FT02',
        data_source='hai',
        sensor_type='flow',
        range_min=0.0,
        range_max=5000.0,
        sampling_rate=1,
        unit='L/min'
    ),
    'DM-FT03': SensorConfig(
        sensor_id='DM-FT03',
        data_source='hai',
        sensor_type='flow',
        range_min=0.0,
        range_max=1500.0,
        sampling_rate=1,
        unit='L/min'
    ),
    'DM-TIT01': SensorConfig(
        sensor_id='DM-TIT01',
        data_source='hai',
        sensor_type='temperature',
        range_min=0.0,
        range_max=100.0,
        sampling_rate=1,
        unit='°C'
    ),
    'DM-TIT02': SensorConfig(
        sensor_id='DM-TIT02',
        data_source='hai',
        sensor_type='temperature',
        range_min=0.0,
        range_max=100.0,
        sampling_rate=1,
        unit='°C'
    ),
    'DM-LIT01': SensorConfig(
        sensor_id='DM-LIT01',
        data_source='hai',
        sensor_type='level',
        range_min=0.0,
        range_max=100.0,
        sampling_rate=1,
        unit='%'
    ),
}

# SWaT 센서 정의
SWAT_SENSORS = {
    'LIT101': SensorConfig(
        sensor_id='LIT101',
        data_source='swat',
        sensor_type='level',
        range_min=0.0,
        range_max=1000.0,
        sampling_rate=1,
        unit='mm'
    ),
    'FIT101': SensorConfig(
        sensor_id='FIT101',
        data_source='swat',
        sensor_type='flow',
        range_min=0.0,
        range_max=2.5,
        sampling_rate=1,
        unit='m³/h'
    ),
    'PIT101': SensorConfig(
        sensor_id='PIT101',
        data_source='swat',
        sensor_type='pressure',
        range_min=0.0,
        range_max=10.0,
        sampling_rate=1,
        unit='bar'
    ),
}

# 암호화 알고리즘 설정
CRYPTO_CONFIG = {
    'bulletproofs': {
        'bit_length': 32,
        'curve': 'secp256k1',
        'hash_function': 'sha256'
    },
    'pedersen': {
        'group_order': 2**256 - 1,
        'generator_count': 2
    },
    'hmac': {
        'algorithm': 'sha256',
        'key_length': 32
    },
    'ed25519': {
        'key_length': 32,
        'signature_length': 64
    }
}

# 로깅 설정
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'colored': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
            'level': 'INFO',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'standard',
            'level': 'DEBUG',
            'filename': str(LOGS_DIR / 'experiment.log'),
            'mode': 'a'
        }
    },
    'loggers': {
        '': {  # root logger
            'level': 'INFO',
            'handlers': ['console', 'file']
        },
        'experiment': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    }
}

# 성능 메트릭 설정
METRICS_CONFIG = {
    'measure_cpu': True,
    'measure_memory': True,
    'measure_network': True,
    'sampling_interval': 0.1,  # seconds
    'export_format': ['json', 'csv'],
    'plot_results': True
}

# Apple Silicon 최적화 설정
APPLE_SILICON_OPTIMIZATION = {
    'use_accelerate': True,
    'multiprocessing_method': 'spawn',  # M1/M2/M3에서 안정적
    'worker_count': os.cpu_count() // 2,  # 효율성을 위해 절반 사용
    'chunk_size': 1000
}

# 기본 서버 설정 파일 생성
def create_default_server_config():
    """기본 서버 설정 JSON 파일 생성"""
    config_path = PROJECT_ROOT / "config" / "server_config.json"
    default_config = {
        "host": "localhost",
        "port": 8084,
        "protocol": "http",
        "timeout": 30,
        "retry_count": 3,
        "max_concurrent_requests": 100
    }
    
    if not config_path.exists():
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default server config: {config_path}")
    
    return config_path

# 설정 파일 자동 생성
if __name__ == "__main__":
    create_default_server_config()
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Results directory: {RESULTS_DIR}")
    print(f"Logs directory: {LOGS_DIR}")

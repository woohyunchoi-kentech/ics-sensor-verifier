"""
Ultra Simple Dataset Loader for ICS Sensor Privacy System
HAI 및 SWaT CSV 파일에서 센서 컬럼만 로드
"""

import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import HAI_SENSORS, SWAT_SENSORS, PROJECT_ROOT


def load_hai_data(sensor_id: str = 'P1_PIT01') -> pd.Series:
    """
    HAI CSV 파일에서 센서 데이터 로드
    
    Args:
        sensor_id: 센서 식별자 (기본값: 'P1_PIT01')
        
    Returns:
        센서 값 Series
        
    Raises:
        FileNotFoundError: CSV 파일을 찾을 수 없는 경우
        ValueError: 알 수 없는 센서 ID인 경우
    """
    if sensor_id not in HAI_SENSORS:
        raise ValueError(f"Unknown HAI sensor ID: {sensor_id}")
    
    data_dir = PROJECT_ROOT / "data" / "hai"
    
    # CSV 파일 경로 추정 - 실제 HAI 데이터 경로 포함
    csv_files = [
        data_dir / f"{sensor_id}.csv",
        data_dir / f"hai_{sensor_id}.csv", 
        data_dir / "hai_dataset.csv",
        data_dir / "dataset.csv",
        data_dir / "haiend-23.05" / "end-train1.csv",
        data_dir / "haiend-23.05" / "end-train2.csv",
        data_dir / "haiend-23.05" / "end-train3.csv",
        data_dir / "haiend-23.05" / "end-train4.csv",
        data_dir / "haiend-23.05" / "end-test1.csv",
        data_dir / "haiend-23.05" / "end-test2.csv"
    ]
    
    for csv_file in csv_files:
        if csv_file.exists():
            try:
                print(f"Loading HAI {sensor_id} from {csv_file}")
                df = pd.read_csv(csv_file)
                
                # 센서 컬럼 찾기
                if sensor_id in df.columns:
                    return df[sensor_id]
                    
            except Exception as e:
                print(f"Failed to load {csv_file}: {e}")
                continue
    
    # 파일 없음
    error_msg = f"HAI data file not found for sensor {sensor_id}. Checked paths:\n"
    for csv_file in csv_files:
        error_msg += f"  - {csv_file}\n"
    raise FileNotFoundError(error_msg)


def load_swat_data(sensor_id: str = 'LIT101') -> pd.Series:
    """
    SWaT CSV 파일에서 센서 데이터 로드
    
    Args:
        sensor_id: 센서 식별자 (기본값: 'LIT101')
        
    Returns:
        센서 값 Series
        
    Raises:
        FileNotFoundError: CSV 파일을 찾을 수 없는 경우
        ValueError: 알 수 없는 센서 ID인 경우
    """
    if sensor_id not in SWAT_SENSORS:
        raise ValueError(f"Unknown SWaT sensor ID: {sensor_id}")
    
    data_dir = PROJECT_ROOT / "data" / "swat"
    
    # CSV 파일 경로 추정
    csv_files = [
        data_dir / f"{sensor_id}.csv",
        data_dir / f"swat_{sensor_id}.csv",
        data_dir / "swat_dataset.csv", 
        data_dir / "SWaT_Dataset_Normal_v1.csv",
        data_dir / "SWaT_Dataset_Attack_v0.csv"
    ]
    
    for csv_file in csv_files:
        if csv_file.exists():
            try:
                print(f"Loading SWaT {sensor_id} from {csv_file}")
                df = pd.read_csv(csv_file)
                
                # 센서 컬럼 찾기
                if sensor_id in df.columns:
                    return df[sensor_id]
                    
            except Exception as e:
                print(f"Failed to load {csv_file}: {e}")
                continue
    
    # 파일 없음
    error_msg = f"SWaT data file not found for sensor {sensor_id}. Checked paths:\n"
    for csv_file in csv_files:
        error_msg += f"  - {csv_file}\n"
    raise FileNotFoundError(error_msg)


# 사용 예제
if __name__ == "__main__":
    print("📊 Ultra Simple Dataset Loader Test")
    print("=" * 50)
    
    # HAI 데이터 테스트
    print("\n🔵 HAI Dataset Test")
    hai_sensors = ['P1_PIT01', 'P1_FIT01']  # 2개만 테스트
    
    for sensor_id in hai_sensors:
        try:
            data = load_hai_data(sensor_id)
            print(f"\n  {sensor_id}:")
            print(f"    Samples: {len(data)}")
            print(f"    Range: {data.min():.3f} - {data.max():.3f}")
            print(f"    Mean: {data.mean():.3f}")
            
        except FileNotFoundError:
            print(f"\n  ❌ {sensor_id}: File not found")
        except Exception as e:
            print(f"\n  ❌ {sensor_id}: Error - {e}")
    
    # SWaT 데이터 테스트
    print("\n🟢 SWaT Dataset Test")
    swat_sensors = ['LIT101', 'FIT101']  # 2개만 테스트
    
    for sensor_id in swat_sensors:
        try:
            data = load_swat_data(sensor_id)
            print(f"\n  {sensor_id}:")
            print(f"    Samples: {len(data)}")
            print(f"    Range: {data.min():.3f} - {data.max():.3f}")
            print(f"    Mean: {data.mean():.3f}")
            
        except FileNotFoundError:
            print(f"\n  ❌ {sensor_id}: File not found")
        except Exception as e:
            print(f"\n  ❌ {sensor_id}: Error - {e}")
    
    print("\n✅ Ultra Simple Dataset Loader Test Completed!")

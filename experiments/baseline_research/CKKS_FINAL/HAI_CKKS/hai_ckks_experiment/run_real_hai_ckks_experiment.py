#!/usr/bin/env python3
"""
실제 HAI CKKS 실험 실행기
=======================
완성된 CKKS 코드를 기반으로 실제 서버 연결 실험
"""

import sys
import os
from pathlib import Path

# 상위 디렉토리의 모듈들을 import 가능하게 설정
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.append(str(project_root))

# 데이터 경로 설정을 위한 환경 변수 설정
os.environ['HAI_DATA_PATH'] = str(project_root / "data/hai/haiend-23.05/end-train1.csv")

# 완성된 CKKS 실험 모듈 import
from comprehensive_ckks_performance_experiment import CKKSPerformanceExperiment, ExperimentConfig
import asyncio

async def run_hai_ckks_experiment():
    """HAI CKKS 실험 실행"""
    
    print("🚀 HAI CKKS 실험 시작!")
    print("=" * 50)
    
    # HAI 데이터 경로 확인
    hai_data_path = Path(os.environ['HAI_DATA_PATH'])
    if not hai_data_path.exists():
        print(f"❌ HAI 데이터 파일을 찾을 수 없습니다: {hai_data_path}")
        return
    
    print(f"✅ HAI 데이터 확인: {hai_data_path}")
    
    # 실험 설정 (baseline과 동일한 16개 조건)
    config = ExperimentConfig(
        dataset_name="HAI",
        sensor_counts=[1, 10, 50, 100],
        frequencies=[1, 2, 10, 100],  # Hz
        duration_seconds=10,  # 빠른 테스트를 위해 10초로 설정
        server_url="http://192.168.0.11:8085"
    )
    
    print(f"\n🔧 실험 설정:")
    print(f"  • 센서 수: {config.sensor_counts}")
    print(f"  • 주파수: {config.frequencies} Hz")
    print(f"  • 각 조건당 시간: {config.duration_seconds}초")
    print(f"  • 총 조건 수: {len(config.sensor_counts) * len(config.frequencies)}개")
    print(f"  • 예상 소요 시간: {len(config.sensor_counts) * len(config.frequencies) * config.duration_seconds / 60:.1f}분")
    
    try:
        # 실험 실행
        experiment = CKKSPerformanceExperiment(config)
        await experiment.run_full_experiment()
        
        print("\n🎉 HAI CKKS 실험 완료!")
        print(f"📁 결과 위치: {experiment.results_dir}")
        
    except Exception as e:
        print(f"❌ 실험 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 현재 디렉토리를 프로젝트 루트로 변경
    os.chdir(project_root)
    
    # 실험 실행
    asyncio.run(run_hai_ckks_experiment())
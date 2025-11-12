#!/usr/bin/env python3
"""
자동 외부 서버 WADI HMAC 실험
===========================

사용자 입력 없이 자동으로 실험을 실행하는 버전
"""

import asyncio
from external_server_experiment import ExternalServerExperiment, ExperimentConfig

async def main():
    """자동 외부 서버 실험 메인 함수"""
    print("🌐 WADI HMAC 외부 서버 자동 실험 시작")
    print("=" * 60)
    
    # 실험 설정 - 각 조건당 1000초
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[1, 10, 50, 100],  # 원래 명세
        frequencies=[1, 2, 10, 100],     # 원래 명세 
        duration_seconds=1000,           # 각 조건당 1000초
        server_host="192.168.0.11",     # 외부 서버
        server_port=8085,               # 외부 서버 포트
        results_dir="../results"
    )
    
    print(f"🎯 실험 설정:")
    print(f"  • 대상 서버: {config.server_host}:{config.server_port}")
    print(f"  • 데이터셋: {config.dataset_name}")
    print(f"  • 센서 개수: {config.sensor_counts}")
    print(f"  • 전송 주파수: {config.frequencies} Hz")
    print(f"  • 각 조건 실행 시간: {config.duration_seconds} 초")
    
    total_conditions = len(config.sensor_counts) * len(config.frequencies)
    total_time_seconds = total_conditions * config.duration_seconds
    total_time_minutes = total_time_seconds / 60
    total_time_hours = total_time_minutes / 60
    
    print(f"  • 총 실험 조건: {total_conditions}개")
    print(f"  • 예상 총 실험 시간: {total_time_minutes:.1f} 분 ({total_time_hours:.1f} 시간)")
    
    print("\n🚀 실험을 자동으로 시작합니다...")
    
    # 실험 실행
    experiment = ExternalServerExperiment(config)
    
    try:
        await experiment.run_full_experiment()
        print(f"\n🎉 실험 완료! 결과 저장 위치: {experiment.results_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 실험 중단됨")
        await experiment.cleanup()
        
    except Exception as e:
        print(f"\n❌ 실험 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        await experiment.cleanup()
        raise

if __name__ == "__main__":
    asyncio.run(main())
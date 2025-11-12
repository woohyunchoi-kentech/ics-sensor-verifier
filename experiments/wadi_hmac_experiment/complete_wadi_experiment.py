#!/usr/bin/env python3
"""
완전한 WADI HMAC 실험 실행기
==========================
누락된 11개 조건 모두 실행

원래 계획:
- 센서: 1, 10, 50, 100개
- 주파수: 1, 2, 10, 100Hz  
- 시간: 1000초/조건
- 총: 16개 조건

완료된 조건: 5개
누락된 조건: 11개
"""

import asyncio
from final_wadi_hmac_experiment import WADIHMACExperiment, ExperimentConfig
import time

async def run_complete_wadi_experiment():
    """완전한 WADI HMAC 실험 실행"""
    
    print("🚀 완전한 WADI HMAC 실험 시작")
    print("=" * 60)
    
    # 전체 실험 조건 정의
    all_conditions = [
        # 기존 완료된 조건들 (참고용)
        # (1, 1), (1, 10), (10, 1), (10, 10), (100, 100) - 이미 완료됨
        
        # 누락된 조건들
        (1, 2),    # 1센서, 2Hz
        (1, 100),  # 1센서, 100Hz
        (10, 2),   # 10센서, 2Hz
        (10, 100), # 10센서, 100Hz
        (50, 1),   # 50센서, 1Hz
        (50, 2),   # 50센서, 2Hz
        (50, 10),  # 50센서, 10Hz
        (50, 100), # 50센서, 100Hz
        (100, 1),  # 100센서, 1Hz
        (100, 2),  # 100센서, 2Hz
        (100, 10), # 100센서, 10Hz
    ]
    
    print(f"📊 누락된 실험 조건: {len(all_conditions)}개")
    total_time = len(all_conditions) * 1000 / 60  # 분 단위
    print(f"⏰ 예상 소요 시간: {total_time:.1f}분 ({total_time/60:.1f}시간)")
    print(f"🎯 목표: 모든 조건에서 100% HMAC 검증 성공")
    print()
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[],  # 동적으로 설정
        frequencies=[],    # 동적으로 설정
        duration_seconds=1000,  # 각 조건당 1000초
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/complete_wadi_experiment"
    )
    
    start_time = time.time()
    
    for i, (sensor_count, frequency) in enumerate(all_conditions, 1):
        print(f"\n🔄 조건 {i}/{len(all_conditions)}: {sensor_count}센서, {frequency}Hz")
        print(f"   예상 요청 수: {sensor_count * frequency * 1000:,}개")
        print(f"   진행률: {i/len(all_conditions)*100:.1f}%")
        
        # 각 조건별 설정
        config.sensor_counts = [sensor_count]
        config.frequencies = [frequency]
        
        condition_start = time.time()
        
        try:
            experiment = WADIHMACExperiment(config)
            await experiment.run_full_experiment()
            
            condition_time = time.time() - condition_start
            elapsed_total = time.time() - start_time
            remaining_conditions = len(all_conditions) - i
            estimated_remaining = remaining_conditions * (condition_time / 60)
            
            print(f"   ✅ 조건 완료 ({condition_time/60:.1f}분 소요)")
            print(f"   📈 총 경과 시간: {elapsed_total/60:.1f}분")
            print(f"   ⏳ 예상 남은 시간: {estimated_remaining:.1f}분")
            
        except Exception as e:
            print(f"   ❌ 조건 실패: {str(e)}")
            print(f"   🔄 다음 조건으로 계속 진행...")
            continue
    
    total_elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"🎉 완전한 WADI HMAC 실험 완료!")
    print(f"📊 처리된 조건: {len(all_conditions)}개")
    print(f"⏰ 총 소요 시간: {total_elapsed/3600:.2f}시간")
    print(f"📁 결과 위치: ../results/complete_wadi_experiment")
    print("=" * 60)

async def run_missing_conditions_only():
    """누락된 조건만 빠르게 실행 (각 조건당 100초)"""
    
    print("🚀 누락된 WADI HMAC 조건 빠른 실행")
    print("=" * 50)
    
    # 우선순위가 높은 누락 조건들
    priority_conditions = [
        (50, 1),   # 50센서, 1Hz
        (50, 10),  # 50센서, 10Hz
        (50, 100), # 50센서, 100Hz
        (1, 2),    # 1센서, 2Hz
        (10, 2),   # 10센서, 2Hz
        (100, 2),  # 100센서, 2Hz
    ]
    
    config = ExperimentConfig(
        dataset_name="WADI",
        sensor_counts=[],
        frequencies=[],
        duration_seconds=100,  # 빠른 테스트: 100초
        server_host="192.168.0.11",
        server_port=8085,
        results_dir="../results/missing_conditions_test"
    )
    
    for i, (sensor_count, frequency) in enumerate(priority_conditions, 1):
        print(f"\n🔄 우선 조건 {i}/{len(priority_conditions)}: {sensor_count}센서, {frequency}Hz")
        
        config.sensor_counts = [sensor_count]
        config.frequencies = [frequency]
        
        try:
            experiment = WADIHMACExperiment(config)
            await experiment.run_full_experiment()
            print(f"   ✅ 조건 완료")
            
        except Exception as e:
            print(f"   ❌ 조건 실패: {str(e)}")

if __name__ == "__main__":
    print("WADI HMAC 완전 실험 옵션:")
    print("1. 전체 누락 조건 실행 (1000초/조건, ~3시간)")
    print("2. 우선 조건만 실행 (100초/조건, ~10분)")
    
    choice = input("선택하세요 (1/2): ").strip()
    
    if choice == "1":
        print("\n📍 전체 실험 시작...")
        asyncio.run(run_complete_wadi_experiment())
    elif choice == "2":
        print("\n📍 우선 조건 실험 시작...")
        asyncio.run(run_missing_conditions_only())
    else:
        print("❌ 잘못된 선택입니다.")
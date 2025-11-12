#!/usr/bin/env python3
"""
WADI HMAC 실험 결과 시각화 및 분석
==================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path
import glob

def load_all_data():
    """모든 실험 결과 데이터 로드"""
    results_dir = Path("./results")
    summary_files = glob.glob(str(results_dir / "*" / "*summary.csv"))
    summary_files.extend(glob.glob(str(results_dir / "*summary.csv")))
    
    print(f"Found files: {summary_files}")
    
    all_data = []
    for file in summary_files:
        try:
            df = pd.read_csv(file)
            print(f"✅ Loaded: {file} - {len(df)} rows")
            print(f"   Columns: {list(df.columns)}")
            all_data.append(df)
        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        # 중복 제거 (같은 sensor_count, frequency 조합)
        combined_df = combined_df.drop_duplicates(subset=['sensor_count', 'frequency'])
        print(f"Final combined data: {len(combined_df)} rows")
        return combined_df
    return pd.DataFrame()

def create_comprehensive_visualization():
    """종합적인 HMAC 성능 시각화"""
    
    # 데이터 로드
    df = load_all_data()
    if df.empty:
        print("❌ No data found")
        return
        
    print(f"📊 Total conditions: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # 스타일 설정
    plt.style.use('default')
    sns.set_palette("husl")
    
    # 한글 폰트 설정 (macOS)
    plt.rcParams['font.family'] = 'DejaVu Sans'
    
    # 메인 그림 생성
    fig = plt.figure(figsize=(20, 16))
    
    # 1. HMAC 생성 시간 vs 센서 수/주파수
    ax1 = plt.subplot(3, 3, 1)
    for freq in sorted(df['frequency'].unique()):
        subset = df[df['frequency'] == freq]
        plt.plot(subset['sensor_count'], subset['avg_hmac_generation_ms'], 
                marker='o', linewidth=2, label=f'{freq}Hz')
    plt.xlabel('Sensor Count')
    plt.ylabel('HMAC Generation Time (ms)')
    plt.title('HMAC Generation Performance')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. 네트워크 RTT vs 센서 수/주파수  
    ax2 = plt.subplot(3, 3, 2)
    for freq in sorted(df['frequency'].unique()):
        subset = df[df['frequency'] == freq]
        plt.plot(subset['sensor_count'], subset['avg_network_rtt_ms'], 
                marker='s', linewidth=2, label=f'{freq}Hz')
    plt.xlabel('센서 수')
    plt.ylabel('네트워크 RTT (ms)')
    plt.title('네트워크 지연시간')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 3. 성공률 히트맵
    ax3 = plt.subplot(3, 3, 3)
    pivot_success = df.pivot(index='sensor_count', columns='frequency', values='success_rate')
    sns.heatmap(pivot_success, annot=True, fmt='.1f', cmap='Greens', 
                cbar_kws={'label': '성공률 (%)'})
    plt.title('HMAC 요청 성공률')
    plt.ylabel('센서 수')
    plt.xlabel('주파수 (Hz)')
    
    # 4. 검증률 히트맵
    ax4 = plt.subplot(3, 3, 4)
    pivot_verify = df.pivot(index='sensor_count', columns='frequency', values='verification_rate')
    sns.heatmap(pivot_verify, annot=True, fmt='.1f', cmap='Blues', 
                cbar_kws={'label': '검증률 (%)'})
    plt.title('HMAC 검증 성공률')
    plt.ylabel('센서 수')
    plt.xlabel('주파수 (Hz)')
    
    # 5. 총 요청 수 vs 성능
    ax5 = plt.subplot(3, 3, 5)
    scatter = plt.scatter(df['total_requests'], df['avg_hmac_generation_ms'], 
                         c=df['sensor_count'], s=df['frequency']*10, 
                         alpha=0.7, cmap='viridis')
    plt.xlabel('총 요청 수')
    plt.ylabel('HMAC 생성 시간 (ms)')
    plt.title('요청량 vs 성능 (크기=주파수, 색상=센서수)')
    plt.colorbar(scatter, label='센서 수')
    plt.xscale('log')
    
    # 6. CPU 사용률
    ax6 = plt.subplot(3, 3, 6)
    for freq in sorted(df['frequency'].unique()):
        subset = df[df['frequency'] == freq]
        plt.plot(subset['sensor_count'], subset['avg_cpu_usage'], 
                marker='d', linewidth=2, label=f'{freq}Hz')
    plt.xlabel('센서 수')
    plt.ylabel('평균 CPU 사용률 (%)')
    plt.title('시스템 CPU 부하')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 7. 메모리 사용량
    ax7 = plt.subplot(3, 3, 7)
    for freq in sorted(df['frequency'].unique()):
        subset = df[df['frequency'] == freq]
        plt.plot(subset['sensor_count'], subset['avg_memory_mb'], 
                marker='^', linewidth=2, label=f'{freq}Hz')
    plt.xlabel('센서 수')
    plt.ylabel('메모리 사용량 (MB)')
    plt.title('메모리 리소스 사용량')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 8. 데이터 처리량
    ax8 = plt.subplot(3, 3, 8)
    df['data_rate_mbps'] = (df['total_data_mb'] * 8) / 1000  # 1000초 기준으로 Mbps 계산
    for freq in sorted(df['frequency'].unique()):
        subset = df[df['frequency'] == freq]
        if 'data_rate_mbps' in subset:
            plt.plot(subset['sensor_count'], subset['data_rate_mbps'], 
                    marker='*', linewidth=2, label=f'{freq}Hz')
    plt.xlabel('센서 수')
    plt.ylabel('데이터 처리량 (Mbps)')
    plt.title('네트워크 처리량')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 9. 종합 성능 레이더 차트
    ax9 = plt.subplot(3, 3, 9, projection='polar')
    
    # 최고 성능 조건 찾기 (100센서, 100Hz)
    best_condition = df[(df['sensor_count'] == 100) & (df['frequency'] == 100)]
    if not best_condition.empty:
        metrics = ['HMAC 생성', '검증률', '성공률', 'CPU 효율', '메모리 효율']
        
        # 정규화된 값들 (0-100 스케일)
        hmac_perf = 100 - min(100, best_condition['avg_hmac_generation_ms'].iloc[0] * 1000)
        verify_rate = best_condition['verification_rate'].iloc[0] 
        success_rate = best_condition['success_rate'].iloc[0]
        cpu_eff = 100 - min(100, best_condition['avg_cpu_usage'].iloc[0])
        mem_eff = 100 - min(100, best_condition['avg_memory_mb'].iloc[0] / 100)
        
        values = [hmac_perf, verify_rate, success_rate, cpu_eff, mem_eff]
        values += values[:1]  # 원형으로 연결
        
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]
        
        ax9.plot(angles, values, 'o-', linewidth=2, color='red', alpha=0.8)
        ax9.fill(angles, values, alpha=0.25, color='red')
        ax9.set_xticks(angles[:-1])
        ax9.set_xticklabels(metrics)
        ax9.set_ylim(0, 100)
        ax9.set_title('최종 조건 성능 프로파일\n(100센서, 100Hz)', y=1.1)
    
    plt.tight_layout()
    plt.savefig('./results/wadi_hmac_comprehensive_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('./results/wadi_hmac_comprehensive_analysis.pdf', bbox_inches='tight')
    print("✅ 종합 분석 차트 저장: ./results/wadi_hmac_comprehensive_analysis.png")
    
    return df

def generate_summary_statistics(df):
    """요약 통계 생성"""
    print("\n📊 WADI HMAC 실험 요약 통계")
    print("=" * 50)
    
    print(f"총 실험 조건: {len(df)}개")
    print(f"센서 범위: {df['sensor_count'].min()}-{df['sensor_count'].max()}개")
    print(f"주파수 범위: {df['frequency'].min()}-{df['frequency'].max()}Hz")
    print(f"총 처리 요청: {df['total_requests'].sum():,}개")
    
    print(f"\n🎯 성능 지표:")
    print(f"평균 HMAC 생성 시간: {df['avg_hmac_generation_ms'].mean():.3f}ms")
    print(f"평균 네트워크 RTT: {df['avg_network_rtt_ms'].mean():.2f}ms")
    print(f"전체 성공률: {df['success_rate'].mean():.1f}%")
    print(f"전체 검증률: {df['verification_rate'].mean():.1f}%")
    
    print(f"\n💻 시스템 리소스:")
    print(f"평균 CPU 사용률: {df['avg_cpu_usage'].mean():.2f}%")
    print(f"평균 메모리 사용량: {df['avg_memory_mb'].mean():.1f}MB")
    print(f"총 데이터 처리량: {df['total_data_mb'].sum():.2f}MB")
    
    # 최고 성능 조건
    best_condition = df.loc[df['total_requests'].idxmax()]
    print(f"\n🏆 최고 부하 조건:")
    print(f"센서: {best_condition['sensor_count']}개, 주파수: {best_condition['frequency']}Hz")
    print(f"처리 요청: {best_condition['total_requests']:,}개")
    print(f"HMAC 생성: {best_condition['avg_hmac_generation_ms']:.3f}ms")
    print(f"성공률: {best_condition['success_rate']:.1f}%")

if __name__ == "__main__":
    print("🚀 WADI HMAC 실험 결과 분석 시작")
    
    df = create_comprehensive_visualization()
    if df is not None and not df.empty:
        generate_summary_statistics(df)
        print("\n✅ 분석 완료!")
    else:
        print("❌ 분석할 데이터가 없습니다.")
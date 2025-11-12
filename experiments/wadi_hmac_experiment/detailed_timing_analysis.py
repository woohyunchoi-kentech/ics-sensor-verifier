#!/usr/bin/env python3
"""
WADI HMAC 실험 상세 타이밍 분석
============================
센서별, 주파수별 암호화/전송/복호화/검증 시간 분석
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import glob

def load_timing_data():
    """모든 타이밍 데이터 로드"""
    summary_files = glob.glob("./results/*/*summary.csv")
    summary_files.extend(glob.glob("./results/*summary.csv"))
    
    all_data = []
    for file in summary_files:
        try:
            df = pd.read_csv(file)
            all_data.append(df)
            print(f"✅ Loaded: {file} - {len(df)} rows")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not all_data:
        print("No data found")
        return pd.DataFrame()
        
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['sensor_count', 'frequency'])
    
    # 결측값 처리 및 데이터 정리
    timing_columns = ['avg_hmac_generation_ms', 'avg_hmac_verification_ms', 
                      'avg_network_rtt_ms', 'avg_serialization_ms']
    
    for col in timing_columns:
        if col not in combined_df.columns:
            combined_df[col] = np.nan
            
    return combined_df

def create_detailed_timing_analysis():
    """상세 타이밍 분석 시각화"""
    df = load_timing_data()
    if df.empty:
        return
        
    print(f"📊 분석 데이터: {len(df)}개 조건")
    print(f"가용한 컬럼: {list(df.columns)}")
    
    # 데이터 정리
    df_clean = df.dropna(subset=['avg_hmac_generation_ms'])
    
    plt.style.use('default')
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. 센서별 HMAC 생성 시간 비교
    ax1 = axes[0,0]
    sensor_counts = sorted(df_clean['sensor_count'].unique())
    colors = plt.cm.Set3(np.linspace(0, 1, len(sensor_counts)))
    
    for i, sensor in enumerate(sensor_counts):
        subset = df_clean[df_clean['sensor_count'] == sensor]
        ax1.bar([f"{sensor}s-{freq}Hz" for freq in subset['frequency']], 
               subset['avg_hmac_generation_ms'], 
               color=colors[i], alpha=0.8, label=f'{sensor} sensors')
    
    ax1.set_xlabel('Test Conditions')
    ax1.set_ylabel('HMAC Generation Time (ms)')
    ax1.set_title('HMAC Generation Time by Sensor Count & Frequency')
    ax1.tick_params(axis='x', rotation=45)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 검증 시간 vs 생성 시간 비교
    ax2 = axes[0,1]
    verification_data = df_clean.dropna(subset=['avg_hmac_verification_ms'])
    if not verification_data.empty:
        x_pos = range(len(verification_data))
        width = 0.35
        
        ax2.bar([x - width/2 for x in x_pos], 
               verification_data['avg_hmac_generation_ms'],
               width, label='Generation', color='lightblue', alpha=0.8)
        ax2.bar([x + width/2 for x in x_pos], 
               verification_data['avg_hmac_verification_ms'],
               width, label='Verification', color='lightcoral', alpha=0.8)
        
        labels = [f"{row['sensor_count']}s/{row['frequency']}Hz" 
                 for _, row in verification_data.iterrows()]
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(labels, rotation=45)
        ax2.set_ylabel('Time (ms)')
        ax2.set_title('HMAC Generation vs Verification Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # 3. 네트워크 전송 시간
    ax3 = axes[0,2]
    network_data = df_clean.dropna(subset=['avg_network_rtt_ms'])
    if not network_data.empty:
        frequencies = sorted(network_data['frequency'].unique())
        for freq in frequencies:
            subset = network_data[network_data['frequency'] == freq]
            ax3.plot(subset['sensor_count'], subset['avg_network_rtt_ms'], 
                    marker='o', linewidth=2, label=f'{freq}Hz')
        
        ax3.set_xlabel('Sensor Count')
        ax3.set_ylabel('Network RTT (ms)')
        ax3.set_title('Network Transmission Time')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    
    # 4. 타이밍 구성 요소 스택 차트
    ax4 = axes[1,0]
    timing_components = df_clean.dropna(subset=['avg_hmac_generation_ms'])
    if not timing_components.empty:
        labels = [f"{row['sensor_count']}s/{row['frequency']}Hz" 
                 for _, row in timing_components.iterrows()]
        
        generation_times = timing_components['avg_hmac_generation_ms'].values
        verification_times = timing_components.get('avg_hmac_verification_ms', 
                                                  np.zeros(len(generation_times)))
        network_times = timing_components.get('avg_network_rtt_ms', 
                                            np.zeros(len(generation_times)))
        
        # Replace NaN with 0
        verification_times = np.nan_to_num(verification_times)
        network_times = np.nan_to_num(network_times)
        
        x_pos = range(len(labels))
        ax4.bar(x_pos, generation_times, label='HMAC Generation', 
               color='skyblue', alpha=0.8)
        ax4.bar(x_pos, verification_times, bottom=generation_times,
               label='HMAC Verification', color='lightcoral', alpha=0.8)
        
        ax4.set_xlabel('Test Conditions')
        ax4.set_ylabel('Time (ms)')
        ax4.set_title('Timing Components Breakdown')
        ax4.set_xticks(x_pos)
        ax4.set_xticklabels(labels, rotation=45)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    
    # 5. 주파수별 성능 트렌드
    ax5 = axes[1,1]
    for freq in sorted(df_clean['frequency'].unique()):
        subset = df_clean[df_clean['frequency'] == freq]
        if len(subset) > 1:  # 트렌드를 보려면 최소 2개 점 필요
            ax5.plot(subset['sensor_count'], subset['avg_hmac_generation_ms'], 
                    marker='s', linewidth=2, label=f'{freq}Hz')
    
    ax5.set_xlabel('Sensor Count')
    ax5.set_ylabel('HMAC Generation Time (ms)')
    ax5.set_title('Performance Trend by Frequency')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 6. 전체 처리 시간 vs 네트워크 시간 비교
    ax6 = axes[1,2]
    network_comparison = df_clean.dropna(subset=['avg_network_rtt_ms'])
    if not network_comparison.empty:
        processing_time = network_comparison['avg_hmac_generation_ms']
        network_time = network_comparison['avg_network_rtt_ms']
        
        ax6.scatter(processing_time, network_time, 
                   s=network_comparison['sensor_count']*20, 
                   alpha=0.6, c=network_comparison['frequency'], 
                   cmap='viridis')
        
        # 동등선 그리기
        max_time = max(processing_time.max(), network_time.max())
        ax6.plot([0, max_time], [0, max_time], 'r--', alpha=0.5, 
                label='Equal Time Line')
        
        ax6.set_xlabel('HMAC Generation Time (ms)')
        ax6.set_ylabel('Network RTT (ms)')
        ax6.set_title('Processing vs Network Time\n(Size=Sensors, Color=Frequency)')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        # 컬러바 추가
        cbar = plt.colorbar(ax6.collections[0], ax=ax6)
        cbar.set_label('Frequency (Hz)')
    
    plt.tight_layout()
    plt.savefig('./results/detailed_timing_analysis.png', dpi=300, bbox_inches='tight')
    plt.savefig('./results/detailed_timing_analysis.pdf', bbox_inches='tight')
    print("✅ Detailed timing analysis saved: ./results/detailed_timing_analysis.png")
    
    return df_clean

def generate_timing_report(df):
    """상세 타이밍 분석 리포트 생성"""
    print("\n📊 WADI HMAC 상세 타이밍 분석 리포트")
    print("=" * 50)
    
    # 기본 통계
    print(f"총 테스트 조건: {len(df)}개")
    print(f"센서 범위: {df['sensor_count'].min():.0f} - {df['sensor_count'].max():.0f}개")
    print(f"주파수 범위: {df['frequency'].min():.0f} - {df['frequency'].max():.0f}Hz")
    
    print(f"\n🔐 HMAC 암호화 성능:")
    print(f"평균 생성 시간: {df['avg_hmac_generation_ms'].mean():.4f}ms")
    print(f"최고 성능: {df['avg_hmac_generation_ms'].min():.4f}ms")
    print(f"최저 성능: {df['avg_hmac_generation_ms'].max():.4f}ms")
    print(f"성능 편차: {df['avg_hmac_generation_ms'].std():.4f}ms")
    
    # 검증 시간 분석
    verification_data = df.dropna(subset=['avg_hmac_verification_ms'])
    if not verification_data.empty:
        print(f"\n🔍 HMAC 검증 성능:")
        print(f"평균 검증 시간: {verification_data['avg_hmac_verification_ms'].mean():.4f}ms")
        print(f"최고 성능: {verification_data['avg_hmac_verification_ms'].min():.4f}ms")
        print(f"최저 성능: {verification_data['avg_hmac_verification_ms'].max():.4f}ms")
        
        # 생성 vs 검증 비교
        gen_vs_ver = verification_data['avg_hmac_verification_ms'] / verification_data['avg_hmac_generation_ms']
        print(f"검증/생성 시간 비율: {gen_vs_ver.mean():.2f}x (검증이 생성보다 {gen_vs_ver.mean():.2f}배 오래 걸림)")
    
    # 네트워크 성능 분석
    network_data = df.dropna(subset=['avg_network_rtt_ms'])
    if not network_data.empty:
        print(f"\n🌐 네트워크 전송 성능:")
        print(f"평균 RTT: {network_data['avg_network_rtt_ms'].mean():.2f}ms")
        print(f"최고 성능: {network_data['avg_network_rtt_ms'].min():.2f}ms")
        print(f"최저 성능: {network_data['avg_network_rtt_ms'].max():.2f}ms")
        
        # 암호화 vs 네트워크 비교
        crypto_vs_network = network_data['avg_network_rtt_ms'] / network_data['avg_hmac_generation_ms']
        print(f"네트워크/암호화 시간 비율: {crypto_vs_network.mean():.0f}x (네트워크가 암호화보다 {crypto_vs_network.mean():.0f}배 오래 걸림)")
    
    # 센서별 성능 분석
    print(f"\n📈 센서별 성능 분석:")
    for sensor_count in sorted(df['sensor_count'].unique()):
        subset = df[df['sensor_count'] == sensor_count]
        print(f"  {sensor_count}개 센서:")
        for _, row in subset.iterrows():
            freq = row['frequency']
            gen_time = row['avg_hmac_generation_ms']
            net_time = row.get('avg_network_rtt_ms', 'N/A')
            ver_time = row.get('avg_hmac_verification_ms', 'N/A')
            
            if isinstance(net_time, (int, float)):
                net_time = f"{net_time:.2f}ms"
            if isinstance(ver_time, (int, float)):
                ver_time = f"{ver_time:.4f}ms"
                
            print(f"    {freq}Hz: 생성={gen_time:.4f}ms, 전송={net_time}, 검증={ver_time}")
    
    # 최적 조건 추천
    best_generation = df.loc[df['avg_hmac_generation_ms'].idxmin()]
    print(f"\n🏆 최적 성능 조건:")
    print(f"HMAC 생성 최고 성능: {best_generation['sensor_count']:.0f}개 센서, {best_generation['frequency']:.0f}Hz")
    print(f"생성 시간: {best_generation['avg_hmac_generation_ms']:.4f}ms")
    
    if 'avg_network_rtt_ms' in network_data.columns and not network_data.empty:
        best_network = network_data.loc[network_data['avg_network_rtt_ms'].idxmin()]
        print(f"네트워크 최고 성능: {best_network['sensor_count']:.0f}개 센서, {best_network['frequency']:.0f}Hz")
        print(f"RTT: {best_network['avg_network_rtt_ms']:.2f}ms")

if __name__ == "__main__":
    print("🚀 WADI HMAC 상세 타이밍 분석 시작")
    df = create_detailed_timing_analysis()
    if df is not None and not df.empty:
        generate_timing_report(df)
        print("\n✅ 상세 분석 완료!")
    else:
        print("❌ 분석할 데이터가 없습니다.")
#!/usr/bin/env python3
"""
WADI HMAC 실험 결과 간단 시각화
=============================
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import glob

def create_simple_visualization():
    """간단한 HMAC 성능 시각화"""
    
    # 데이터 로드
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
        return
        
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['sensor_count', 'frequency'])
    
    print(f"Total conditions: {len(combined_df)}")
    
    # English labels for compatibility
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. HMAC Generation Time
    ax1 = axes[0,0]
    for freq in sorted(combined_df['frequency'].unique()):
        subset = combined_df[combined_df['frequency'] == freq]
        ax1.plot(subset['sensor_count'], subset['avg_hmac_generation_ms'], 
                marker='o', linewidth=2, label=f'{freq}Hz')
    ax1.set_xlabel('Sensor Count')
    ax1.set_ylabel('HMAC Generation Time (ms)')
    ax1.set_title('HMAC Generation Performance')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Success Rate (if available)
    ax2 = axes[0,1]
    if 'success_rate' in combined_df.columns:
        success_data = combined_df.dropna(subset=['success_rate'])
        if not success_data.empty:
            bars = ax2.bar(range(len(success_data)), success_data['success_rate'], 
                          color='green', alpha=0.7)
            ax2.set_xlabel('Test Conditions')
            ax2.set_ylabel('Success Rate (%)')
            ax2.set_title('HMAC Request Success Rate')
            ax2.set_ylim([95, 105])
            
            # Add labels
            labels = [f"{row['sensor_count']}s/{row['frequency']}Hz" 
                     for _, row in success_data.iterrows()]
            ax2.set_xticks(range(len(labels)))
            ax2.set_xticklabels(labels, rotation=45)
    
    # 3. CPU Usage
    ax3 = axes[1,0]
    for freq in sorted(combined_df['frequency'].unique()):
        subset = combined_df[combined_df['frequency'] == freq]
        ax3.plot(subset['sensor_count'], subset['avg_cpu_usage'], 
                marker='s', linewidth=2, label=f'{freq}Hz')
    ax3.set_xlabel('Sensor Count')
    ax3.set_ylabel('CPU Usage (%)')
    ax3.set_title('System CPU Load')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Memory Usage
    ax4 = axes[1,1]
    for freq in sorted(combined_df['frequency'].unique()):
        subset = combined_df[combined_df['frequency'] == freq]
        ax4.plot(subset['sensor_count'], subset['avg_memory_mb'], 
                marker='^', linewidth=2, label=f'{freq}Hz')
    ax4.set_xlabel('Sensor Count')
    ax4.set_ylabel('Memory Usage (MB)')
    ax4.set_title('Memory Resource Usage')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('./results/wadi_hmac_simple_analysis.png', dpi=300, bbox_inches='tight')
    print("✅ Chart saved: ./results/wadi_hmac_simple_analysis.png")
    
    return combined_df

def generate_statistics(df):
    """통계 생성"""
    print("\n📊 WADI HMAC Experiment Summary")
    print("=" * 40)
    
    print(f"Total test conditions: {len(df)}")
    print(f"Sensor range: {df['sensor_count'].min()}-{df['sensor_count'].max()}")
    print(f"Frequency range: {df['frequency'].min()}-{df['frequency'].max()}Hz")
    
    if 'total_requests' in df.columns:
        total_reqs = df['total_requests'].sum()
        print(f"Total requests processed: {total_reqs:,}")
    
    print(f"\nPerformance metrics:")
    print(f"Avg HMAC generation time: {df['avg_hmac_generation_ms'].mean():.3f}ms")
    print(f"Avg CPU usage: {df['avg_cpu_usage'].mean():.2f}%")
    print(f"Avg memory usage: {df['avg_memory_mb'].mean():.1f}MB")
    
    if 'success_rate' in df.columns:
        success_data = df.dropna(subset=['success_rate'])
        if not success_data.empty:
            print(f"Overall success rate: {success_data['success_rate'].mean():.1f}%")
    
    # Find best performance condition
    best_condition = df.loc[df['avg_hmac_generation_ms'].idxmin()]
    print(f"\n🏆 Best performance condition:")
    print(f"Sensors: {best_condition['sensor_count']}, Frequency: {best_condition['frequency']}Hz")
    print(f"HMAC generation: {best_condition['avg_hmac_generation_ms']:.3f}ms")

if __name__ == "__main__":
    print("🚀 WADI HMAC Results Analysis")
    df = create_simple_visualization()
    if df is not None and not df.empty:
        generate_statistics(df)
        print("\n✅ Analysis complete!")
    else:
        print("❌ No data to analyze")
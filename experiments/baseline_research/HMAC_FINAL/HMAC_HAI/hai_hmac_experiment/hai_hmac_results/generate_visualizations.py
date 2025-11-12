#!/usr/bin/env python3
"""
HAI HMAC 실험 결과 시각화 생성
================================
영어/한국어 버전 차트 생성
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# 한국어 폰트 설정
plt.rcParams['font.family'] = ['Arial Unicode MS', 'Malgun Gothic', 'AppleGothic', 'Noto Sans CJK KR']
plt.rcParams['axes.unicode_minus'] = False

def load_data():
    """HAI HMAC 실험 데이터 로드"""
    df = pd.read_csv('final_hai_hmac_20250901_135951.csv')
    return df

def create_success_rate_chart(df, lang='en'):
    """성공률 차트 생성"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 센서 수별로 그룹화
    sensor_groups = df.groupby('sensor_count')
    
    x_pos = np.arange(len(df))
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    bars = ax.bar(x_pos, df['success_rate'], color=[colors[i//4] for i in range(len(df))])
    
    # 라벨 설정
    if lang == 'en':
        ax.set_title('HAI HMAC Authentication Success Rate by Configuration', fontsize=16, fontweight='bold')
        ax.set_xlabel('Test Configuration (Sensors × Frequency)', fontsize=12)
        ax.set_ylabel('Success Rate (%)', fontsize=12)
        legend_labels = ['1 Sensor', '10 Sensors', '50 Sensors', '100 Sensors']
    else:
        ax.set_title('HAI HMAC 인증 성공률 - 조건별 분석', fontsize=16, fontweight='bold')
        ax.set_xlabel('실험 조건 (센서 수 × 주파수)', fontsize=12)
        ax.set_ylabel('성공률 (%)', fontsize=12)
        legend_labels = ['1개 센서', '10개 센서', '50개 센서', '100개 센서']
    
    # X축 라벨
    x_labels = [f"{row['sensor_count']}×{row['frequency']}Hz" for _, row in df.iterrows()]
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    
    # 범례
    legend_elements = [plt.Rectangle((0,0),1,1, color=colors[i], label=legend_labels[i]) 
                      for i in range(4)]
    ax.legend(handles=legend_elements, loc='lower right')
    
    # 값 표시
    for bar, value in zip(bars, df['success_rate']):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5, f'{value:.1f}%',
                ha='center', va='bottom', fontsize=9)
    
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    filename = f'success_rate_{"en" if lang == "en" else "ko"}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 성공률 차트 생성: {filename}")

def create_rtt_analysis_chart(df, lang='en'):
    """RTT 분석 차트 생성"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # RTT vs 센서 수
    sensor_counts = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]
    
    for freq in frequencies:
        freq_data = df[df['frequency'] == freq]
        ax1.plot(freq_data['sensor_count'], freq_data['avg_rtt_ms'], 
                marker='o', linewidth=2, label=f'{freq}Hz')
    
    if lang == 'en':
        ax1.set_title('RTT vs Number of Sensors', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Number of Sensors', fontsize=12)
        ax1.set_ylabel('Average RTT (ms)', fontsize=12)
    else:
        ax1.set_title('RTT vs 센서 수', fontsize=14, fontweight='bold')
        ax1.set_xlabel('센서 수', fontsize=12)
        ax1.set_ylabel('평균 RTT (ms)', fontsize=12)
    
    ax1.set_xscale('log')
    ax1.set_xticks(sensor_counts)
    ax1.set_xticklabels(sensor_counts)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # RTT vs 주파수
    for sensors in sensor_counts:
        sensor_data = df[df['sensor_count'] == sensors]
        ax2.plot(sensor_data['frequency'], sensor_data['avg_rtt_ms'], 
                marker='s', linewidth=2, label=f'{sensors} sensors')
    
    if lang == 'en':
        ax2.set_title('RTT vs Frequency', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Frequency (Hz)', fontsize=12)
        ax2.set_ylabel('Average RTT (ms)', fontsize=12)
    else:
        ax2.set_title('RTT vs 주파수', fontsize=14, fontweight='bold')
        ax2.set_xlabel('주파수 (Hz)', fontsize=12)
        ax2.set_ylabel('평균 RTT (ms)', fontsize=12)
    
    ax2.set_xscale('log')
    ax2.set_xticks(frequencies)
    ax2.set_xticklabels(frequencies)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filename = f'rtt_analysis_{"en" if lang == "en" else "ko"}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ RTT 분석 차트 생성: {filename}")

def create_rps_heatmap(df, lang='en'):
    """RPS 히트맵 생성"""
    # 피벗 테이블 생성
    pivot_data = df.pivot(index='sensor_count', columns='frequency', values='actual_rps')
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 히트맵 생성
    im = ax.imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
    
    # 축 설정
    ax.set_xticks(np.arange(len(pivot_data.columns)))
    ax.set_yticks(np.arange(len(pivot_data.index)))
    ax.set_xticklabels([f'{f}Hz' for f in pivot_data.columns])
    ax.set_yticklabels([f'{s}' for s in pivot_data.index])
    
    if lang == 'en':
        ax.set_title('Requests Per Second (RPS) Heatmap', fontsize=16, fontweight='bold')
        ax.set_xlabel('Frequency', fontsize=12)
        ax.set_ylabel('Number of Sensors', fontsize=12)
    else:
        ax.set_title('초당 요청 처리량(RPS) 히트맵', fontsize=16, fontweight='bold')
        ax.set_xlabel('주파수', fontsize=12)
        ax.set_ylabel('센서 수', fontsize=12)
    
    # 값 표시
    for i in range(len(pivot_data.index)):
        for j in range(len(pivot_data.columns)):
            value = pivot_data.iloc[i, j]
            ax.text(j, i, f'{value:.1f}', ha='center', va='center',
                   color='white' if value > pivot_data.values.max() * 0.5 else 'black',
                   fontweight='bold')
    
    # 컬러바
    cbar = plt.colorbar(im)
    cbar.set_label('RPS', fontsize=12)
    
    plt.tight_layout()
    filename = f'rps_heatmap_{"en" if lang == "en" else "ko"}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ RPS 히트맵 생성: {filename}")

def create_performance_summary(df, lang='en'):
    """성능 요약 차트 생성"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 성공률 분포
    success_counts = df['success_rate'].value_counts().sort_index()
    ax1.bar(range(len(success_counts)), success_counts.values, color='#2E86AB')
    ax1.set_xticks(range(len(success_counts)))
    ax1.set_xticklabels([f'{x}%' for x in success_counts.index])
    
    if lang == 'en':
        ax1.set_title('Success Rate Distribution', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Success Rate (%)')
        ax1.set_ylabel('Number of Conditions')
    else:
        ax1.set_title('성공률 분포', fontsize=14, fontweight='bold')
        ax1.set_xlabel('성공률 (%)')
        ax1.set_ylabel('조건 수')
    
    # 2. RTT 박스플롯
    sensor_groups = [df[df['sensor_count'] == sc]['avg_rtt_ms'].values for sc in [1, 10, 50, 100]]
    ax2.boxplot(sensor_groups, labels=['1', '10', '50', '100'])
    
    if lang == 'en':
        ax2.set_title('RTT Distribution by Sensor Count', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Number of Sensors')
        ax2.set_ylabel('RTT (ms)')
    else:
        ax2.set_title('센서 수별 RTT 분포', fontsize=14, fontweight='bold')
        ax2.set_xlabel('센서 수')
        ax2.set_ylabel('RTT (ms)')
    
    # 3. RPS vs 주파수
    ax3.scatter(df['frequency'], df['actual_rps'], 
               c=[['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][i//4] for i in range(len(df))],
               s=100, alpha=0.7)
    ax3.set_xscale('log')
    
    if lang == 'en':
        ax3.set_title('RPS vs Frequency', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Frequency (Hz)')
        ax3.set_ylabel('RPS')
    else:
        ax3.set_title('RPS vs 주파수', fontsize=14, fontweight='bold')
        ax3.set_xlabel('주파수 (Hz)')
        ax3.set_ylabel('RPS')
    
    # 4. 실험 시간 분포
    ax4.bar(range(len(df)), df['duration_seconds'], 
           color=[['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][i//4] for i in range(len(df))])
    ax4.set_yscale('log')
    
    if lang == 'en':
        ax4.set_title('Experiment Duration by Condition', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Condition Number')
        ax4.set_ylabel('Duration (seconds)')
    else:
        ax4.set_title('조건별 실험 시간', fontsize=14, fontweight='bold')
        ax4.set_xlabel('조건 번호')
        ax4.set_ylabel('실험 시간 (초)')
    
    for ax in [ax1, ax2, ax3, ax4]:
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filename = f'performance_summary_{"en" if lang == "en" else "ko"}.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 성능 요약 차트 생성: {filename}")

def main():
    """메인 함수"""
    print("🎨 HAI HMAC 실험 결과 시각화 생성")
    print("=" * 50)
    
    # 데이터 로드
    df = load_data()
    print(f"📊 데이터 로드 완료: {len(df)}개 조건")
    
    # 영어 버전 차트 생성
    print("\n🇺🇸 영어 버전 차트 생성 중...")
    create_success_rate_chart(df, 'en')
    create_rtt_analysis_chart(df, 'en')
    create_rps_heatmap(df, 'en')
    create_performance_summary(df, 'en')
    
    # 한국어 버전 차트 생성
    print("\n🇰🇷 한국어 버전 차트 생성 중...")
    create_success_rate_chart(df, 'ko')
    create_rtt_analysis_chart(df, 'ko')
    create_rps_heatmap(df, 'ko')
    create_performance_summary(df, 'ko')
    
    print("\n🎉 HAI HMAC 시각화 완료!")
    print("📁 생성된 파일:")
    chart_files = [
        "success_rate_en.png", "success_rate_ko.png",
        "rtt_analysis_en.png", "rtt_analysis_ko.png", 
        "rps_heatmap_en.png", "rps_heatmap_ko.png",
        "performance_summary_en.png", "performance_summary_ko.png"
    ]
    for file in chart_files:
        print(f"   • {file}")

if __name__ == "__main__":
    main()
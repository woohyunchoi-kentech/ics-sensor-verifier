#!/usr/bin/env python3
"""
WADI CKKS 실험 결과 시각화 생성 스크립트
HAI CKKS와 동일한 구조로 WADI 결과를 분석하고 시각화합니다.
실험 데이터: ckks_perf_wadi_20250828_125554 (20,343 requests, 16 conditions)
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 경로 설정
BASE_DIR = Path("/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy")
WADI_RESULTS_DIR = BASE_DIR / "experiment_results/ckks_perf_wadi_20250828_125554"
OUTPUT_DIR = Path(__file__).parent

def load_wadi_data():
    """WADI CKKS 실험 데이터 로드"""
    print("Loading WADI CKKS experiment data...")
    
    # 완전한 성능 데이터 로드
    perf_data = pd.read_csv(WADI_RESULTS_DIR / "complete_performance_data.csv")
    
    # 실험 요약 로드
    with open(WADI_RESULTS_DIR / "experiment_summary.json", 'r') as f:
        summary = json.load(f)
    
    print(f"Loaded {len(perf_data)} performance records")
    print(f"Sensor counts: {summary['sensor_counts_tested']}")
    print(f"Frequencies: {summary['frequencies_tested']}")
    
    return perf_data, summary

def analyze_by_condition(perf_data):
    """16개 조건별로 데이터 분석"""
    conditions = []
    
    sensor_counts = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]
    
    for sensors in sensor_counts:
        for freq in frequencies:
            condition_data = perf_data[
                (perf_data['sensor_count'] == sensors) & 
                (perf_data['frequency'] == freq)
            ]
            
            if len(condition_data) > 0:
                condition = {
                    'sensor_count': sensors,
                    'frequency': freq,
                    'total_requests': len(condition_data),
                    'success_rate': (condition_data['success'] == True).mean() * 100,
                    'avg_encryption_time': condition_data['encryption_time_ms'].mean(),
                    'avg_decryption_time': condition_data['decryption_time_ms'].mean(),
                    'avg_network_rtt': condition_data['network_rtt_ms'].mean(),
                    'avg_accuracy_error': condition_data['accuracy_error'].mean(),
                    'std_encryption_time': condition_data['encryption_time_ms'].std(),
                    'std_decryption_time': condition_data['decryption_time_ms'].std(),
                }
                conditions.append(condition)
                
                print(f"Condition {sensors} sensors @ {freq}Hz: {len(condition_data)} requests, {condition['success_rate']:.1f}% success")
    
    return pd.DataFrame(conditions)

def create_comprehensive_dashboard():
    """HAI CKKS와 동일한 구조의 종합 대시보드 생성"""
    perf_data, summary = load_wadi_data()
    conditions_df = analyze_by_condition(perf_data)
    
    # 대시보드 생성
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('WADI CKKS Performance Analysis - Comprehensive Dashboard', fontsize=16, fontweight='bold')
    
    # 1. 암호화 시간 히트맵
    heatmap_data = conditions_df.pivot(index='sensor_count', columns='frequency', values='avg_encryption_time')
    sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='YlOrRd', ax=axes[0,0])
    axes[0,0].set_title('Average Encryption Time (ms)')
    axes[0,0].set_xlabel('Frequency (Hz)')
    axes[0,0].set_ylabel('Sensor Count')
    
    # 2. 복호화 시간 히트맵  
    heatmap_data = conditions_df.pivot(index='sensor_count', columns='frequency', values='avg_decryption_time')
    sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='Blues', ax=axes[0,1])
    axes[0,1].set_title('Average Decryption Time (ms)')
    axes[0,1].set_xlabel('Frequency (Hz)')
    axes[0,1].set_ylabel('Sensor Count')
    
    # 3. 네트워크 RTT 히트맵
    heatmap_data = conditions_df.pivot(index='sensor_count', columns='frequency', values='avg_network_rtt')
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='Greens', ax=axes[0,2])
    axes[0,2].set_title('Average Network RTT (ms)')
    axes[0,2].set_xlabel('Frequency (Hz)')
    axes[0,2].set_ylabel('Sensor Count')
    
    # 4. 센서 수별 성능 비교
    for freq in [1, 2, 10, 100]:
        freq_data = conditions_df[conditions_df['frequency'] == freq]
        axes[1,0].plot(freq_data['sensor_count'], freq_data['avg_encryption_time'], 
                      marker='o', label=f'{freq}Hz')
    axes[1,0].set_xlabel('Sensor Count')
    axes[1,0].set_ylabel('Encryption Time (ms)')
    axes[1,0].set_title('Encryption Time vs Sensor Count')
    axes[1,0].legend()
    axes[1,0].set_xscale('log')
    
    # 5. 주파수별 성능 비교
    for sensors in [1, 10, 50, 100]:
        sensor_data = conditions_df[conditions_df['sensor_count'] == sensors]
        axes[1,1].plot(sensor_data['frequency'], sensor_data['avg_encryption_time'], 
                      marker='s', label=f'{sensors} sensors')
    axes[1,1].set_xlabel('Frequency (Hz)')
    axes[1,1].set_ylabel('Encryption Time (ms)')
    axes[1,1].set_title('Encryption Time vs Frequency')
    axes[1,1].legend()
    axes[1,1].set_xscale('log')
    
    # 6. 정확도 오차 분석
    heatmap_data = conditions_df.pivot(index='sensor_count', columns='frequency', values='avg_accuracy_error')
    sns.heatmap(heatmap_data, annot=True, fmt='.2e', cmap='Reds', ax=axes[1,2])
    axes[1,2].set_title('Average Accuracy Error')
    axes[1,2].set_xlabel('Frequency (Hz)')
    axes[1,2].set_ylabel('Sensor Count')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'wadi_ckks_comprehensive_dashboard.png', dpi=300, bbox_inches='tight')
    print("✓ Comprehensive dashboard saved")
    
    return conditions_df

def create_performance_comparison():
    """성능 비교 차트 생성"""
    perf_data, summary = load_wadi_data()
    conditions_df = analyze_by_condition(perf_data)
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('WADI CKKS Performance Detailed Analysis', fontsize=16, fontweight='bold')
    
    # 1. 암호화 vs 복호화 시간
    axes[0,0].scatter(conditions_df['avg_encryption_time'], conditions_df['avg_decryption_time'], 
                     s=100, alpha=0.7, c=conditions_df['sensor_count'], cmap='viridis')
    axes[0,0].set_xlabel('Encryption Time (ms)')
    axes[0,0].set_ylabel('Decryption Time (ms)')
    axes[0,0].set_title('Encryption vs Decryption Time')
    
    # 2. 처리량 분석 (RPS)
    conditions_df['theoretical_rps'] = conditions_df['frequency'] * conditions_df['sensor_count']
    conditions_df['actual_rps'] = 1000 / conditions_df['avg_encryption_time']
    
    axes[0,1].scatter(conditions_df['theoretical_rps'], conditions_df['actual_rps'], 
                     s=100, alpha=0.7, c=conditions_df['frequency'], cmap='plasma')
    axes[0,1].plot([0, conditions_df['theoretical_rps'].max()], 
                   [0, conditions_df['theoretical_rps'].max()], 'r--', alpha=0.5, label='1:1 line')
    axes[0,1].set_xlabel('Theoretical RPS')
    axes[0,1].set_ylabel('Actual RPS')
    axes[0,1].set_title('Theoretical vs Actual RPS')
    axes[0,1].legend()
    
    # 3. 효율성 분석
    conditions_df['efficiency'] = conditions_df['actual_rps'] / conditions_df['theoretical_rps'] * 100
    
    pivot_eff = conditions_df.pivot(index='sensor_count', columns='frequency', values='efficiency')
    sns.heatmap(pivot_eff, annot=True, fmt='.1f', cmap='RdYlGn', ax=axes[1,0])
    axes[1,0].set_title('Processing Efficiency (%)')
    axes[1,0].set_xlabel('Frequency (Hz)')
    axes[1,0].set_ylabel('Sensor Count')
    
    # 4. 네트워크 vs 계산 시간
    conditions_df['compute_time'] = conditions_df['avg_encryption_time'] + conditions_df['avg_decryption_time']
    
    axes[1,1].scatter(conditions_df['compute_time'], conditions_df['avg_network_rtt'], 
                     s=100, alpha=0.7, c=conditions_df['sensor_count'], cmap='coolwarm')
    axes[1,1].set_xlabel('Compute Time (ms)')
    axes[1,1].set_ylabel('Network RTT (ms)')
    axes[1,1].set_title('Compute vs Network Time')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'wadi_ckks_performance_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Performance comparison chart saved")

def create_detailed_analysis():
    """상세 분석 차트 생성"""
    perf_data, summary = load_wadi_data()
    conditions_df = analyze_by_condition(perf_data)
    
    fig, axes = plt.subplots(3, 2, figsize=(15, 18))
    fig.suptitle('WADI CKKS Detailed Performance Analysis', fontsize=16, fontweight='bold')
    
    # 1. 센서별 암호화 시간 박스플롯
    sensor_data = []
    sensor_labels = []
    for sensors in [1, 10, 50, 100]:
        data = perf_data[perf_data['sensor_count'] == sensors]['encryption_time_ms']
        if len(data) > 0:
            sensor_data.append(data)
            sensor_labels.append(f'{sensors} sensors')
    
    axes[0,0].boxplot(sensor_data, labels=sensor_labels)
    axes[0,0].set_title('Encryption Time Distribution by Sensor Count')
    axes[0,0].set_ylabel('Encryption Time (ms)')
    axes[0,0].tick_params(axis='x', rotation=45)
    
    # 2. 주파수별 암호화 시간 박스플롯
    freq_data = []
    freq_labels = []
    for freq in [1, 2, 10, 100]:
        data = perf_data[perf_data['frequency'] == freq]['encryption_time_ms']
        if len(data) > 0:
            freq_data.append(data)
            freq_labels.append(f'{freq}Hz')
    
    axes[0,1].boxplot(freq_data, labels=freq_labels)
    axes[0,1].set_title('Encryption Time Distribution by Frequency')
    axes[0,1].set_ylabel('Encryption Time (ms)')
    
    # 3. 시간별 성능 추이 (샘플링)
    sample_data = perf_data.sample(min(1000, len(perf_data))).sort_values('timestamp')
    axes[1,0].plot(range(len(sample_data)), sample_data['encryption_time_ms'], alpha=0.7)
    axes[1,0].set_title('Encryption Time Over Experiment Duration (Sample)')
    axes[1,0].set_xlabel('Request Order')
    axes[1,0].set_ylabel('Encryption Time (ms)')
    
    # 4. 정확도 오차 분포
    axes[1,1].hist(perf_data['accuracy_error'], bins=50, alpha=0.7, edgecolor='black')
    axes[1,1].set_title('Accuracy Error Distribution')
    axes[1,1].set_xlabel('Accuracy Error')
    axes[1,1].set_ylabel('Frequency')
    axes[1,1].set_yscale('log')
    
    # 5. 성능 상관관계 히트맵
    corr_data = conditions_df[['sensor_count', 'frequency', 'avg_encryption_time', 
                              'avg_decryption_time', 'avg_network_rtt', 'avg_accuracy_error']].corr()
    sns.heatmap(corr_data, annot=True, fmt='.3f', cmap='coolwarm', center=0, ax=axes[2,0])
    axes[2,0].set_title('Performance Metrics Correlation')
    
    # 6. 처리량 한계 분석
    conditions_df['total_rps'] = conditions_df['frequency'] * conditions_df['sensor_count']
    conditions_df['bottleneck_ratio'] = conditions_df['avg_encryption_time'] / 1000 * conditions_df['total_rps']
    
    scatter = axes[2,1].scatter(conditions_df['total_rps'], conditions_df['bottleneck_ratio'], 
                               s=100, alpha=0.7, c=conditions_df['sensor_count'], cmap='viridis')
    axes[2,1].axhline(y=1, color='r', linestyle='--', alpha=0.7, label='100% Utilization')
    axes[2,1].set_xlabel('Total RPS Required')
    axes[2,1].set_ylabel('System Utilization Ratio')
    axes[2,1].set_title('System Bottleneck Analysis')
    axes[2,1].legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'wadi_ckks_detailed_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Detailed analysis chart saved")

def create_experiment_summary():
    """실험 요약 정보 생성"""
    perf_data, summary = load_wadi_data()
    conditions_df = analyze_by_condition(perf_data)
    
    # CSV 형태로 요약 데이터 저장
    summary_data = conditions_df.copy()
    summary_data['dataset'] = 'WADI'
    summary_data['experiment_id'] = 'ckks_perf_wadi_20250828_125554'
    
    summary_data.to_csv(OUTPUT_DIR / 'wadi_ckks_experiment_data.csv', index=False)
    print("✓ Experiment data CSV saved")
    
    # 실험 요약 차트
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # 조건별 성능 요약
    x_pos = np.arange(len(conditions_df))
    condition_labels = [f"{row['sensor_count']}s@{row['frequency']}Hz" 
                       for _, row in conditions_df.iterrows()]
    
    bars = ax.bar(x_pos, conditions_df['avg_encryption_time'], 
                  color=plt.cm.viridis(conditions_df['sensor_count']/100), alpha=0.8)
    
    ax.set_xlabel('Experiment Condition')
    ax.set_ylabel('Average Encryption Time (ms)')
    ax.set_title('WADI CKKS Experiment Summary - All 16 Conditions\n' + 
                f'Total Requests: {summary["total_tests"]:,} | Success Rate: {summary["success_rate"]:.2f}%')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(condition_labels, rotation=45, ha='right')
    
    # 수치 표시
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{height:.1f}ms', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'wadi_ckks_experiment_summary.png', dpi=300, bbox_inches='tight')
    print("✓ Experiment summary chart saved")

def main():
    """메인 실행 함수"""
    print("🚀 Starting WADI CKKS Visualization Generation")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    
    # 출력 디렉토리 생성
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    try:
        # 모든 시각화 생성
        print("\n📊 Creating comprehensive dashboard...")
        conditions_df = create_comprehensive_dashboard()
        
        print("\n📈 Creating performance comparison...")
        create_performance_comparison()
        
        print("\n🔍 Creating detailed analysis...")
        create_detailed_analysis()
        
        print("\n📋 Creating experiment summary...")
        create_experiment_summary()
        
        print(f"\n✅ All WADI CKKS visualizations completed!")
        print(f"📈 Generated {len(conditions_df)} condition analyses")
        print(f"📁 Files saved to: {OUTPUT_DIR}")
        
        # 생성된 파일 목록 출력
        generated_files = list(OUTPUT_DIR.glob('wadi_ckks_*.png')) + list(OUTPUT_DIR.glob('wadi_ckks_*.csv'))
        for file in generated_files:
            print(f"   📄 {file.name}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
WADI ED25519 실험 결과 시각화
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 스타일 설정
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (15, 10)

# 데이터 로드
with open('wadi_ed25519_final_20250902_191413.json', 'r') as f:
    data = json.load(f)

# 데이터 준비
conditions = []
for cond in data['condition_results']:
    conditions.append({
        'sensors': cond['sensor_count'],
        'frequency': cond['frequency'],
        'success_rate': cond['server_success_rate'],
        'verification_rate': cond['verification_success_rate'],
        'avg_total_time': cond['avg_total_time_ms'],
        'avg_transmission': cond['avg_transmission_time_ms'],
        'avg_crypto': cond['avg_crypto_time_ms'],
        'avg_verification': cond['avg_verification_time_ms'],
        'throughput': cond['actual_throughput_requests_per_second'],
        'processed': cond['actual_processed']
    })

df = pd.DataFrame(conditions)

# Figure 1: 성능 히트맵
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 1-1: 평균 총 처리 시간 히트맵
pivot_time = df.pivot_table(values='avg_total_time', 
                            index='sensors', 
                            columns='frequency')
sns.heatmap(pivot_time, annot=True, fmt='.1f', cmap='YlOrRd', 
            ax=axes[0,0], cbar_kws={'label': 'Time (ms)'})
axes[0,0].set_title('Average Total Processing Time (ms)', fontsize=14, fontweight='bold')
axes[0,0].set_xlabel('Frequency (Hz)')
axes[0,0].set_ylabel('Number of Sensors')

# 1-2: 성공률 히트맵
pivot_success = df.pivot_table(values='success_rate', 
                               index='sensors', 
                               columns='frequency')
sns.heatmap(pivot_success, annot=True, fmt='.1f', cmap='RdYlGn', 
            ax=axes[0,1], vmin=95, vmax=100, cbar_kws={'label': 'Success Rate (%)'})
axes[0,1].set_title('Server Success Rate (%)', fontsize=14, fontweight='bold')
axes[0,1].set_xlabel('Frequency (Hz)')
axes[0,1].set_ylabel('Number of Sensors')

# 1-3: 처리량 히트맵
pivot_throughput = df.pivot_table(values='throughput', 
                                  index='sensors', 
                                  columns='frequency')
sns.heatmap(pivot_throughput, annot=True, fmt='.2f', cmap='viridis', 
            ax=axes[1,0], cbar_kws={'label': 'Throughput (req/s)'})
axes[1,0].set_title('Actual Throughput (requests/second)', fontsize=14, fontweight='bold')
axes[1,0].set_xlabel('Frequency (Hz)')
axes[1,0].set_ylabel('Number of Sensors')

# 1-4: 전송 시간 히트맵
pivot_trans = df.pivot_table(values='avg_transmission', 
                             index='sensors', 
                             columns='frequency')
sns.heatmap(pivot_trans, annot=True, fmt='.1f', cmap='coolwarm', 
            ax=axes[1,1], cbar_kws={'label': 'Time (ms)'})
axes[1,1].set_title('Average Transmission Time (ms)', fontsize=14, fontweight='bold')
axes[1,1].set_xlabel('Frequency (Hz)')
axes[1,1].set_ylabel('Number of Sensors')

plt.suptitle('WADI ED25519 Performance Heatmaps', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('wadi_ed25519_heatmaps.png', dpi=300, bbox_inches='tight')
plt.show()

# Figure 2: 시간 분석
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 2-1: 센서별 시간 분포
sensor_groups = df.groupby('sensors')[['avg_crypto', 'avg_transmission', 'avg_verification']].mean()
sensor_groups.plot(kind='bar', stacked=True, ax=axes[0,0], 
                   color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
axes[0,0].set_title('Time Breakdown by Sensor Count', fontsize=14, fontweight='bold')
axes[0,0].set_xlabel('Number of Sensors')
axes[0,0].set_ylabel('Time (ms)')
axes[0,0].legend(['Crypto', 'Transmission', 'Verification'])
axes[0,0].set_xticklabels(axes[0,0].get_xticklabels(), rotation=0)

# 2-2: 주파수별 시간 분포
freq_groups = df.groupby('frequency')[['avg_crypto', 'avg_transmission', 'avg_verification']].mean()
freq_groups.plot(kind='bar', stacked=True, ax=axes[0,1],
                color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
axes[0,1].set_title('Time Breakdown by Frequency', fontsize=14, fontweight='bold')
axes[0,1].set_xlabel('Frequency (Hz)')
axes[0,1].set_ylabel('Time (ms)')
axes[0,1].legend(['Crypto', 'Transmission', 'Verification'])
axes[0,1].set_xticklabels(axes[0,1].get_xticklabels(), rotation=0)

# 2-3: 전송 시간 vs 총 시간
axes[1,0].scatter(df['avg_transmission'], df['avg_total_time'], 
                 s=df['sensors']*2, alpha=0.6, c=df['frequency'], cmap='plasma')
axes[1,0].plot([0, 120], [0, 120], 'r--', alpha=0.3)
axes[1,0].set_xlabel('Average Transmission Time (ms)')
axes[1,0].set_ylabel('Average Total Time (ms)')
axes[1,0].set_title('Transmission vs Total Time', fontsize=14, fontweight='bold')
cbar = plt.colorbar(axes[1,0].collections[0], ax=axes[1,0])
cbar.set_label('Frequency (Hz)')

# 2-4: 처리량 vs 주파수 (센서별)
for sensors in df['sensors'].unique():
    data_subset = df[df['sensors'] == sensors]
    axes[1,1].plot(data_subset['frequency'], data_subset['throughput'], 
                  marker='o', linewidth=2, markersize=8, label=f'{sensors} sensors')
axes[1,1].set_xlabel('Frequency (Hz)')
axes[1,1].set_ylabel('Throughput (req/s)')
axes[1,1].set_title('Throughput vs Frequency', fontsize=14, fontweight='bold')
axes[1,1].set_xscale('log')
axes[1,1].legend()
axes[1,1].grid(True, alpha=0.3)

plt.suptitle('WADI ED25519 Time Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('wadi_ed25519_time_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Figure 3: 비교 분석
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# 3-1: 센서 개수별 성능
sensors_perf = df.groupby('sensors').agg({
    'success_rate': 'mean',
    'avg_total_time': 'mean',
    'throughput': 'mean'
})

ax1 = axes[0,0]
ax2 = ax1.twinx()
ax1.bar(sensors_perf.index, sensors_perf['success_rate'], alpha=0.7, color='green', label='Success Rate')
ax2.plot(sensors_perf.index, sensors_perf['avg_total_time'], 'r-o', linewidth=2, markersize=8, label='Avg Time')
ax1.set_xlabel('Number of Sensors')
ax1.set_ylabel('Success Rate (%)', color='green')
ax2.set_ylabel('Average Time (ms)', color='red')
ax1.set_title('Performance by Sensor Count', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')

# 3-2: 주파수별 성능
freq_perf = df.groupby('frequency').agg({
    'success_rate': 'mean',
    'avg_total_time': 'mean',
    'throughput': 'mean'
})

ax3 = axes[0,1]
ax4 = ax3.twinx()
ax3.bar(np.arange(len(freq_perf)), freq_perf['success_rate'], alpha=0.7, color='blue', label='Success Rate')
ax4.plot(np.arange(len(freq_perf)), freq_perf['avg_total_time'], 'r-o', linewidth=2, markersize=8, label='Avg Time')
ax3.set_xticks(np.arange(len(freq_perf)))
ax3.set_xticklabels([f'{int(f)}Hz' for f in freq_perf.index])
ax3.set_xlabel('Frequency')
ax3.set_ylabel('Success Rate (%)', color='blue')
ax4.set_ylabel('Average Time (ms)', color='red')
ax3.set_title('Performance by Frequency', fontsize=14, fontweight='bold')
ax3.legend(loc='upper left')
ax4.legend(loc='upper right')

# 3-3: 처리된 요청 수
processed_data = df.pivot_table(values='processed', index='sensors', columns='frequency')
im = axes[1,0].imshow(processed_data, cmap='Blues', aspect='auto')
axes[1,0].set_xticks(np.arange(len(processed_data.columns)))
axes[1,0].set_yticks(np.arange(len(processed_data.index)))
axes[1,0].set_xticklabels([f'{int(f)}Hz' for f in processed_data.columns])
axes[1,0].set_yticklabels([f'{int(s)} sensors' for s in processed_data.index])
axes[1,0].set_xlabel('Frequency')
axes[1,0].set_ylabel('Sensors')
axes[1,0].set_title('Processed Requests per Condition', fontsize=14, fontweight='bold')

for i in range(len(processed_data.index)):
    for j in range(len(processed_data.columns)):
        text = axes[1,0].text(j, i, f'{int(processed_data.iloc[i, j])}',
                             ha="center", va="center", color="white" if processed_data.iloc[i, j] < 980 else "black")

plt.colorbar(im, ax=axes[1,0], label='Requests')

# 3-4: 효율성 지표
efficiency = df['throughput'] / df['frequency']  # 실제 처리량 / 목표 처리량
df['efficiency'] = efficiency * 100

efficiency_pivot = df.pivot_table(values='efficiency', index='sensors', columns='frequency')
sns.heatmap(efficiency_pivot, annot=True, fmt='.1f', cmap='RdYlGn', 
            ax=axes[1,1], vmin=0, vmax=100, cbar_kws={'label': 'Efficiency (%)'})
axes[1,1].set_title('Processing Efficiency (Actual/Target)', fontsize=14, fontweight='bold')
axes[1,1].set_xlabel('Frequency (Hz)')
axes[1,1].set_ylabel('Number of Sensors')

plt.suptitle('WADI ED25519 Comparative Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('wadi_ed25519_comparison.png', dpi=300, bbox_inches='tight')
plt.show()

# Figure 4: 요약 통계
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# 4-1: 전체 시간 분포
all_times = {
    'Preprocessing': data['overall_timing']['avg_preprocess_time_ms'],
    'Encryption': data['overall_timing']['avg_crypto_time_ms'],
    'Transmission': data['overall_timing']['avg_transmission_time_ms'],
    'Decryption': data['overall_timing']['avg_decryption_time_ms'],
    'Verification': data['overall_timing']['avg_verification_time_ms']
}

colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#95E1D3', '#F8B500']
wedges, texts, autotexts = axes[0,0].pie(all_times.values(), labels=all_times.keys(), 
                                          autopct='%1.2f%%', colors=colors, startangle=90)
axes[0,0].set_title('Overall Time Distribution', fontsize=14, fontweight='bold')

# 4-2: 주요 지표
metrics = {
    'Total Requests': f"{data['total_requests']:,}",
    'Success Rate': f"{data['overall_server_success_rate']:.2f}%",
    'Total Duration': f"{data['total_duration_minutes']:.1f} min",
    'Avg Total Time': f"{data['overall_timing']['avg_total_time_ms']:.2f} ms"
}

y_pos = np.arange(len(metrics))
axes[0,1].barh(y_pos, [1]*len(metrics), alpha=0)
for i, (key, value) in enumerate(metrics.items()):
    axes[0,1].text(0.5, i, f'{key}: {value}', ha='center', va='center', 
                  fontsize=12, fontweight='bold')
axes[0,1].set_yticks([])
axes[0,1].set_xticks([])
axes[0,1].set_title('Key Metrics Summary', fontsize=14, fontweight='bold')
axes[0,1].set_xlim(0, 1)

# 4-3: 센서별 평균 성공률
sensor_success = df.groupby('sensors')['success_rate'].mean()
axes[1,0].bar(sensor_success.index, sensor_success.values, color='skyblue', edgecolor='navy')
axes[1,0].axhline(y=99, color='r', linestyle='--', label='99% threshold')
axes[1,0].set_xlabel('Number of Sensors')
axes[1,0].set_ylabel('Average Success Rate (%)')
axes[1,0].set_title('Average Success Rate by Sensor Count', fontsize=14, fontweight='bold')
axes[1,0].legend()
axes[1,0].set_ylim(95, 101)

# 4-4: 처리량 분포
axes[1,1].boxplot([df[df['frequency']==f]['throughput'].values for f in sorted(df['frequency'].unique())],
                  labels=[f'{int(f)}Hz' for f in sorted(df['frequency'].unique())])
axes[1,1].set_xlabel('Frequency')
axes[1,1].set_ylabel('Throughput (req/s)')
axes[1,1].set_title('Throughput Distribution by Frequency', fontsize=14, fontweight='bold')
axes[1,1].set_yscale('log')
axes[1,1].grid(True, alpha=0.3)

plt.suptitle('WADI ED25519 Summary Statistics', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('wadi_ed25519_summary.png', dpi=300, bbox_inches='tight')
plt.show()

print("\n✅ WADI ED25519 시각화 완료!")
print("생성된 파일:")
print("  - wadi_ed25519_heatmaps.png")
print("  - wadi_ed25519_time_analysis.png")
print("  - wadi_ed25519_comparison.png")
print("  - wadi_ed25519_summary.png")
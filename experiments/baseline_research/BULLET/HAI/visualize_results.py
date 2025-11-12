import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from datetime import datetime

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

results_dir = '/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI/results'
output_dir = os.path.join(results_dir, 'visualizations')
os.makedirs(output_dir, exist_ok=True)

df = pd.read_csv(os.path.join(results_dir, 'hai_bulletproofs_final_20250903_145745.csv'))

print("데이터 개요:")
print(df.head())
print("\n컬럼 정보:")
print(df.columns.tolist())
print("\n기본 통계:")
print(df.describe())

fig = plt.figure(figsize=(20, 16))

ax1 = plt.subplot(3, 3, 1)
sensor_groups = df.groupby('sensor_count')['avg_total_time'].mean()
sensor_groups.plot(kind='bar', ax=ax1, color='steelblue')
ax1.set_title('Average Total Time by Sensor Count', fontsize=12, fontweight='bold')
ax1.set_xlabel('Sensor Count')
ax1.set_ylabel('Average Total Time (ms)')
ax1.grid(True, alpha=0.3)

ax2 = plt.subplot(3, 3, 2)
freq_groups = df.groupby('frequency')['avg_total_time'].mean()
freq_groups.plot(kind='bar', ax=ax2, color='coral', log=True)
ax2.set_title('Average Total Time by Frequency (Log Scale)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Frequency (Hz)')
ax2.set_ylabel('Average Total Time (ms)')
ax2.grid(True, alpha=0.3)

ax3 = plt.subplot(3, 3, 3)
pivot_data = df.pivot_table(values='avg_total_time', index='sensor_count', columns='frequency')
sns.heatmap(pivot_data, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax3)
ax3.set_title('Total Time Heatmap (Sensor Count vs Frequency)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Frequency (Hz)')
ax3.set_ylabel('Sensor Count')

ax4 = plt.subplot(3, 3, 4)
time_components = df[['condition_id', 'avg_commitment_time', 'avg_bulletproof_time', 'avg_verification_time']].set_index('condition_id')
time_components.plot(kind='bar', stacked=True, ax=ax4, colormap='viridis')
ax4.set_title('Time Components Breakdown by Condition', fontsize=12, fontweight='bold')
ax4.set_xlabel('Condition ID')
ax4.set_ylabel('Time (ms)')
ax4.legend(title='Components', bbox_to_anchor=(1.05, 1), loc='upper left')
ax4.grid(True, alpha=0.3)

ax5 = plt.subplot(3, 3, 5)
for sensor_count in df['sensor_count'].unique():
    sensor_data = df[df['sensor_count'] == sensor_count]
    ax5.plot(sensor_data['frequency'], sensor_data['avg_total_time'],
             marker='o', label=f'{sensor_count} sensors', linewidth=2)
ax5.set_xscale('log')
ax5.set_title('Performance vs Frequency by Sensor Count', fontsize=12, fontweight='bold')
ax5.set_xlabel('Frequency (Hz)')
ax5.set_ylabel('Average Total Time (ms)')
ax5.legend()
ax5.grid(True, alpha=0.3)

ax6 = plt.subplot(3, 3, 6)
df['efficiency'] = df['actual_frequency'] / df['frequency'] * 100
efficiency_pivot = df.pivot_table(values='efficiency', index='sensor_count', columns='frequency')
sns.heatmap(efficiency_pivot, annot=True, fmt='.1f', cmap='RdYlGn', ax=ax6, vmin=0, vmax=100)
ax6.set_title('Frequency Efficiency (%) Heatmap', fontsize=12, fontweight='bold')
ax6.set_xlabel('Target Frequency (Hz)')
ax6.set_ylabel('Sensor Count')

ax7 = plt.subplot(3, 3, 7)
resource_data = df[['sensor_count', 'frequency', 'avg_cpu_usage', 'avg_memory_usage']]
ax7_twin = ax7.twinx()
x_pos = np.arange(len(df))
width = 0.35
ax7.bar(x_pos - width/2, df['avg_cpu_usage'], width, label='CPU Usage (%)', color='skyblue', alpha=0.7)
ax7_twin.bar(x_pos + width/2, df['avg_memory_usage'], width, label='Memory (MB)', color='lightcoral', alpha=0.7)
ax7.set_xlabel('Condition ID')
ax7.set_ylabel('CPU Usage (%)', color='skyblue')
ax7_twin.set_ylabel('Memory Usage (MB)', color='lightcoral')
ax7.set_title('Resource Usage by Condition', fontsize=12, fontweight='bold')
ax7.set_xticks(x_pos)
ax7.set_xticklabels(df['condition_id'], rotation=45)
ax7.legend(loc='upper left')
ax7_twin.legend(loc='upper right')
ax7.grid(True, alpha=0.3)

ax8 = plt.subplot(3, 3, 8)
df['throughput'] = 1000 / df['avg_total_time']
throughput_pivot = df.pivot_table(values='throughput', index='sensor_count', columns='frequency')
sns.heatmap(throughput_pivot, annot=True, fmt='.1f', cmap='viridis', ax=ax8)
ax8.set_title('Throughput (Operations/sec) Heatmap', fontsize=12, fontweight='bold')
ax8.set_xlabel('Frequency (Hz)')
ax8.set_ylabel('Sensor Count')

ax9 = plt.subplot(3, 3, 9)
scalability_data = []
for freq in df['frequency'].unique():
    freq_data = df[df['frequency'] == freq]
    scalability_data.append({
        'frequency': freq,
        'sensor_1': freq_data[freq_data['sensor_count'] == 1]['avg_total_time'].values[0] if len(freq_data[freq_data['sensor_count'] == 1]) > 0 else 0,
        'sensor_10': freq_data[freq_data['sensor_count'] == 10]['avg_total_time'].values[0] if len(freq_data[freq_data['sensor_count'] == 10]) > 0 else 0,
        'sensor_50': freq_data[freq_data['sensor_count'] == 50]['avg_total_time'].values[0] if len(freq_data[freq_data['sensor_count'] == 50]) > 0 else 0,
        'sensor_100': freq_data[freq_data['sensor_count'] == 100]['avg_total_time'].values[0] if len(freq_data[freq_data['sensor_count'] == 100]) > 0 else 0,
    })
scalability_df = pd.DataFrame(scalability_data)
x = np.arange(len(scalability_df))
width = 0.2
ax9.bar(x - 1.5*width, scalability_df['sensor_1'], width, label='1 sensor', color='#1f77b4')
ax9.bar(x - 0.5*width, scalability_df['sensor_10'], width, label='10 sensors', color='#ff7f0e')
ax9.bar(x + 0.5*width, scalability_df['sensor_50'], width, label='50 sensors', color='#2ca02c')
ax9.bar(x + 1.5*width, scalability_df['sensor_100'], width, label='100 sensors', color='#d62728')
ax9.set_xlabel('Frequency (Hz)')
ax9.set_ylabel('Average Total Time (ms)')
ax9.set_title('Scalability Analysis', fontsize=12, fontweight='bold')
ax9.set_xticks(x)
ax9.set_xticklabels(scalability_df['frequency'])
ax9.legend()
ax9.grid(True, alpha=0.3)

plt.suptitle('HAI BulletProofs Performance Analysis', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'hai_bulletproofs_comprehensive_analysis.png'), dpi=300, bbox_inches='tight')
plt.close()

fig2, axes = plt.subplots(2, 2, figsize=(15, 12))

ax1 = axes[0, 0]
for sensor_count in df['sensor_count'].unique():
    sensor_data = df[df['sensor_count'] == sensor_count]
    ax1.plot(sensor_data['frequency'], sensor_data['actual_frequency'],
             marker='o', label=f'{sensor_count} sensors', linewidth=2)
ax1.plot([df['frequency'].min(), df['frequency'].max()],
         [df['frequency'].min(), df['frequency'].max()],
         'k--', alpha=0.5, label='Ideal')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_title('Target vs Actual Frequency', fontsize=14, fontweight='bold')
ax1.set_xlabel('Target Frequency (Hz)')
ax1.set_ylabel('Actual Frequency (Hz)')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2 = axes[0, 1]
time_breakdown = df[['sensor_count', 'avg_commitment_time', 'avg_bulletproof_time', 'avg_verification_time']].groupby('sensor_count').mean()
time_breakdown.plot(kind='bar', stacked=True, ax=ax2, colormap='Set2')
ax2.set_title('Average Time Breakdown by Sensor Count', fontsize=14, fontweight='bold')
ax2.set_xlabel('Sensor Count')
ax2.set_ylabel('Time (ms)')
ax2.legend(title='Components')
ax2.grid(True, alpha=0.3)

ax3 = axes[1, 0]
df['total_latency'] = df['duration_seconds'] * 1000
latency_pivot = df.pivot_table(values='total_latency', index='sensor_count', columns='frequency')
im = ax3.imshow(latency_pivot.values, aspect='auto', cmap='coolwarm')
ax3.set_xticks(np.arange(len(latency_pivot.columns)))
ax3.set_yticks(np.arange(len(latency_pivot.index)))
ax3.set_xticklabels(latency_pivot.columns)
ax3.set_yticklabels(latency_pivot.index)
ax3.set_title('Total Experiment Duration (ms)', fontsize=14, fontweight='bold')
ax3.set_xlabel('Frequency (Hz)')
ax3.set_ylabel('Sensor Count')
plt.colorbar(im, ax=ax3)
for i in range(len(latency_pivot.index)):
    for j in range(len(latency_pivot.columns)):
        text = ax3.text(j, i, f'{latency_pivot.values[i, j]:.0f}',
                       ha="center", va="center", color="white", fontsize=8)

ax4 = axes[1, 1]
efficiency_data = []
for _, row in df.iterrows():
    theoretical_ops = row['frequency'] * row['duration_seconds']
    actual_ops = row['total_requests']
    efficiency = (actual_ops / theoretical_ops * 100) if theoretical_ops > 0 else 0
    efficiency_data.append({
        'sensor_count': row['sensor_count'],
        'frequency': row['frequency'],
        'efficiency': efficiency
    })
efficiency_df = pd.DataFrame(efficiency_data)
for sensor_count in efficiency_df['sensor_count'].unique():
    sensor_data = efficiency_df[efficiency_df['sensor_count'] == sensor_count]
    ax4.plot(sensor_data['frequency'], sensor_data['efficiency'],
             marker='s', label=f'{sensor_count} sensors', linewidth=2)
ax4.set_xscale('log')
ax4.set_title('Processing Efficiency (%)', fontsize=14, fontweight='bold')
ax4.set_xlabel('Frequency (Hz)')
ax4.set_ylabel('Efficiency (%)')
ax4.legend()
ax4.grid(True, alpha=0.3)
ax4.axhline(y=100, color='r', linestyle='--', alpha=0.5)

plt.suptitle('HAI BulletProofs Detailed Performance Metrics', fontsize=16, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'hai_bulletproofs_detailed_metrics.png'), dpi=300, bbox_inches='tight')
plt.close()

summary_stats = {
    'Total Experiments': len(df),
    'Success Rate': f"{df['success_rate'].mean():.2f}%",
    'Average Processing Time': f"{df['avg_total_time'].mean():.2f} ms",
    'Best Performance (Time)': f"{df['avg_total_time'].min():.2f} ms",
    'Worst Performance (Time)': f"{df['avg_total_time'].max():.2f} ms",
    'Average CPU Usage': f"{df['avg_cpu_usage'].mean():.2f}%",
    'Average Memory Usage': f"{df['avg_memory_usage'].mean():.2f} MB",
    'Proof Size': f"{df['proof_size_bytes'].iloc[0]} bytes"
}

with open(os.path.join(output_dir, 'summary_statistics.txt'), 'w', encoding='utf-8') as f:
    f.write("HAI BulletProofs Performance Summary\n")
    f.write("=" * 50 + "\n\n")
    for key, value in summary_stats.items():
        f.write(f"{key}: {value}\n")

    f.write("\n\nPerformance by Sensor Count:\n")
    f.write("-" * 30 + "\n")
    for sensor_count in sorted(df['sensor_count'].unique()):
        sensor_data = df[df['sensor_count'] == sensor_count]
        f.write(f"\n{sensor_count} Sensor(s):\n")
        f.write(f"  Average Time: {sensor_data['avg_total_time'].mean():.2f} ms\n")
        f.write(f"  Min Time: {sensor_data['avg_total_time'].min():.2f} ms\n")
        f.write(f"  Max Time: {sensor_data['avg_total_time'].max():.2f} ms\n")

    f.write("\n\nPerformance by Frequency:\n")
    f.write("-" * 30 + "\n")
    for frequency in sorted(df['frequency'].unique()):
        freq_data = df[df['frequency'] == frequency]
        f.write(f"\n{frequency} Hz:\n")
        f.write(f"  Average Time: {freq_data['avg_total_time'].mean():.2f} ms\n")
        f.write(f"  Average Actual Frequency: {freq_data['actual_frequency'].mean():.2f} Hz\n")

print(f"\n시각화 파일이 {output_dir} 디렉토리에 저장되었습니다.")
print("\n생성된 파일:")
print("1. hai_bulletproofs_comprehensive_analysis.png - 종합 분석 차트")
print("2. hai_bulletproofs_detailed_metrics.png - 상세 성능 메트릭")
print("3. summary_statistics.txt - 요약 통계")
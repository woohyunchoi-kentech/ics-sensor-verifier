#!/usr/bin/env python3
"""
WADI HMAC Experiment Results Visualization (English Version)
============================================================
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정  
plt.rcParams['font.family'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def create_experiment_data():
    """실험 결과 데이터 생성"""
    data = [
        # 조건, 센서수, 주파수, 총요청, 성공률, 검증률, 실험시간, RPS, 암호화, 전송, 복호화, 검증, 총시간
        (1, 1, 1, 1000, 100.0, 100.0, 999.1, 1.0, 0.03, 27.5, 0.02, 0.15, 27.7),
        (2, 1, 2, 1000, 100.0, 100.0, 499.5, 2.0, 0.03, 27.8, 0.02, 0.14, 27.99),
        (3, 1, 10, 1000, 100.0, 100.0, 99.9, 10.0, 0.03, 27.2, 0.02, 0.15, 27.4),
        (4, 1, 100, 1000, 100.0, 100.0, 10.2, 97.8, 0.04, 28.1, 0.02, 0.16, 28.32),
        (5, 10, 1, 1000, 100.0, 100.0, 99.0, 10.1, 0.03, 27.6, 0.02, 0.15, 27.8),
        (6, 10, 2, 1000, 100.0, 100.0, 49.5, 20.2, 0.03, 27.9, 0.02, 0.14, 28.09),
        (7, 10, 10, 1000, 100.0, 100.0, 9.9, 100.9, 0.03, 27.4, 0.02, 0.15, 27.6),
        (8, 10, 100, 1000, 100.0, 100.0, 1.0, 981.8, 0.04, 28.3, 0.02, 0.16, 28.52),
        (9, 50, 1, 1000, 100.0, 100.0, 19.1, 52.4, 0.03, 27.7, 0.02, 0.15, 27.9),
        (10, 50, 2, 1000, 100.0, 100.0, 9.5, 105.1, 0.03, 27.5, 0.02, 0.14, 27.69),
        (11, 50, 10, 1000, 100.0, 100.0, 1.9, 521.6, 0.03, 27.8, 0.02, 0.15, 28.0),
        (12, 50, 100, 1000, 100.0, 100.0, 0.3, 2965.9, 0.04, 28.0, 0.02, 0.16, 28.22),
        (13, 100, 1, 1000, 100.0, 100.0, 9.1, 110.0, 0.03, 27.6, 0.02, 0.15, 27.8),
        (14, 100, 2, 1000, 100.0, 100.0, 4.6, 218.8, 0.03, 27.9, 0.02, 0.14, 28.09),
        (15, 100, 10, 1000, 100.0, 100.0, 0.9, 1080.7, 0.03, 27.3, 0.02, 0.15, 27.5),
        (16, 100, 100, 1000, 100.0, 100.0, 0.3, 3170.1, 0.04, 27.8, 0.02, 0.16, 28.02),
    ]
    
    columns = ['condition', 'sensors', 'frequency', 'total_requests', 'success_rate', 
               'verification_rate', 'experiment_time', 'rps', 'crypto_time', 
               'network_time', 'decrypt_time', 'verify_time', 'total_time']
    
    return pd.DataFrame(data, columns=columns)

def create_time_breakdown_chart(df):
    """Time breakdown chart (stacked bar chart)"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    conditions = [f"{row['sensors']}S×{row['frequency']}Hz" for _, row in df.iterrows()]
    
    # Time components
    crypto_times = df['crypto_time']
    network_times = df['network_time'] 
    decrypt_times = df['decrypt_time']
    verify_times = df['verify_time']
    
    # Color settings
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    # Stacked bar chart
    ax.bar(conditions, crypto_times, label='Encryption Time', color=colors[0], alpha=0.8)
    ax.bar(conditions, network_times, bottom=crypto_times, label='Network Transmission', color=colors[1], alpha=0.8)
    ax.bar(conditions, decrypt_times, bottom=crypto_times+network_times, label='Decryption Time', color=colors[2], alpha=0.8)
    ax.bar(conditions, verify_times, bottom=crypto_times+network_times+decrypt_times, label='Verification Time', color=colors[3], alpha=0.8)
    
    ax.set_title('WADI HMAC Experiment - Processing Time Breakdown Analysis', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Test Conditions (Sensors × Frequency)', fontsize=12)
    ax.set_ylabel('Processing Time (ms)', fontsize=12)
    ax.legend(loc='upper left', framealpha=0.9)
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    
    # Grid
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add total time text
    for i, (_, row) in enumerate(df.iterrows()):
        total = row['total_time']
        ax.text(i, total + 0.5, f'{total:.1f}ms', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    plt.tight_layout()
    return fig

def create_rps_performance_chart(df):
    """RPS performance chart"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # RPS by sensor count
    sensor_groups = df.groupby('sensors')['rps'].max().reset_index()
    ax1.bar(sensor_groups['sensors'], sensor_groups['rps'], 
           color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'], alpha=0.8)
    ax1.set_title('Maximum RPS Performance by Sensor Count', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Number of Sensors', fontsize=12)
    ax1.set_ylabel('Maximum RPS', fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Display RPS values
    for i, v in enumerate(sensor_groups['rps']):
        ax1.text(i, v + 50, f'{v:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # RPS trend by frequency
    frequency_groups = df.groupby('frequency')['rps'].mean().reset_index()
    ax2.plot(frequency_groups['frequency'], frequency_groups['rps'], 
            marker='o', linewidth=3, markersize=8, color='#FF6B6B')
    ax2.fill_between(frequency_groups['frequency'], frequency_groups['rps'], alpha=0.3, color='#FF6B6B')
    
    ax2.set_title('Average RPS Trend by Frequency', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Frequency (Hz)', fontsize=12)
    ax2.set_ylabel('Average RPS', fontsize=12)
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.grid(True, alpha=0.3)
    
    # Display RPS values
    for _, row in frequency_groups.iterrows():
        ax2.annotate(f'{row["rps"]:.0f}', (row['frequency'], row['rps']), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    plt.tight_layout()
    return fig

def create_scalability_heatmap(df):
    """Scalability heatmap"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create pivot table
    pivot_data = df.pivot_table(index='sensors', columns='frequency', values='rps', aggfunc='first')
    
    # Generate heatmap
    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='YlOrRd', 
               cbar_kws={'label': 'RPS (Requests Per Second)'}, ax=ax)
    
    ax.set_title('WADI HMAC Scalability Heatmap - RPS Performance', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Frequency (Hz)', fontsize=12)
    ax.set_ylabel('Number of Sensors', fontsize=12)
    
    plt.tight_layout()
    return fig

def create_efficiency_pie_chart(df):
    """Efficiency pie chart"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Calculate average times
    avg_crypto = df['crypto_time'].mean()
    avg_network = df['network_time'].mean() 
    avg_decrypt = df['decrypt_time'].mean()
    avg_verify = df['verify_time'].mean()
    
    # First pie chart - time breakdown
    sizes = [avg_crypto, avg_network, avg_decrypt, avg_verify]
    labels = ['Encryption\n(0.03ms)', 'Network Transmission\n(27.7ms)', 'Decryption\n(0.02ms)', 'Verification\n(0.15ms)']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    explode = [0, 0.1, 0, 0]  # Emphasize network portion
    
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                                      startangle=90, explode=explode, shadow=True)
    ax1.set_title('Average Processing Time Breakdown Analysis', fontsize=14, fontweight='bold')
    
    # Second pie chart - success rate
    success_data = [16, 0]  # All conditions successful
    success_labels = ['Verification Success\n(16 conditions)', 'Verification Failure\n(0 conditions)']  
    success_colors = ['#2ECC71', '#E74C3C']
    
    ax2.pie(success_data, labels=success_labels, colors=success_colors, autopct='%1.0f%%',
           startangle=90, shadow=True)
    ax2.set_title('HMAC Verification Success Rate', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    return fig

def create_comprehensive_dashboard(df):
    """Comprehensive dashboard"""
    fig = plt.figure(figsize=(20, 12))
    
    # Grid setup
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # 1. RPS trend (top left)
    ax1 = fig.add_subplot(gs[0, :2])
    conditions = [f"C{i}" for i in range(1, 17)]
    ax1.plot(conditions, df['rps'], marker='o', linewidth=2, markersize=6, color='#FF6B6B')
    ax1.fill_between(conditions, df['rps'], alpha=0.3, color='#FF6B6B')
    ax1.set_title('RPS Performance Trend by Condition', fontweight='bold')
    ax1.set_ylabel('RPS')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Time breakdown (top right)
    ax2 = fig.add_subplot(gs[0, 2:])
    time_components = ['Encryption', 'Network', 'Decryption', 'Verification']
    avg_times = [df['crypto_time'].mean(), df['network_time'].mean(), 
                df['decrypt_time'].mean(), df['verify_time'].mean()]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    bars = ax2.bar(time_components, avg_times, color=colors, alpha=0.8)
    ax2.set_title('Average Processing Time Composition', fontweight='bold')
    ax2.set_ylabel('Time (ms)')
    
    # Display values
    for bar, time in zip(bars, avg_times):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{time:.2f}ms', ha='center', va='bottom')
    
    # 3. Performance by sensors (middle left)
    ax3 = fig.add_subplot(gs[1, :2])
    sensor_perf = df.groupby('sensors').agg({
        'rps': 'max',
        'total_time': 'mean'
    }).reset_index()
    
    ax3_twin = ax3.twinx()
    
    bars1 = ax3.bar([f"{s} Sensors" for s in sensor_perf['sensors']], sensor_perf['rps'], 
                   alpha=0.7, color='#4ECDC4', label='Max RPS')
    line1 = ax3_twin.plot([f"{s} Sensors" for s in sensor_perf['sensors']], sensor_perf['total_time'], 
                         'ro-', linewidth=2, label='Avg Response Time')
    
    ax3.set_title('Performance Analysis by Sensor Scale', fontweight='bold')
    ax3.set_ylabel('Maximum RPS', color='#4ECDC4')
    ax3_twin.set_ylabel('Average Response Time (ms)', color='red')
    
    # 4. Efficiency by frequency (middle right)
    ax4 = fig.add_subplot(gs[1, 2:])
    freq_eff = df.groupby('frequency').agg({
        'rps': 'mean',
        'experiment_time': 'mean'
    }).reset_index()
    
    ax4.scatter(freq_eff['experiment_time'], freq_eff['rps'], 
               s=[100, 200, 300, 400], alpha=0.7, color='#45B7D1')
    
    for _, row in freq_eff.iterrows():
        ax4.annotate(f"{row['frequency']}Hz", 
                    (row['experiment_time'], row['rps']),
                    xytext=(5, 5), textcoords='offset points')
    
    ax4.set_title('Efficiency Analysis by Frequency', fontweight='bold')
    ax4.set_xlabel('Average Experiment Time (seconds)')
    ax4.set_ylabel('Average RPS')
    ax4.set_xscale('log')
    ax4.grid(True, alpha=0.3)
    
    # 5. Performance summary (bottom left)
    ax5 = fig.add_subplot(gs[2, :2])
    ax5.axis('off')
    
    summary_text = f"""
    🏆 WADI HMAC Experiment Performance Summary
    
    ✅ Completed Conditions: 16/16 (100%)
    ✅ Total Requests: {df['total_requests'].sum():,}  
    ✅ Overall Verification Rate: 100.00%
    ✅ Average RPS: {df['rps'].mean():.1f}
    ✅ Maximum RPS: {df['rps'].max():.1f}
    
    ⚡ Average Processing Time: {df['total_time'].mean():.2f}ms
    🔐 Average Encryption: {df['crypto_time'].mean():.3f}ms  
    🌐 Average Network: {df['network_time'].mean():.1f}ms
    ✔️ Average Verification: {df['verify_time'].mean():.2f}ms
    """
    
    ax5.text(0.1, 0.9, summary_text, transform=ax5.transAxes, fontsize=11,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    # 6. Scalability matrix (bottom right)
    ax6 = fig.add_subplot(gs[2, 2:])
    
    # Sensor count vs frequency matrix
    sensors = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]
    
    matrix_data = np.zeros((len(sensors), len(frequencies)))
    for i, s in enumerate(sensors):
        for j, f in enumerate(frequencies):
            rps_val = df[(df['sensors']==s) & (df['frequency']==f)]['rps'].values[0]
            matrix_data[i, j] = rps_val
    
    im = ax6.imshow(matrix_data, cmap='YlOrRd', aspect='auto')
    ax6.set_xticks(range(len(frequencies)))
    ax6.set_yticks(range(len(sensors)))
    ax6.set_xticklabels([f"{f}Hz" for f in frequencies])
    ax6.set_yticklabels([f"{s} Sensors" for s in sensors])
    ax6.set_title('Scalability Matrix (RPS)', fontweight='bold')
    
    # Display values
    for i in range(len(sensors)):
        for j in range(len(frequencies)):
            ax6.text(j, i, f'{matrix_data[i, j]:.0f}', ha="center", va="center", 
                    color="white" if matrix_data[i, j] > 1000 else "black", fontweight='bold')
    
    plt.suptitle('WADI HMAC-SHA256 Experiment Comprehensive Dashboard', fontsize=18, fontweight='bold', y=0.98)
    
    return fig

def save_all_charts():
    """Generate and save all charts"""
    
    # Create results directory
    results_dir = Path("../results/hmac_visualizations_english")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎨 Generating WADI HMAC experiment result visualizations...")
    
    # Load data
    df = create_experiment_data()
    
    # 1. Time breakdown chart
    print("📊 1/5: Generating processing time breakdown chart...")
    fig1 = create_time_breakdown_chart(df)
    fig1.savefig(results_dir / "01_time_breakdown_analysis_en.png", dpi=300, bbox_inches='tight')
    plt.close(fig1)
    
    # 2. RPS performance chart  
    print("🚀 2/5: Generating RPS performance chart...")
    fig2 = create_rps_performance_chart(df)
    fig2.savefig(results_dir / "02_rps_performance_en.png", dpi=300, bbox_inches='tight')
    plt.close(fig2)
    
    # 3. Scalability heatmap
    print("🔥 3/5: Generating scalability heatmap...")
    fig3 = create_scalability_heatmap(df)
    fig3.savefig(results_dir / "03_scalability_heatmap_en.png", dpi=300, bbox_inches='tight')
    plt.close(fig3)
    
    # 4. Efficiency pie chart
    print("🥧 4/5: Generating efficiency analysis chart...")
    fig4 = create_efficiency_pie_chart(df)
    fig4.savefig(results_dir / "04_efficiency_analysis_en.png", dpi=300, bbox_inches='tight')
    plt.close(fig4)
    
    # 5. Comprehensive dashboard
    print("📈 5/5: Generating comprehensive dashboard...")
    fig5 = create_comprehensive_dashboard(df)
    fig5.savefig(results_dir / "05_comprehensive_dashboard_en.png", dpi=300, bbox_inches='tight')
    plt.close(fig5)
    
    print(f"\n✅ All visualizations completed! Save location: {results_dir}")
    print(f"📁 Generated files:")
    print(f"   • 01_time_breakdown_analysis_en.png - Processing time breakdown analysis")
    print(f"   • 02_rps_performance_en.png - RPS performance analysis") 
    print(f"   • 03_scalability_heatmap_en.png - Scalability heatmap")
    print(f"   • 04_efficiency_analysis_en.png - Efficiency analysis")
    print(f"   • 05_comprehensive_dashboard_en.png - Comprehensive dashboard")

if __name__ == "__main__":
    save_all_charts()
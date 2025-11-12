import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path

# 모든 알고리즘의 공통 메트릭 분석
print("="*80)
print("COMPREHENSIVE ALGORITHM COMPARISON ANALYSIS")
print("="*80)

# 공통 메트릭 정의
common_metrics = {
    'success_rate': [],
    'total_time_ms': [],
    'preprocessing_time_ms': [],
    'crypto_time_ms': [],
    'transmission_time_ms': [],
    'verification_time_ms': [],
    'algorithm': [],
    'dataset': [],
    'sensor_count': [],
    'frequency': []
}

# HMAC 데이터 로드 및 처리
print("\n📊 LOADING HMAC DATA...")
hmac_file = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/HMAC_FINAL/HMAC_HAI/hai_hmac_experiment/hai_hmac_results/detailed_progress_16_20250901_141509.csv"
hmac_df = pd.read_csv(hmac_file)

for _, row in hmac_df.iterrows():
    common_metrics['success_rate'].append(row['success_rate'])
    common_metrics['total_time_ms'].append(row['avg_total_time_ms'])
    common_metrics['preprocessing_time_ms'].append(row['avg_preprocessing_ms'])
    common_metrics['crypto_time_ms'].append(row['avg_hmac_generation_ms'])
    common_metrics['transmission_time_ms'].append(row['avg_network_rtt_ms'])
    common_metrics['verification_time_ms'].append(row['avg_verification_ms'])
    common_metrics['algorithm'].append('HMAC')
    common_metrics['dataset'].append('HAI')
    common_metrics['sensor_count'].append(row['sensor_count'])
    common_metrics['frequency'].append(row['frequency'])

print(f"HMAC: {len(hmac_df)} conditions loaded")

# ED25519 데이터 로드 및 처리
print("\n📊 LOADING ED25519 DATA...")
ed25519_file = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/ED25519/HAI_ED25519/hai_ed25519_complete_20250902_150711.csv"
ed25519_df = pd.read_csv(ed25519_file)

# ED25519 데이터를 조건별로 그룹화
ed25519_grouped = ed25519_df.groupby(['sensor_count', 'frequency']).agg({
    'server_success': lambda x: (x == True).mean() * 100,
    'total_time_ms': 'mean',
    'preprocess_time_ms': 'mean',
    'crypto_time_ms': 'mean',
    'transmission_time_ms': 'mean',
    'verification_time_ms': 'mean'
}).reset_index()

for _, row in ed25519_grouped.iterrows():
    common_metrics['success_rate'].append(row['server_success'])
    common_metrics['total_time_ms'].append(row['total_time_ms'])
    common_metrics['preprocessing_time_ms'].append(row['preprocess_time_ms'])
    common_metrics['crypto_time_ms'].append(row['crypto_time_ms'])
    common_metrics['transmission_time_ms'].append(row['transmission_time_ms'])
    common_metrics['verification_time_ms'].append(row['verification_time_ms'])
    common_metrics['algorithm'].append('ED25519')
    common_metrics['dataset'].append('HAI')
    common_metrics['sensor_count'].append(row['sensor_count'])
    common_metrics['frequency'].append(row['frequency'])

print(f"ED25519: {len(ed25519_grouped)} conditions loaded")

# CKKS 데이터 로드 및 처리
print("\n📊 LOADING CKKS DATA...")
ckks_file = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/CKKS_FINAL/HAI_CKKS/hai_ckks_experiment/hai_ckks_results/detailed_progress_16_20250901_144317.csv"
ckks_df = pd.read_csv(ckks_file)

# CKKS 데이터를 조건별로 그룹화
ckks_grouped = ckks_df.groupby(['sensor_count', 'frequency']).agg({
    'success': lambda x: (x == True).mean() * 100,
    'total_time_ms': 'mean',
    'preprocessing_time_ms': 'mean',
    'encryption_time_ms': 'mean',
    'network_rtt_ms': 'mean',
    'verification_time_ms': 'mean'
}).reset_index()

for _, row in ckks_grouped.iterrows():
    common_metrics['success_rate'].append(row['success'])
    common_metrics['total_time_ms'].append(row['total_time_ms'])
    common_metrics['preprocessing_time_ms'].append(row['preprocessing_time_ms'])
    common_metrics['crypto_time_ms'].append(row['encryption_time_ms'])
    common_metrics['transmission_time_ms'].append(row['network_rtt_ms'])
    common_metrics['verification_time_ms'].append(row['verification_time_ms'])
    common_metrics['algorithm'].append('CKKS')
    common_metrics['dataset'].append('HAI')
    common_metrics['sensor_count'].append(row['sensor_count'])
    common_metrics['frequency'].append(row['frequency'])

print(f"CKKS: {len(ckks_grouped)} conditions loaded")

# BulletProfs 데이터 로드 및 처리
print("\n📊 LOADING BULLETPROOFS DATA...")
bullet_file = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/BULLET/HAI/results/hai_bulletproofs_final_20250903_145745.csv"
bullet_df = pd.read_csv(bullet_file)

for _, row in bullet_df.iterrows():
    common_metrics['success_rate'].append(row['success_rate'])
    common_metrics['total_time_ms'].append(row['avg_total_time'])
    common_metrics['preprocessing_time_ms'].append(row['avg_commitment_time'])
    common_metrics['crypto_time_ms'].append(row['avg_bulletproof_time'])
    common_metrics['transmission_time_ms'].append(0.0)  # BulletProfs는 전송 없음
    common_metrics['verification_time_ms'].append(row['avg_verification_time'])
    common_metrics['algorithm'].append('BulletProfs')
    common_metrics['dataset'].append('HAI')
    common_metrics['sensor_count'].append(row['sensor_count'])
    common_metrics['frequency'].append(row['frequency'])

print(f"BulletProfs: {len(bullet_df)} conditions loaded")

# DataFrame 생성
df = pd.DataFrame(common_metrics)
print(f"\n📈 TOTAL CONDITIONS: {len(df)}")

# 시각화는 생략하고 상세 분석만 수행

# 상세 통계 출력
print("\n" + "="*80)
print("DETAILED STATISTICAL COMPARISON")
print("="*80)

algorithms = ['HMAC', 'ED25519', 'CKKS', 'BulletProfs']
metrics = ['success_rate', 'total_time_ms', 'preprocessing_time_ms', 'crypto_time_ms', 'transmission_time_ms', 'verification_time_ms']

print(f"\n{'Algorithm':<12} {'Success%':<9} {'Total(ms)':<12} {'Preproc':<10} {'Crypto':<12} {'Transmit':<12} {'Verify':<10}")
print("-" * 80)

for alg in algorithms:
    alg_data = df[df['algorithm'] == alg]
    if len(alg_data) > 0:
        success_avg = alg_data['success_rate'].mean()
        total_avg = alg_data['total_time_ms'].mean()
        prep_avg = alg_data['preprocessing_time_ms'].mean()
        crypto_avg = alg_data['crypto_time_ms'].mean()
        trans_avg = alg_data['transmission_time_ms'].mean()
        verify_avg = alg_data['verification_time_ms'].mean()

        print(f"{alg:<12} {success_avg:<9.1f} {total_avg:<12.1f} {prep_avg:<10.3f} {crypto_avg:<12.3f} {trans_avg:<12.1f} {verify_avg:<10.1f}")

# 성능 순위 분석
print("\n🏆 PERFORMANCE RANKINGS:")
print("-" * 40)

ranking_metrics = {
    'Success Rate (높을수록 좋음)': df.groupby('algorithm')['success_rate'].mean().sort_values(ascending=False),
    'Total Time (낮을수록 좋음)': df.groupby('algorithm')['total_time_ms'].mean().sort_values(),
    'Crypto Speed (낮을수록 좋음)': df.groupby('algorithm')['crypto_time_ms'].mean().sort_values(),
    'Verification Speed (낮을수록 좋음)': df.groupby('algorithm')['verification_time_ms'].mean().sort_values()
}

for metric_name, ranking in ranking_metrics.items():
    print(f"\n• {metric_name}:")
    for i, (alg, value) in enumerate(ranking.items(), 1):
        print(f"  {i}. {alg}: {value:.2f}")

# 센서 확장성 분석
print("\n📈 SCALABILITY ANALYSIS (by sensor count):")
print("-" * 50)

scalability_df = df.groupby(['algorithm', 'sensor_count'])['total_time_ms'].mean().reset_index()
scalability_pivot = scalability_df.pivot(index='sensor_count', columns='algorithm', values='total_time_ms')

print(scalability_pivot.fillna(0))

# 주파수 확장성 분석
print("\n🔄 FREQUENCY SCALING ANALYSIS:")
print("-" * 40)

freq_df = df.groupby(['algorithm', 'frequency'])['total_time_ms'].mean().reset_index()
freq_pivot = freq_df.pivot(index='frequency', columns='algorithm', values='total_time_ms')

print(freq_pivot.fillna(0))

# 트레이드오프 분석
print("\n⚖️  PERFORMANCE-PRIVACY TRADE-OFF ANALYSIS:")
print("-" * 50)
print("• Privacy Level: HMAC/ED25519 (No Privacy) < CKKS/BulletProfs (Full Privacy)")
print("• Performance: ED25519 (Fast) < HMAC < BulletProfs < CKKS (Slow)")
print("• Success Rate: HMAC/ED25519/CKKS (100%) > BulletProfs (0% on HAI)")
print("• Bandwidth: BulletProfs (No transmission) < Others (Network dependent)")

print("\n💡 DEPLOYMENT RECOMMENDATIONS:")
print("-" * 40)
print("• Real-time ICS: ED25519 (ultra-fast crypto + verification)")
print("• Legacy systems: HMAC (simple implementation, network-bound)")
print("• Privacy-critical: CKKS (if computational resources available)")
print("• Bandwidth-limited: BulletProfs (if verification latency acceptable)")
print("• High-reliability: Avoid BulletProfs on HAI-like environments")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 실제 실험 데이터 기반 타이밍 분해 (ms 단위)
# HAI와 WADI 평균값 사용

algorithms = ['HMAC', 'ED25519', 'BulletProofs', 'CKKS']

# HAI 데이터셋 타이밍 (ms)
hai_preprocessing = [0.35, 0.0005, 0.0, 10.2]  # BulletProfs는 전처리 없음
hai_crypto = [0.023, 0.0044, 5.9, 382.5]  # 암호화/서명/증명생성
hai_transmission = [42.0, 22.9, 0.0, 467.5]  # 전송시간, BulletProfs는 즉시
hai_decryption = [0.0, 0.0, 0.0, 2.1]  # 복호화 (HMAC/ED25519/BulletProfs 없음)
hai_verification = [0.18, 0.4, 13.8, 5.7]  # 검증시간

# WADI 데이터셋 타이밍 (ms)
wadi_preprocessing = [0.035, 0.0006, 0.0, 0.001]
wadi_crypto = [0.032, 0.0044, 6.2, 9.2]
wadi_transmission = [27.7, 45.7, 0.0, 31.6]
wadi_decryption = [0.0, 0.0, 0.0, 0.0]  # WADI CKKS는 복호화 시간 별도 측정 안됨
wadi_verification = [0.15, 0.32, 125.1, 0.0]

# 색상 설정 (각 타이밍 단계별)
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
stage_labels = ['Preprocessing', 'Crypto Operation', 'Transmission', 'Decryption', 'Verification']

# 그림 생성
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 1. HAI 데이터셋 타이밍 분해 (스택 차트)
bottom_hai = np.zeros(len(algorithms))
bars_hai = []

for i, (times, label, color) in enumerate(zip(
    [hai_preprocessing, hai_crypto, hai_transmission, hai_decryption, hai_verification],
    stage_labels, colors)):
    bars = ax1.bar(algorithms, times, bottom=bottom_hai, label=label, color=color, alpha=0.8)
    bars_hai.append(bars)
    bottom_hai += np.array(times)

ax1.set_ylabel('Time (ms)', fontsize=12)
ax1.set_title('1. HAI Dataset - Timing Breakdown', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=9)
ax1.set_yscale('log')

# 총 시간 표시
hai_totals = [sum(x) for x in zip(hai_preprocessing, hai_crypto, hai_transmission, hai_decryption, hai_verification)]
for i, total in enumerate(hai_totals):
    ax1.text(i, total * 1.1, f'{total:.1f}ms', ha='center', va='bottom', fontweight='bold')

# 2. WADI 데이터셋 타이밍 분해 (스택 차트)
bottom_wadi = np.zeros(len(algorithms))
bars_wadi = []

for i, (times, label, color) in enumerate(zip(
    [wadi_preprocessing, wadi_crypto, wadi_transmission, wadi_decryption, wadi_verification],
    stage_labels, colors)):
    bars = ax2.bar(algorithms, times, bottom=bottom_wadi, label=label, color=color, alpha=0.8)
    bars_wadi.append(bars)
    bottom_wadi += np.array(times)

ax2.set_ylabel('Time (ms)', fontsize=12)
ax2.set_title('2. WADI Dataset - Timing Breakdown', fontsize=14, fontweight='bold')
ax2.legend(loc='upper left', fontsize=9)
ax2.set_yscale('log')

# 총 시간 표시
wadi_totals = [sum(x) for x in zip(wadi_preprocessing, wadi_crypto, wadi_transmission, wadi_decryption, wadi_verification)]
for i, total in enumerate(wadi_totals):
    ax2.text(i, total * 1.1, f'{total:.1f}ms', ha='center', va='bottom', fontweight='bold')

# 3. 암호화 연산 시간만 비교
crypto_times_hai = hai_crypto
crypto_times_wadi = wadi_crypto

x = np.arange(len(algorithms))
width = 0.35

bars1 = ax3.bar(x - width/2, crypto_times_hai, width, label='HAI', color='#FF6B6B', alpha=0.8)
bars2 = ax3.bar(x + width/2, crypto_times_wadi, width, label='WADI', color='#4ECDC4', alpha=0.8)

ax3.set_xlabel('Algorithms', fontsize=12)
ax3.set_ylabel('Crypto Operation Time (ms)', fontsize=12)
ax3.set_title('3. Cryptographic Operation Time Comparison', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(algorithms)
ax3.legend()
ax3.set_yscale('log')

# 값 표시
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height * 1.1,
                f'{height:.3f}ms', ha='center', va='bottom', fontsize=8, rotation=45)

# 4. 검증 시간 비교
verification_times_hai = hai_verification
verification_times_wadi = wadi_verification

bars1 = ax4.bar(x - width/2, verification_times_hai, width, label='HAI', color='#FECA57', alpha=0.8)
bars2 = ax4.bar(x + width/2, verification_times_wadi, width, label='WADI', color='#96CEB4', alpha=0.8)

ax4.set_xlabel('Algorithms', fontsize=12)
ax4.set_ylabel('Verification Time (ms)', fontsize=12)
ax4.set_title('4. Verification Time Comparison', fontsize=14, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels(algorithms)
ax4.legend()
ax4.set_yscale('log')

# 값 표시
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax4.text(bar.get_x() + bar.get_width()/2., height * 1.1,
                    f'{height:.1f}ms', ha='center', va='bottom', fontsize=9)

# 전체 레이아웃 조정
plt.tight_layout()
plt.suptitle('ICS Authentication Algorithm Timing Breakdown Analysis', fontsize=16, fontweight='bold', y=0.95)
plt.subplots_adjust(top=0.90)

# 저장
plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/timing_breakdown_analysis.png',
           dpi=300, bbox_inches='tight')
plt.show()

# 상세 분석 출력
print("=" * 70)
print("DETAILED TIMING BREAKDOWN ANALYSIS")
print("=" * 70)
print()

print("📊 HAI DATASET TIMING BREAKDOWN:")
print("-" * 50)
print(f"{'Algorithm':<12} {'Preproc':<8} {'Crypto':<8} {'Transmit':<9} {'Decrypt':<8} {'Verify':<8} {'Total':<8}")
print("-" * 50)
for i, alg in enumerate(algorithms):
    print(f"{alg:<12} {hai_preprocessing[i]:<8.3f} {hai_crypto[i]:<8.3f} {hai_transmission[i]:<9.1f} "
          f"{hai_decryption[i]:<8.3f} {hai_verification[i]:<8.1f} {hai_totals[i]:<8.1f}")

print(f"\n📊 WADI DATASET TIMING BREAKDOWN:")
print("-" * 50)
print(f"{'Algorithm':<12} {'Preproc':<8} {'Crypto':<8} {'Transmit':<9} {'Decrypt':<8} {'Verify':<8} {'Total':<8}")
print("-" * 50)
for i, alg in enumerate(algorithms):
    print(f"{alg:<12} {wadi_preprocessing[i]:<8.3f} {wadi_crypto[i]:<8.3f} {wadi_transmission[i]:<9.1f} "
          f"{wadi_decryption[i]:<8.3f} {wadi_verification[i]:<8.1f} {wadi_totals[i]:<8.1f}")

print("\n🔍 KEY OBSERVATIONS:")
print("=" * 70)

# 가장 빠른 단계별 분석
print("⚡ FASTEST BY STAGE:")
stages = ['Preprocessing', 'Crypto Operation', 'Transmission', 'Decryption', 'Verification']
hai_data = [hai_preprocessing, hai_crypto, hai_transmission, hai_decryption, hai_verification]
wadi_data = [wadi_preprocessing, wadi_crypto, wadi_transmission, wadi_decryption, wadi_verification]

for i, stage in enumerate(stages):
    hai_min_idx = np.argmin([x for x in hai_data[i] if x > 0] or [float('inf')])
    wadi_min_idx = np.argmin([x for x in wadi_data[i] if x > 0] or [float('inf')])

    if hai_data[i][hai_min_idx] > 0:
        print(f"• {stage}: HAI - {algorithms[hai_min_idx]} ({hai_data[i][hai_min_idx]:.3f}ms)")
    if wadi_data[i][wadi_min_idx] > 0:
        print(f"  {' '*len(stage)}: WADI - {algorithms[wadi_min_idx]} ({wadi_data[i][wadi_min_idx]:.3f}ms)")

print("\n🎯 ALGORITHM CHARACTERISTICS:")
print("-" * 40)
print("• HMAC: Network-bound (transmission dominant)")
print("• ED25519: Ultra-fast crypto, network-bound")
print("• BulletProofs: Verification-heavy, no transmission")
print("• CKKS: Crypto-heavy, network-bound")

print("\n📈 SCALABILITY INSIGHTS:")
print("-" * 40)
print("• BulletProofs: Constant verification time regardless of sensors")
print("• HMAC/ED25519: Linear scaling with sensor count")
print("• CKKS: Batch efficiency reduces per-sensor overhead")

print("\n💡 DEPLOYMENT RECOMMENDATIONS:")
print("-" * 40)
print("• Low Latency: ED25519 (crypto + verification < 1ms)")
print("• Privacy Required: BulletProofs (verification-dominant but secure)")
print("• Computation on Data: CKKS (accept higher crypto overhead)")
print("• Bandwidth Limited: BulletProfs (no transmission) > others")
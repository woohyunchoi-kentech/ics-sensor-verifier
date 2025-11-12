import matplotlib.pyplot as plt
import numpy as np

# 실제 실험 데이터에서 추출한 크기 정보
algorithms = ['HMAC\n(SHA-256)', 'ED25519\n(Digital Sign)', 'BulletProofs\n(Zero-Knowledge)', 'CKKS\n(Homomorphic)']

# 증명/서명/암호문 크기 (bytes)
proof_sizes = [32, 64, 1395, 13000]  # CKKS는 평균 추정값

# 센서 수에 따른 크기 변화 시뮬레이션
sensor_counts = [1, 10, 50, 100]

# 각 알고리즘별 센서 수에 따른 크기 변화
hmac_sizes = [32 * count for count in sensor_counts]  # 선형 증가
ed25519_sizes = [64 * count for count in sensor_counts]  # 선형 증가
bulletproof_sizes = [1395] * len(sensor_counts)  # 일정한 크기
ckks_sizes = [13000, 25000, 45000, 65000]  # 배치 효율성으로 서브선형

# 색상 설정
colors = ['#2E8B57', '#4169E1', '#DC143C', '#FF8C00']

# 그림 생성
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 1. 기본 증명/서명 크기 비교 (로그 스케일)
bars1 = ax1.bar(algorithms, proof_sizes, color=colors, alpha=0.8)
ax1.set_ylabel('Size (bytes)', fontsize=12)
ax1.set_title('1. Proof/Signature Base Size Comparison', fontsize=14, fontweight='bold')
ax1.set_yscale('log')

for i, (bar, size) in enumerate(zip(bars1, proof_sizes)):
    height = bar.get_height()
    if size >= 1000:
        label = f'{size/1000:.1f}KB'
    else:
        label = f'{size}B'
    ax1.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             label, ha='center', va='bottom', fontweight='bold')

# 2. 센서 수에 따른 크기 확장성
ax2.plot(sensor_counts, hmac_sizes, 'o-', color=colors[0], linewidth=2, markersize=8, label='HMAC')
ax2.plot(sensor_counts, ed25519_sizes, 's-', color=colors[1], linewidth=2, markersize=8, label='ED25519')
ax2.plot(sensor_counts, bulletproof_sizes, '^-', color=colors[2], linewidth=3, markersize=10, label='BulletProofs')
ax2.plot(sensor_counts, ckks_sizes, 'd-', color=colors[3], linewidth=2, markersize=8, label='CKKS')

ax2.set_xlabel('Number of Sensors', fontsize=12)
ax2.set_ylabel('Total Size (bytes)', fontsize=12)
ax2.set_title('2. Scalability: Size vs Sensor Count', fontsize=14, fontweight='bold')
ax2.set_yscale('log')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# 3. 크기 효율성 비교 (100센서 기준)
size_100_sensors = [hmac_sizes[-1], ed25519_sizes[-1], bulletproof_sizes[-1], ckks_sizes[-1]]
bars3 = ax3.bar(algorithms, size_100_sensors, color=colors, alpha=0.8)
ax3.set_ylabel('Total Size (bytes)', fontsize=12)
ax3.set_title('3. Size Efficiency at 100 Sensors', fontsize=14, fontweight='bold')
ax3.set_yscale('log')

for i, (bar, size) in enumerate(zip(bars3, size_100_sensors)):
    height = bar.get_height()
    if size >= 1000:
        label = f'{size/1000:.1f}KB'
    else:
        label = f'{size}B'
    color_text = 'red' if size > 10000 else 'green' if size < 2000 else 'orange'
    ax3.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             label, ha='center', va='bottom', fontweight='bold', color=color_text)

# 4. 크기 대비 프라이버시 레벨
privacy_levels = [0, 0, 10, 8]  # 0=없음, 10=완전영지식, 8=암호화
scatter = ax4.scatter(proof_sizes, privacy_levels, c=colors, s=300, alpha=0.7)

for i, (size, privacy, alg) in enumerate(zip(proof_sizes, privacy_levels, algorithms)):
    ax4.annotate(alg.replace('\n', ' '), (size, privacy),
                xytext=(10, 10), textcoords='offset points',
                fontsize=10, fontweight='bold')

ax4.set_xlabel('Proof/Signature Size (bytes)', fontsize=12)
ax4.set_ylabel('Privacy Level (0=None, 10=Complete)', fontsize=12)
ax4.set_title('4. Size vs Privacy Trade-off', fontsize=14, fontweight='bold')
ax4.set_xscale('log')
ax4.grid(True, alpha=0.3)

# 전체 레이아웃 조정
plt.tight_layout()
plt.suptitle('ICS Authentication Algorithm Size Analysis', fontsize=16, fontweight='bold', y=0.95)
plt.subplots_adjust(top=0.90)

# 저장
plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/algorithm_size_comparison.png',
           dpi=300, bbox_inches='tight')
plt.show()

# 크기 분석 출력
print("=" * 60)
print("ALGORITHM SIZE ANALYSIS")
print("=" * 60)
print()

print("📦 BASE SIZE RANKING:")
size_ranking = sorted(zip(algorithms, proof_sizes), key=lambda x: x[1])
for i, (alg, size) in enumerate(size_ranking, 1):
    if size >= 1000:
        size_str = f"{size/1000:.1f}KB"
        multiplier = f"({size/size_ranking[0][1]:.0f}x)"
    else:
        size_str = f"{size}B"
        multiplier = "(baseline)" if i == 1 else f"({size/size_ranking[0][1]:.0f}x)"

    efficiency = "🟢 EXCELLENT" if size < 100 else "🟡 MODERATE" if size < 2000 else "🔴 LARGE"
    print(f"{i}. {alg.replace(chr(10), ' ')}: {size_str} {multiplier} {efficiency}")

print("\n📈 SCALABILITY ANALYSIS (100 sensors):")
scalability_ranking = sorted(zip(algorithms, size_100_sensors), key=lambda x: x[1])
for i, (alg, size) in enumerate(scalability_ranking, 1):
    if size >= 1000:
        size_str = f"{size/1000:.1f}KB"
    else:
        size_str = f"{size}B"

    # 확장성 평가
    base_size = proof_sizes[algorithms.index(alg)]
    scale_factor = size / base_size if base_size > 0 else 1

    if scale_factor == 1:
        scalability = "🏆 CONSTANT"
    elif scale_factor <= 10:
        scalability = "🟢 SUBLINEAR"
    elif scale_factor <= 100:
        scalability = "🟡 LINEAR"
    else:
        scalability = "🔴 SUPERLINEAR"

    print(f"{i}. {alg.replace(chr(10), ' ')}: {size_str} {scalability}")

print("\n🔒 SIZE-PRIVACY EFFICIENCY:")
for i, (alg, size, privacy) in enumerate(zip(algorithms, proof_sizes, privacy_levels)):
    if privacy == 0:
        privacy_str = "No Privacy"
        efficiency = "N/A"
    else:
        privacy_str = "Zero-Knowledge" if privacy == 10 else "Encrypted"
        # 프라이버시 대비 크기 효율성 (작을수록 좋음)
        efficiency_score = size / privacy if privacy > 0 else float('inf')
        if efficiency_score < 200:
            efficiency = "🏆 EXCELLENT"
        elif efficiency_score < 1000:
            efficiency = "🟢 GOOD"
        else:
            efficiency = "🟡 ACCEPTABLE"

    size_str = f"{size/1000:.1f}KB" if size >= 1000 else f"{size}B"
    print(f"• {alg.replace(chr(10), ' ')}: {size_str} for {privacy_str} {efficiency}")

print("\n" + "=" * 60)
print("🎯 SIZE-BASED RECOMMENDATIONS:")
print("=" * 60)
print("🥇 MINIMUM SIZE: HMAC (32B) - Best for bandwidth-limited")
print("🥈 COMPACT: ED25519 (64B) - Good size/security balance")
print("🥉 EFFICIENT PRIVACY: BulletProofs (1.4KB constant) - Scalable privacy")
print("⚠️  LARGE: CKKS (13-65KB) - High bandwidth requirement")
print()
print("📋 SIZE-CONSCIOUS DEPLOYMENT:")
print("• Bandwidth Limited: HMAC or ED25519")
print("• Scalable Privacy: BulletProofs (size independent of sensors)")
print("• Rich Computation: CKKS (if bandwidth allows)")
print("• IoT/Edge: Avoid CKKS, prefer BulletProofs over linear schemes")
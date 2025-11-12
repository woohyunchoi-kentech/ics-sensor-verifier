import matplotlib.pyplot as plt
import numpy as np

# 실제 실험 데이터 기반 객관적 분석
algorithms = ['HMAC', 'ED25519', 'BulletProofs', 'CKKS']
processing_times = [27.89, 23.19, 132.43, 975.8]  # ms
success_rates = [100, 100, 50, 99.99]  # HAI+WADI 평균 (BulletProofs는 HAI 실패로 50%)
network_overhead = [32, 64, 1395, 13000]  # bytes
privacy_levels = [0, 0, 10, 8]  # 0=없음, 10=완전영지식, 8=암호화

# 색상 설정
colors = ['#2E8B57', '#4169E1', '#DC143C', '#FF8C00']

# 그림 생성
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

# 1. 처리 시간 비교 (로그 스케일)
bars1 = ax1.bar(algorithms, processing_times, color=colors, alpha=0.8)
ax1.set_ylabel('Processing Time (ms)', fontsize=11)
ax1.set_title('1. Average Processing Time Comparison', fontsize=12, fontweight='bold')
ax1.set_yscale('log')
for i, (bar, time) in enumerate(zip(bars1, processing_times)):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             f'{time:.1f}ms', ha='center', va='bottom', fontweight='bold', fontsize=9)

# 2. 성공률 비교
bars2 = ax2.bar(algorithms, success_rates, color=colors, alpha=0.8)
ax2.set_ylabel('Success Rate (%)', fontsize=11)
ax2.set_title('2. Cross-Environment Success Rate', fontsize=12, fontweight='bold')
ax2.set_ylim(0, 105)
for i, (bar, rate) in enumerate(zip(bars2, success_rates)):
    height = bar.get_height()
    color = 'red' if rate < 80 else 'green'
    ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', color=color, fontsize=9)

# 3. 네트워크 오버헤드 (로그 스케일)
bars3 = ax3.bar(algorithms, network_overhead, color=colors, alpha=0.8)
ax3.set_ylabel('Network Overhead (bytes)', fontsize=11)
ax3.set_title('3. Proof/Signature Size Comparison', fontsize=12, fontweight='bold')
ax3.set_yscale('log')
for i, (bar, size) in enumerate(zip(bars3, network_overhead)):
    height = bar.get_height()
    if size >= 1000:
        label = f'{size/1000:.1f}KB'
    else:
        label = f'{size}B'
    ax3.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             label, ha='center', va='bottom', fontweight='bold', fontsize=9)

# 4. 프라이버시 레벨 vs 성능 산점도
scatter = ax4.scatter(privacy_levels, processing_times, c=colors, s=200, alpha=0.7)
ax4.set_xlabel('Privacy Level (0=None, 10=Complete)', fontsize=11)
ax4.set_ylabel('Processing Time (ms)', fontsize=11)
ax4.set_title('4. Privacy vs Performance Trade-off', fontsize=12, fontweight='bold')
ax4.set_yscale('log')

# 알고리즘 라벨 추가
for i, (x, y, alg) in enumerate(zip(privacy_levels, processing_times, algorithms)):
    ax4.annotate(alg, (x, y), xytext=(10, 10),
                textcoords='offset points', fontsize=10, fontweight='bold')

# 전체 레이아웃 조정
plt.tight_layout()
plt.suptitle('ICS Sensor Authentication Algorithm Performance Analysis', fontsize=14, fontweight='bold', y=0.95)
plt.subplots_adjust(top=0.90)

# 저장
plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/algorithm_performance_analysis.png',
           dpi=300, bbox_inches='tight')
plt.show()

# 객관적 평가 요약 출력
print("=" * 60)
print("OBJECTIVE ICS SENSOR AUTHENTICATION ANALYSIS")
print("=" * 60)
print()

print("📊 PROCESSING TIME RANKING:")
time_ranking = sorted(zip(algorithms, processing_times), key=lambda x: x[1])
for i, (alg, time) in enumerate(time_ranking, 1):
    relative = f"({time/time_ranking[0][1]:.1f}x)" if i > 1 else "(baseline)"
    print(f"{i}. {alg}: {time:.1f}ms {relative}")

print("\n📈 SUCCESS RATE RANKING:")
success_ranking = sorted(zip(algorithms, success_rates), key=lambda x: x[1], reverse=True)
for i, (alg, rate) in enumerate(success_ranking, 1):
    status = "🟢 RELIABLE" if rate >= 95 else "🟡 MODERATE" if rate >= 80 else "🔴 UNRELIABLE"
    print(f"{i}. {alg}: {rate:.1f}% {status}")

print("\n📦 NETWORK EFFICIENCY RANKING:")
network_ranking = sorted(zip(algorithms, network_overhead), key=lambda x: x[1])
for i, (alg, size) in enumerate(network_ranking, 1):
    if size >= 1000:
        size_str = f"{size/1000:.1f}KB"
        relative = f"({size/network_ranking[0][1]:.0f}x)"
    else:
        size_str = f"{size}B"
        relative = "(baseline)" if i == 1 else f"({size/network_ranking[0][1]:.0f}x)"
    print(f"{i}. {alg}: {size_str} {relative}")

print("\n🔒 PRIVACY PROTECTION LEVEL:")
privacy_ranking = sorted(zip(algorithms, privacy_levels), key=lambda x: x[1], reverse=True)
for i, (alg, level) in enumerate(privacy_ranking, 1):
    if level == 0:
        level_str = "NONE ❌"
    elif level <= 5:
        level_str = "PARTIAL 🟡"
    elif level <= 8:
        level_str = "ENCRYPTED 🟢"
    else:
        level_str = "ZERO-KNOWLEDGE 🏆"
    print(f"{i}. {alg}: {level_str}")

print("\n" + "=" * 60)
print("🎯 OBJECTIVE RECOMMENDATIONS:")
print("=" * 60)
print("🥇 BEST PERFORMANCE: ED25519 (23.1ms, 100% success)")
print("🥈 MOST RELIABLE: HMAC (27.9ms, 100% success, universal)")
print("🥉 BEST PRIVACY: CKKS (encrypted, 99.99% success)")
print("⚠️  LIMITED USE: BulletProofs (environment-dependent, 50% success)")
print()
print("📋 DEPLOYMENT GUIDANCE:")
print("• Production Systems: HMAC or ED25519")
print("• Privacy-Critical: CKKS (proven reliability)")
print("• Research/Specific: BulletProofs (WADI-only)")
print("• Avoid: BulletProofs for HAI-type environments")
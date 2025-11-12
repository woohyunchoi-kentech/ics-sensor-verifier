import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'Malgun Gothic']
plt.rcParams['axes.unicode_minus'] = False

# 실제 실험 데이터 기반
algorithms = ['HMAC\n(SHA-256)', 'ED25519\n(Digital Sign)', 'BulletProofs\n(Zero-Knowledge)', 'CKKS\n(Homomorphic)']
processing_times = [27.89, 23.19, 132.43, 975.8]  # ms
success_rates = [100, 100, 50, 99.99]  # HAI+WADI 평균 (BulletProofs는 HAI 실패로 50%)
network_overhead = [32, 64, 1395, 13000]  # bytes
privacy_levels = [0, 0, 10, 8]  # 0=없음, 10=완전영지식, 8=암호화

# 색상 설정
colors = ['#2E8B57', '#4169E1', '#DC143C', '#FF8C00']

# 그림 생성
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 1. 처리 시간 비교 (로그 스케일)
bars1 = ax1.bar(algorithms, processing_times, color=colors, alpha=0.8)
ax1.set_ylabel('처리 시간 (ms)', fontsize=12)
ax1.set_title('1. 평균 처리 시간 비교 (WADI 기준)', fontsize=14, fontweight='bold')
ax1.set_yscale('log')
for i, (bar, time) in enumerate(zip(bars1, processing_times)):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             f'{time:.1f}ms', ha='center', va='bottom', fontweight='bold')

# 2. 성공률 비교
bars2 = ax2.bar(algorithms, success_rates, color=colors, alpha=0.8)
ax2.set_ylabel('성공률 (%)', fontsize=12)
ax2.set_title('2. 환경별 성공률 (HAI + WADI)', fontsize=14, fontweight='bold')
ax2.set_ylim(0, 105)
for i, (bar, rate) in enumerate(zip(bars2, success_rates)):
    height = bar.get_height()
    color = 'red' if rate < 80 else 'green'
    ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', color=color)

# 3. 네트워크 오버헤드 (로그 스케일)
bars3 = ax3.bar(algorithms, network_overhead, color=colors, alpha=0.8)
ax3.set_ylabel('네트워크 오버헤드 (bytes)', fontsize=12)
ax3.set_title('3. 증명/서명 크기 비교', fontsize=14, fontweight='bold')
ax3.set_yscale('log')
for i, (bar, size) in enumerate(zip(bars3, network_overhead)):
    height = bar.get_height()
    if size >= 1000:
        label = f'{size/1000:.1f}KB'
    else:
        label = f'{size}B'
    ax3.text(bar.get_x() + bar.get_width()/2., height * 1.1,
             label, ha='center', va='bottom', fontweight='bold')

# 4. 프라이버시 레벨 vs 성능 산점도
scatter = ax4.scatter(privacy_levels, processing_times, c=colors, s=300, alpha=0.7)
ax4.set_xlabel('프라이버시 레벨 (0=없음, 10=완전)', fontsize=12)
ax4.set_ylabel('처리 시간 (ms)', fontsize=12)
ax4.set_title('4. 프라이버시 vs 성능 트레이드오프', fontsize=14, fontweight='bold')
ax4.set_yscale('log')

# 알고리즘 라벨 추가
for i, (x, y, alg) in enumerate(zip(privacy_levels, processing_times, algorithms)):
    ax4.annotate(alg.replace('\n', ' '), (x, y), xytext=(10, 10),
                textcoords='offset points', fontsize=10, fontweight='bold')

# 전체 레이아웃 조정
plt.tight_layout()
plt.suptitle('ICS 센서 인증 알고리즘 종합 성능 비교', fontsize=16, fontweight='bold', y=0.98)
plt.subplots_adjust(top=0.93)

# 저장
plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiments/baseline_research/algorithm_comparison_chart.png',
           dpi=300, bbox_inches='tight')
plt.show()

# 객관적 평가 요약
print("=" * 60)
print("ICS 센서 인증 알고리즘 객관적 성능 분석")
print("=" * 60)
print()

print("📊 처리 시간 순위:")
time_ranking = sorted(zip(algorithms, processing_times), key=lambda x: x[1])
for i, (alg, time) in enumerate(time_ranking, 1):
    print(f"{i}. {alg.replace(chr(10), ' ')}: {time:.1f}ms")

print("\n📈 성공률 순위:")
success_ranking = sorted(zip(algorithms, success_rates), key=lambda x: x[1], reverse=True)
for i, (alg, rate) in enumerate(success_ranking, 1):
    status = "🟢" if rate >= 95 else "🟡" if rate >= 80 else "🔴"
    print(f"{i}. {alg.replace(chr(10), ' ')}: {rate:.1f}% {status}")

print("\n📦 네트워크 효율성 순위:")
network_ranking = sorted(zip(algorithms, network_overhead), key=lambda x: x[1])
for i, (alg, size) in enumerate(network_ranking, 1):
    if size >= 1000:
        size_str = f"{size/1000:.1f}KB"
    else:
        size_str = f"{size}B"
    print(f"{i}. {alg.replace(chr(10), ' ')}: {size_str}")

print("\n🔒 프라이버시 레벨:")
privacy_ranking = sorted(zip(algorithms, privacy_levels), key=lambda x: x[1], reverse=True)
for i, (alg, level) in enumerate(privacy_ranking, 1):
    if level == 0:
        level_str = "없음 ❌"
    elif level <= 5:
        level_str = "부분적 🟡"
    elif level <= 8:
        level_str = "암호화 🟢"
    else:
        level_str = "완전영지식 🏆"
    print(f"{i}. {alg.replace(chr(10), ' ')}: {level_str}")

print("\n" + "=" * 60)
print("🎯 종합 권장사항:")
print("=" * 60)
print("• 성능 우선: HMAC 또는 ED25519")
print("• 프라이버시 필요: CKKS (안정성) 또는 BulletProofs (특수용도)")
print("• 범용성: HMAC (가장 안정적)")
print("• 주의: BulletProofs는 환경 의존성 높음 (HAI 환경 실패)")
#!/usr/bin/env python3
"""
HAI Bulletproof 빠른 시각화 도구
전처리→암호화→전송→검증 상세 타이밍 분석
"""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI 없는 백엔드 사용

print("🎨 HAI Bulletproof 시각화 자료 생성 중...")

# 1. 상세 타이밍 분해 차트 생성
def create_timing_breakdown():
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    # 실제 HAI Bulletproof 타이밍 데이터
    methods = ['HMAC', 'CKKS', 'HAI Bulletproof']
    
    # 각 단계별 시간 (ms)
    preprocessing = [0.05, 2.0, 1.0]
    encryption = [0.1, 25.0, 2.1]
    transmission = [0.05, 1.5, 1.3]
    verification = [0.1, 120.0, 13.8]
    
    width = 0.6
    x_pos = np.arange(len(methods))
    
    # 스택 바 차트
    bars1 = ax.bar(x_pos, preprocessing, width, label='전처리시간', color='#FFB6C1', alpha=0.8)
    bars2 = ax.bar(x_pos, encryption, width, bottom=preprocessing, label='암호화시간', color='#87CEEB', alpha=0.8)
    bars3 = ax.bar(x_pos, transmission, width, 
                   bottom=np.array(preprocessing) + np.array(encryption), 
                   label='전송시간', color='#98FB98', alpha=0.8)
    bars4 = ax.bar(x_pos, verification, width,
                   bottom=np.array(preprocessing) + np.array(encryption) + np.array(transmission),
                   label='검증시간', color='#DDA0DD', alpha=0.8)
    
    # 총 시간 표시
    total_times = [p+e+t+v for p,e,t,v in zip(preprocessing, encryption, transmission, verification)]
    for i, total in enumerate(total_times):
        ax.text(i, total + 5, f'{total:.1f}ms', ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax.set_title('HAI Bulletproof 상세 처리시간 분해 분석\n전처리→암호화→전송→검증 (Perfect Success 16,000/16,000)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.set_ylabel('처리 시간 (ms)', fontsize=12, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(methods, fontsize=11)
    ax.set_yscale('log')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 목표선 추가
    ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, linewidth=2, label='목표 (50ms)')
    
    plt.tight_layout()
    plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/hai_timing_breakdown.png', 
               dpi=300, bbox_inches='tight')
    print("✅ 타이밍 분해 차트 생성 완료: hai_timing_breakdown.png")
    plt.close()

# 2. 성능 비교 차트 생성
def create_performance_summary():
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
    
    methods = ['HMAC', 'CKKS', 'HAI Bulletproof']
    
    # 1. 프라이버시 레벨
    privacy = [0, 50, 100]
    bars1 = ax1.bar(methods, privacy, color=['#FF6B6B', '#4ECDC4', '#45B7D1'], alpha=0.8)
    ax1.set_title('프라이버시 보장 수준', fontweight='bold')
    ax1.set_ylabel('프라이버시 레벨 (%)')
    for bar, value in zip(bars1, privacy):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                f'{value}%', ha='center', va='bottom', fontweight='bold')
    
    # 2. 증명 크기
    sizes = [0.032, 8.5, 1.3]
    bars2 = ax2.bar(methods, sizes, color=['#FF6B6B', '#4ECDC4', '#45B7D1'], alpha=0.8)
    ax2.set_title('증명 크기', fontweight='bold')
    ax2.set_ylabel('크기 (KB)')
    ax2.set_yscale('log')
    for bar, value in zip(bars2, sizes):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() * 1.5,
                f'{value}KB', ha='center', va='bottom', fontweight='bold')
    
    # 3. 총 처리시간
    total_times = [0.3, 148.5, 18.2]
    bars3 = ax3.bar(methods, total_times, color=['#FF6B6B', '#4ECDC4', '#45B7D1'], alpha=0.8)
    ax3.set_title('총 처리시간', fontweight='bold')
    ax3.set_ylabel('처리시간 (ms)')
    ax3.set_yscale('log')
    ax3.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='목표 (50ms)')
    for bar, value in zip(bars3, total_times):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() * 1.5,
                f'{value}ms', ha='center', va='bottom', fontweight='bold')
    ax3.legend()
    
    # 4. 처리율
    throughput = [1000, 8, 33.2]
    bars4 = ax4.bar(methods, throughput, color=['#FF6B6B', '#4ECDC4', '#45B7D1'], alpha=0.8)
    ax4.set_title('처리율', fontweight='bold')
    ax4.set_ylabel('증명/초')
    ax4.set_yscale('log')
    for bar, value in zip(bars4, throughput):
        ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() * 1.5,
                f'{value:.1f}/s', ha='center', va='bottom', fontweight='bold')
    
    plt.suptitle('HAI Bulletproof 종합 성능 비교\n완전한 영지식 + 실시간 성능 달성', 
                fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/hai_performance_summary.png', 
               dpi=300, bbox_inches='tight')
    print("✅ 성능 비교 차트 생성 완료: hai_performance_summary.png")
    plt.close()

# 3. 16조건 성공률 차트
def create_success_chart():
    fig, ax = plt.subplots(1, 1, figsize=(15, 6))
    
    # 16개 조건 (모두 100% 성공)
    conditions = [f'Phase{i//4+1}-{freq}Hz' for i in range(16) 
                 for freq in [1, 2, 10, 100] if i%4 == [1,2,10,100].index(freq)]
    success_rates = [100.0] * 16
    
    # 색상 구분 (Phase별)
    colors = ['#2E8B57']*4 + ['#4682B4']*4 + ['#FF8C00']*4 + ['#DC143C']*4
    
    bars = ax.bar(range(16), success_rates, color=colors, alpha=0.8, edgecolor='black')
    
    # 100% 성공 표시
    for i, bar in enumerate(bars):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
               '100%', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    ax.set_title('HAI Bulletproof 16개 조건 완전 성공\n16,000개 증명 100% 검증 성공', 
                fontsize=14, fontweight='bold')
    ax.set_ylabel('성공률 (%)', fontweight='bold')
    ax.set_xlabel('실험 조건', fontweight='bold')
    ax.set_xticks(range(16))
    ax.set_xticklabels([f'P{i//4+1}-{[1,2,10,100][i%4]}Hz' for i in range(16)], rotation=45)
    ax.set_ylim(95, 105)
    ax.axhline(y=100, color='gold', linestyle='-', linewidth=3, label='Perfect Success')
    ax.axhline(y=95, color='red', linestyle=':', linewidth=2, label='Target (95%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/hai_success_chart.png', 
               dpi=300, bbox_inches='tight')
    print("✅ 16조건 성공률 차트 생성 완료: hai_success_chart.png")
    plt.close()

if __name__ == "__main__":
    create_timing_breakdown()
    create_performance_summary()
    create_success_chart()
    
    print("\n🎉 모든 시각화 자료 생성 완료!")
    print("\n📁 생성된 파일들:")
    print("• hai_timing_breakdown.png - 상세 처리시간 분해")
    print("• hai_performance_summary.png - 종합 성능 비교") 
    print("• hai_success_chart.png - 16조건 성공률")
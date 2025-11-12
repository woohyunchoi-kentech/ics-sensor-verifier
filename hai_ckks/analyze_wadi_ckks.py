#!/usr/bin/env python3
"""
WADI CKKS Performance Analysis Script
Analyzes 16 conditions (4 sensor counts × 4 frequencies) from CKKS experimental data
"""

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_wadi_ckks_performance():
    """Analyze WADI CKKS performance data for all 16 conditions"""
    
    # Load the data
    data_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/experiment_results/ckks_perf_wadi_20250828_125554/complete_performance_data.csv"
    
    print("Loading WADI CKKS performance data...")
    df = pd.read_csv(data_path)
    
    # Filter for WADI dataset only (though it seems all data is WADI based on sample)
    df = df[df['dataset'] == 'WADI']
    
    print(f"Total records loaded: {len(df)}")
    print(f"Unique sensor counts: {sorted(df['sensor_count'].unique())}")
    print(f"Unique frequencies: {sorted(df['frequency'].unique())}")
    
    # Define the 16 conditions
    sensor_counts = [1, 10, 50, 100]
    frequencies = [1, 2, 10, 100]
    
    results = []
    
    print("\nAnalyzing performance for 16 conditions...")
    print("=" * 80)
    
    for sensor_count in sensor_counts:
        for frequency in frequencies:
            # Filter data for current condition
            condition_data = df[(df['sensor_count'] == sensor_count) & (df['frequency'] == frequency)]
            
            if len(condition_data) == 0:
                print(f"WARNING: No data found for {sensor_count} sensors @ {frequency}Hz")
                continue
                
            # Calculate metrics
            total_requests = len(condition_data)
            successful_requests = len(condition_data[condition_data['success'] == True])
            success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
            
            # Only analyze successful requests for timing metrics
            success_data = condition_data[condition_data['success'] == True]
            
            if len(success_data) == 0:
                print(f"WARNING: No successful requests for {sensor_count} sensors @ {frequency}Hz")
                continue
            
            # Encryption time analysis
            enc_mean = success_data['encryption_time_ms'].mean()
            enc_min = success_data['encryption_time_ms'].min()
            enc_max = success_data['encryption_time_ms'].max()
            enc_std = success_data['encryption_time_ms'].std()
            
            # Decryption time analysis
            dec_mean = success_data['decryption_time_ms'].mean()
            dec_min = success_data['decryption_time_ms'].min()
            dec_max = success_data['decryption_time_ms'].max()
            dec_std = success_data['decryption_time_ms'].std()
            
            # Network RTT analysis
            rtt_mean = success_data['network_rtt_ms'].mean()
            rtt_min = success_data['network_rtt_ms'].min()
            rtt_max = success_data['network_rtt_ms'].max()
            rtt_std = success_data['network_rtt_ms'].std()
            
            # Store results
            result = {
                'sensor_count': sensor_count,
                'frequency': frequency,
                'condition': f"{sensor_count}센서 @ {frequency}Hz",
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'enc_mean': enc_mean,
                'enc_min': enc_min,
                'enc_max': enc_max,
                'enc_std': enc_std,
                'dec_mean': dec_mean,
                'dec_min': dec_min,
                'dec_max': dec_max,
                'dec_std': dec_std,
                'rtt_mean': rtt_mean,
                'rtt_min': rtt_min,
                'rtt_max': rtt_max,
                'rtt_std': rtt_std
            }
            
            results.append(result)
            
            print(f"{result['condition']}: {total_requests} requests, {success_rate:.1f}% success")
    
    return results

def generate_markdown_report(results):
    """Generate detailed markdown report for all conditions"""
    
    markdown_content = """# WADI CKKS 실험 성능 분석 결과

## 실험 개요
- **데이터셋**: WADI (Water Distribution)
- **암호화 방식**: CKKS (Homomorphic Encryption)
- **테스트 조건**: 16개 조건 (4개 센서 수 × 4개 주파수)
- **분석 지표**: 암호화/복호화 시간, 네트워크 RTT, 성공률, 성능 안정성

## 조건별 세부 성능 분석

### 1. 전체 요약 테이블

| 센서 수 | 주파수 | 요청 수 | 성공률(%) | 평균 암호화(ms) | 평균 복호화(ms) | 평균 RTT(ms) |
|---------|--------|---------|-----------|----------------|----------------|--------------|"""
    
    # Add summary table rows
    for result in results:
        markdown_content += f"\n| {result['sensor_count']} | {result['frequency']}Hz | {result['total_requests']} | {result['success_rate']:.1f} | {result['enc_mean']:.2f} | {result['dec_mean']:.2f} | {result['rtt_mean']:.2f} |"
    
    markdown_content += """

### 2. 암호화 시간 상세 분석

| 조건 | 평균(ms) | 최소(ms) | 최대(ms) | 표준편차(ms) | 안정성 |
|------|----------|----------|----------|--------------|--------|"""
    
    for result in results:
        stability = "높음" if result['enc_std'] < result['enc_mean'] * 0.3 else "보통" if result['enc_std'] < result['enc_mean'] * 0.5 else "낮음"
        markdown_content += f"\n| {result['condition']} | {result['enc_mean']:.2f} | {result['enc_min']:.2f} | {result['enc_max']:.2f} | {result['enc_std']:.2f} | {stability} |"
    
    markdown_content += """

### 3. 복호화 시간 상세 분석

| 조건 | 평균(ms) | 최소(ms) | 최대(ms) | 표준편차(ms) | 안정성 |
|------|----------|----------|----------|--------------|--------|"""
    
    for result in results:
        stability = "높음" if result['dec_std'] < result['dec_mean'] * 0.3 else "보통" if result['dec_std'] < result['dec_mean'] * 0.5 else "낮음"
        markdown_content += f"\n| {result['condition']} | {result['dec_mean']:.2f} | {result['dec_min']:.2f} | {result['dec_max']:.2f} | {result['dec_std']:.2f} | {stability} |"
    
    markdown_content += """

### 4. 네트워크 RTT 상세 분석

| 조건 | 평균(ms) | 최소(ms) | 최대(ms) | 표준편차(ms) | 안정성 |
|------|----------|----------|----------|--------------|--------|"""
    
    for result in results:
        stability = "높음" if result['rtt_std'] < result['rtt_mean'] * 0.3 else "보통" if result['rtt_std'] < result['rtt_mean'] * 0.5 else "낮음"
        markdown_content += f"\n| {result['condition']} | {result['rtt_mean']:.2f} | {result['rtt_min']:.2f} | {result['rtt_max']:.2f} | {result['rtt_std']:.2f} | {stability} |"
    
    markdown_content += """

### 5. 센서 수별 성능 비교

#### 1Hz 주파수에서의 센서 수별 비교
"""
    
    # Group by frequency for comparison
    freq_1hz = [r for r in results if r['frequency'] == 1]
    if freq_1hz:
        markdown_content += """
| 센서 수 | 암호화 시간(ms) | 복호화 시간(ms) | RTT(ms) | 성공률(%) |
|---------|----------------|----------------|---------|-----------|"""
        for result in freq_1hz:
            markdown_content += f"\n| {result['sensor_count']} | {result['enc_mean']:.2f} | {result['dec_mean']:.2f} | {result['rtt_mean']:.2f} | {result['success_rate']:.1f} |"
    
    markdown_content += """

#### 100Hz 주파수에서의 센서 수별 비교
"""
    
    freq_100hz = [r for r in results if r['frequency'] == 100]
    if freq_100hz:
        markdown_content += """
| 센서 수 | 암호화 시간(ms) | 복호화 시간(ms) | RTT(ms) | 성공률(%) |
|---------|----------------|----------------|---------|-----------|"""
        for result in freq_100hz:
            markdown_content += f"\n| {result['sensor_count']} | {result['enc_mean']:.2f} | {result['dec_mean']:.2f} | {result['rtt_mean']:.2f} | {result['success_rate']:.1f} |"
    
    markdown_content += """

### 6. 주요 관찰 사항

#### 성능 경향 분석
"""
    
    # Calculate some insights
    best_enc_condition = min(results, key=lambda x: x['enc_mean'])
    worst_enc_condition = max(results, key=lambda x: x['enc_mean'])
    best_success_condition = max(results, key=lambda x: x['success_rate'])
    
    markdown_content += f"""
- **최고 암호화 성능**: {best_enc_condition['condition']} ({best_enc_condition['enc_mean']:.2f}ms 평균)
- **최저 암호화 성능**: {worst_enc_condition['condition']} ({worst_enc_condition['enc_mean']:.2f}ms 평균)  
- **최고 성공률**: {best_success_condition['condition']} ({best_success_condition['success_rate']:.1f}%)

#### 성능 안정성 분석
"""
    
    # Analyze stability
    stable_conditions = [r for r in results if r['enc_std'] < r['enc_mean'] * 0.3]
    unstable_conditions = [r for r in results if r['enc_std'] >= r['enc_mean'] * 0.5]
    
    markdown_content += f"""
- **안정적인 조건** ({len(stable_conditions)}개): 표준편차가 평균의 30% 미만
- **불안정한 조건** ({len(unstable_conditions)}개): 표준편차가 평균의 50% 이상

#### 센서 수와 주파수의 영향
"""
    
    # Calculate averages by sensor count and frequency
    sensor_avg = {}
    freq_avg = {}
    
    for sensor_count in [1, 10, 50, 100]:
        sensor_results = [r for r in results if r['sensor_count'] == sensor_count]
        if sensor_results:
            sensor_avg[sensor_count] = sum(r['enc_mean'] for r in sensor_results) / len(sensor_results)
    
    for frequency in [1, 2, 10, 100]:
        freq_results = [r for r in results if r['frequency'] == frequency]
        if freq_results:
            freq_avg[frequency] = sum(r['enc_mean'] for r in freq_results) / len(freq_results)
    
    if sensor_avg:
        markdown_content += f"""
- **센서 수별 평균 암호화 시간**:
"""
        for sensor_count, avg_time in sensor_avg.items():
            markdown_content += f"  - {sensor_count}센서: {avg_time:.2f}ms\n"
    
    if freq_avg:
        markdown_content += f"""
- **주파수별 평균 암호화 시간**:
"""
        for frequency, avg_time in freq_avg.items():
            markdown_content += f"  - {frequency}Hz: {avg_time:.2f}ms\n"
    
    markdown_content += """

### 7. 실험 결론

1. **확장성**: 센서 수 증가에 따른 성능 변화 패턴 분석
2. **주파수 영향**: 데이터 전송 주파수가 암호화 성능에 미치는 영향  
3. **안정성**: 각 조건에서의 성능 일관성 평가
4. **실용성**: 실제 산업 환경 적용을 위한 권장 조건

---
*분석 날짜: 2025-09-01*  
*데이터 소스: WADI CKKS 실험 결과 (20250828_125554)*
"""
    
    return markdown_content

if __name__ == "__main__":
    try:
        # Perform analysis
        results = analyze_wadi_ckks_performance()
        
        if not results:
            print("No results found. Please check the data file.")
            exit(1)
        
        print(f"\nAnalysis completed for {len(results)} conditions.")
        
        # Generate markdown report
        print("\nGenerating markdown report...")
        markdown_report = generate_markdown_report(results)
        
        # Save to file
        output_path = "/Users/woohyunchoi/Downloads/archive/experiment_project/ics-sensor-privacy/hai_ckks/WADI_CKKS_DETAILED_ANALYSIS.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        print(f"Detailed analysis report saved to: {output_path}")
        print("\nReport preview (first few lines):")
        print("=" * 80)
        print(markdown_report[:1000] + "...")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
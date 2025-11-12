#!/usr/bin/env python3
"""
WADI HMAC 실험 결과 테이블 생성기
================================
센서별, 주파수별 상세 타이밍 테이블 생성
"""

import pandas as pd
import glob
import numpy as np

def load_and_process_data():
    """모든 실험 데이터 로드 및 처리"""
    summary_files = glob.glob("./results/*/*summary.csv")
    summary_files.extend(glob.glob("./results/*summary.csv"))
    
    all_data = []
    for file in summary_files:
        try:
            df = pd.read_csv(file)
            all_data.append(df)
            print(f"✅ Loaded: {file} - {len(df)} rows")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if not all_data:
        return pd.DataFrame()
        
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['sensor_count', 'frequency'])
    
    return combined_df

def generate_detailed_timing_table():
    """상세 타이밍 테이블 생성"""
    df = load_and_process_data()
    if df.empty:
        print("No data available")
        return
    
    print("\n" + "="*120)
    print("📊 WADI HMAC 센서별 주파수별 상세 타이밍 분석 테이블")
    print("="*120)
    
    # 테이블 헤더
    headers = [
        "센서수", "주파수(Hz)", "총요청수", 
        "HMAC생성(ms)", "HMAC검증(ms)", "네트워크RTT(ms)",
        "직렬화(ms)", "성공률(%)", "검증률(%)",
        "CPU사용률(%)", "메모리(MB)", "데이터량(MB)"
    ]
    
    # 헤더 출력
    print(f"{'|'.join(f'{h:>12}' for h in headers)}")
    print("|" + "-"*12 + "|" * (len(headers) - 1) + "-"*12 + "|")
    
    # 데이터 정렬 (센서수, 주파수 순)
    df_sorted = df.sort_values(['sensor_count', 'frequency'])
    
    total_requests = 0
    total_generation_time = 0
    total_network_time = 0
    
    for _, row in df_sorted.iterrows():
        # 기본 정보
        sensor_count = int(row['sensor_count'])
        frequency = int(row['frequency'])
        
        # 요청 수 (여러 컬럼명 중 존재하는 것 사용)
        requests = row.get('total_requests', row.get('total_samples', 0))
        if pd.isna(requests):
            requests = 0
        requests = int(requests)
        
        # HMAC 생성 시간
        hmac_gen = row.get('avg_hmac_generation_ms', np.nan)
        hmac_gen_str = f"{hmac_gen:.4f}" if not pd.isna(hmac_gen) else "N/A"
        
        # HMAC 검증 시간
        hmac_ver = row.get('avg_hmac_verification_ms', np.nan)
        hmac_ver_str = f"{hmac_ver:.4f}" if not pd.isna(hmac_ver) else "N/A"
        
        # 네트워크 RTT
        network_rtt = row.get('avg_network_rtt_ms', row.get('avg_network_simulation_ms', np.nan))
        network_str = f"{network_rtt:.2f}" if not pd.isna(network_rtt) else "N/A"
        
        # 직렬화 시간
        serialization = row.get('avg_serialization_ms', np.nan)
        serial_str = f"{serialization:.4f}" if not pd.isna(serialization) else "N/A"
        
        # 성공률, 검증률
        success_rate = row.get('success_rate', np.nan)
        success_str = f"{success_rate:.1f}" if not pd.isna(success_rate) else "N/A"
        
        verification_rate = row.get('verification_rate', np.nan)
        verify_str = f"{verification_rate:.1f}" if not pd.isna(verification_rate) else "N/A"
        
        # CPU, 메모리
        cpu_usage = row.get('avg_cpu_usage', np.nan)
        cpu_str = f"{cpu_usage:.2f}" if not pd.isna(cpu_usage) else "N/A"
        
        memory_mb = row.get('avg_memory_mb', np.nan)
        memory_str = f"{memory_mb:.0f}" if not pd.isna(memory_mb) else "N/A"
        
        # 데이터량
        data_mb = row.get('total_data_mb', row.get('total_data_processed_mb', np.nan))
        data_str = f"{data_mb:.3f}" if not pd.isna(data_mb) else "N/A"
        
        # 통계 누적
        total_requests += requests
        if not pd.isna(hmac_gen):
            total_generation_time += hmac_gen * requests
        if not pd.isna(network_rtt):
            total_network_time += network_rtt * requests
        
        # 테이블 행 출력
        values = [
            sensor_count, frequency, f"{requests:,}",
            hmac_gen_str, hmac_ver_str, network_str,
            serial_str, success_str, verify_str,
            cpu_str, memory_str, data_str
        ]
        
        print(f"{'|'.join(f'{str(v):>12}' for v in values)}")
    
    # 구분선
    print("|" + "-"*12 + "|" * (len(headers) - 1) + "-"*12 + "|")
    
    return df_sorted

def generate_summary_statistics(df):
    """요약 통계 생성"""
    print("\n📈 요약 통계")
    print("-" * 60)
    
    # 기본 통계
    print(f"총 테스트 조건: {len(df)}개")
    print(f"센서 범위: {df['sensor_count'].min():.0f} ~ {df['sensor_count'].max():.0f}개")
    print(f"주파수 범위: {df['frequency'].min():.0f} ~ {df['frequency'].max():.0f}Hz")
    
    # 요청 수 통계
    total_requests_col = df.get('total_requests', df.get('total_samples', pd.Series([0])))
    total_requests = total_requests_col.sum()
    print(f"총 처리 요청: {total_requests:,}개")
    
    # 성능 통계
    hmac_gen_data = df.dropna(subset=['avg_hmac_generation_ms'])
    if not hmac_gen_data.empty:
        print(f"\n🔐 HMAC 암호화 성능:")
        print(f"  평균: {hmac_gen_data['avg_hmac_generation_ms'].mean():.4f}ms")
        print(f"  최고: {hmac_gen_data['avg_hmac_generation_ms'].min():.4f}ms")
        print(f"  최저: {hmac_gen_data['avg_hmac_generation_ms'].max():.4f}ms")
        print(f"  편차: {hmac_gen_data['avg_hmac_generation_ms'].std():.4f}ms")
    
    # 검증 성능
    hmac_ver_data = df.dropna(subset=['avg_hmac_verification_ms'])
    if not hmac_ver_data.empty:
        print(f"\n🔍 HMAC 검증 성능:")
        print(f"  평균: {hmac_ver_data['avg_hmac_verification_ms'].mean():.4f}ms")
        gen_ver_ratio = hmac_ver_data['avg_hmac_verification_ms'].mean() / hmac_gen_data['avg_hmac_generation_ms'].mean()
        print(f"  검증/생성 비율: {gen_ver_ratio:.2f}x")
    
    # 네트워크 성능
    network_data = df.dropna(subset=['avg_network_rtt_ms'])
    if not network_data.empty:
        print(f"\n🌐 네트워크 전송 성능:")
        print(f"  평균 RTT: {network_data['avg_network_rtt_ms'].mean():.2f}ms")
        crypto_network_ratio = network_data['avg_network_rtt_ms'].mean() / hmac_gen_data['avg_hmac_generation_ms'].mean()
        print(f"  네트워크/암호화 비율: {crypto_network_ratio:.0f}x")
    
    # 시스템 리소스
    cpu_data = df.dropna(subset=['avg_cpu_usage'])
    memory_data = df.dropna(subset=['avg_memory_mb'])
    if not cpu_data.empty and not memory_data.empty:
        print(f"\n💻 시스템 리소스:")
        print(f"  평균 CPU 사용률: {cpu_data['avg_cpu_usage'].mean():.2f}%")
        print(f"  평균 메모리 사용량: {memory_data['avg_memory_mb'].mean():.0f}MB")
    
    # 성공률 통계
    success_data = df.dropna(subset=['success_rate'])
    verify_data = df.dropna(subset=['verification_rate'])
    if not success_data.empty:
        print(f"\n✅ 신뢰성 지표:")
        print(f"  평균 성공률: {success_data['success_rate'].mean():.1f}%")
        if not verify_data.empty:
            print(f"  평균 검증률: {verify_data['verification_rate'].mean():.1f}%")

def generate_performance_ranking(df):
    """성능 순위 테이블"""
    print(f"\n🏆 성능 순위")
    print("-" * 80)
    
    # HMAC 생성 성능 순위
    hmac_data = df.dropna(subset=['avg_hmac_generation_ms']).copy()
    if not hmac_data.empty:
        hmac_data = hmac_data.sort_values('avg_hmac_generation_ms')
        print(f"\n🥇 HMAC 생성 속도 순위:")
        print(f"{'순위':<4} {'센서수':<8} {'주파수':<8} {'생성시간(ms)':<12} {'상대성능':<10}")
        print("-" * 50)
        
        fastest_time = hmac_data['avg_hmac_generation_ms'].iloc[0]
        for i, (_, row) in enumerate(hmac_data.iterrows()):
            sensor = int(row['sensor_count'])
            freq = int(row['frequency'])
            time = row['avg_hmac_generation_ms']
            ratio = time / fastest_time
            print(f"{i+1:<4} {sensor:<8} {freq}Hz{'':<3} {time:<12.4f} {ratio:.2f}x{'':<4}")
    
    # 처리량 순위 (요청 수 기준)
    request_cols = ['total_requests', 'total_samples']
    request_col = None
    for col in request_cols:
        if col in df.columns and not df[col].isna().all():
            request_col = col
            break
    
    if request_col:
        throughput_data = df.dropna(subset=[request_col]).copy()
        if not throughput_data.empty:
            throughput_data = throughput_data.sort_values(request_col, ascending=False)
            print(f"\n🚀 처리량 순위:")
            print(f"{'순위':<4} {'센서수':<8} {'주파수':<8} {'총요청수':<12} {'비율':<10}")
            print("-" * 50)
            
            max_requests = throughput_data[request_col].iloc[0]
            for i, (_, row) in enumerate(throughput_data.iterrows()):
                sensor = int(row['sensor_count'])
                freq = int(row['frequency'])
                requests = int(row[request_col])
                ratio = requests / max_requests
                print(f"{i+1:<4} {sensor:<8} {freq}Hz{'':<3} {requests:<12,} {ratio:.1%}{'':<4}")

if __name__ == "__main__":
    print("🚀 WADI HMAC 타이밍 테이블 생성")
    
    df = generate_detailed_timing_table()
    if df is not None and not df.empty:
        generate_summary_statistics(df)
        generate_performance_ranking(df)
        print("\n✅ 테이블 생성 완료!")
    else:
        print("❌ 분석할 데이터가 없습니다.")
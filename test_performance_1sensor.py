#!/usr/bin/env python3
"""
1개 센서 성능 테스트: 초당 1회 요청, 10번 테스트
실제 운영 환경을 시뮬레이션한 안정성 및 성능 테스트
"""

import json
import time
import requests
import pandas as pd
from crypto.ckks_baseline import CKKSBaseline
import statistics

def send_to_server_for_verification(proof_data, ckks, server_url='http://192.168.0.11:8085'):
    """서버에 CKKS 증명 데이터를 보내고 검증 결과를 받음"""
    try:
        verify_url = f"{server_url}/api/v1/ckks/verify"
        
        print(f"   Context ID 사용: {proof_data['context_id']}")
        
        verification_request = {
            "sensor_id": "DM-PIT01", 
            "timestamp": proof_data['timestamp'],
            "encrypted_data": proof_data['encrypted_data'],
            "context": proof_data['context_id'],
            "algorithm": "CKKS"
        }
        
        print(f"📤 서버에 검증 요청 전송 중...")
        print(f"   요청 시간: {time.strftime('%H:%M:%S')}")
        
        response = requests.post(
            verify_url,
            json=verification_request,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"   응답 시간: {time.strftime('%H:%M:%S')}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 서버 응답 받음")
            
            if not result.get('success', False):
                print(f"   ⚠️ 서버 검증 실패: {result.get('error_message', 'Unknown error')}")
            
            return {
                "success": result.get('success', False),
                "decrypted_value": result.get('decrypted_value'),
                "verification_time_ms": result.get('processing_time_ms'),
                "server_response": result
            }
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return {
                "success": False,
                "error": f"Server returned {response.status_code}",
                "response": response.text
            }
            
    except Exception as e:
        print(f"❌ 요청 오류: {e}")
        return {
            "success": False,
            "error": f"Request error: {str(e)}"
        }

def main():
    """1센서 성능 테스트 메인 함수"""
    print("🚀 1센서 성능 테스트 (1 req/sec, 10회)")
    print("=" * 60)
    
    # CKKS 클라이언트 초기화
    ckks = CKKSBaseline()
    server_url = 'http://192.168.0.11:8085'
    
    # 서버 full-context 로드
    print("🔑 서버 full-context 로드 중...")
    if not ckks.load_server_public_key_from_api(server_url):
        print("❌ Context 로드 실패")
        return
    
    # HAI 데이터에서 테스트 값 로드 (10개)
    print("\n📊 HAI 센서 데이터 로드 중...")
    csv_path = 'data/hai/haiend-23.05/end-train1.csv'
    df = pd.read_csv(csv_path)
    sensor_id = 'DM-PIT01'
    sensor_data = df[sensor_id].dropna().clip(0.0, 3.0)
    test_values = sensor_data.sample(n=10).tolist()
    
    print(f"테스트 값: {[f'{v:.6f}' for v in test_values]}")
    
    # 결과 저장용
    all_results = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_type": "performance_1sensor_1rps",
        "server_url": server_url,
        "sensor_id": sensor_id,
        "total_tests": len(test_values),
        "interval_seconds": 1.0,
        "successful_verifications": 0,
        "test_details": [],
        "performance_metrics": {}
    }
    
    # 성능 메트릭 수집용
    encryption_times = []
    server_response_times = []
    total_request_times = []
    accuracies = []
    
    print(f"\n🔬 성능 테스트 시작 (10회, 1초 간격)")
    print("=" * 60)
    
    start_test_time = time.time()
    
    # 각 값에 대해 1초 간격으로 테스트
    for i, value in enumerate(test_values, 1):
        test_start_time = time.time()
        
        print(f"\n🔬 테스트 {i}/10")
        print(f"   원본 값: {value:.6f}")
        print(f"   테스트 시작: {time.strftime('%H:%M:%S')}")
        
        try:
            # 1. CKKS 암호화
            encryption_start = time.perf_counter()
            proof_data = ckks.generate_proof(value)
            encryption_time = (time.perf_counter() - encryption_start) * 1000
            encryption_times.append(encryption_time)
            print(f"   ✅ 암호화 완료 ({encryption_time:.1f}ms)")
            
            # 2. 서버에 검증 요청
            request_start = time.perf_counter()
            verification_result = send_to_server_for_verification(proof_data, ckks, server_url)
            request_time = (time.perf_counter() - request_start) * 1000
            total_request_times.append(request_time)
            
            # 3. 결과 처리
            test_result = {
                "test_num": i,
                "original_value": value,
                "encryption_time_ms": encryption_time,
                "request_time_ms": request_time,
                "encrypted_size_bytes": proof_data['encrypted_size_bytes'],
                "server_verification": verification_result,
                "test_timestamp": time.time()
            }
            
            if verification_result['success']:
                all_results['successful_verifications'] += 1
                decrypted = verification_result.get('decrypted_value', 'N/A')
                server_time = verification_result.get('verification_time_ms', 0)
                server_response_times.append(server_time)
                
                if decrypted != 'N/A':
                    error = abs(decrypted - value)
                    error_pct = (error / value) * 100 if value != 0 else 0
                    accuracies.append(error_pct)
                    
                    print(f"   📊 복호화 값: {decrypted:.6f}")
                    print(f"   📏 오차: {error:.6f} ({error_pct:.4f}%)")
                    print(f"   ⚡ 서버 처리: {server_time:.2f}ms")
                    
                    test_result['error'] = error
                    test_result['error_percentage'] = error_pct
                    test_result['decrypted_value'] = decrypted
            else:
                print(f"   ❌ 검증 실패: {verification_result.get('error')}")
            
            all_results['test_details'].append(test_result)
            
            # 성능 메트릭 실시간 출력
            print(f"   📈 총 소요시간: {request_time:.1f}ms")
            print(f"   🕒 테스트 진행: {i}/10 ({(i/10)*100:.0f}%)")
            
        except Exception as e:
            print(f"   ❌ 테스트 실패: {e}")
            test_result = {
                "test_num": i,
                "original_value": value,
                "error": str(e),
                "success": False
            }
            all_results['test_details'].append(test_result)
        
        # 1초 간격 유지 (다음 테스트가 있는 경우)
        if i < len(test_values):
            elapsed = time.time() - test_start_time
            wait_time = max(0, 1.0 - elapsed)
            if wait_time > 0:
                print(f"   ⏳ {wait_time:.1f}초 대기 중...")
                time.sleep(wait_time)
    
    # 전체 테스트 소요 시간
    total_test_time = time.time() - start_test_time
    
    # 성능 메트릭 계산
    if encryption_times:
        all_results['performance_metrics'] = {
            "total_duration_seconds": total_test_time,
            "average_encryption_time_ms": statistics.mean(encryption_times),
            "max_encryption_time_ms": max(encryption_times),
            "min_encryption_time_ms": min(encryption_times),
            "average_request_time_ms": statistics.mean(total_request_times),
            "max_request_time_ms": max(total_request_times),
            "min_request_time_ms": min(total_request_times),
            "requests_per_second": len(test_values) / total_test_time,
        }
        
        if server_response_times:
            all_results['performance_metrics'].update({
                "average_server_time_ms": statistics.mean(server_response_times),
                "max_server_time_ms": max(server_response_times),
                "min_server_time_ms": min(server_response_times),
            })
            
        if accuracies:
            all_results['performance_metrics'].update({
                "average_accuracy_error_pct": statistics.mean(accuracies),
                "max_accuracy_error_pct": max(accuracies),
                "min_accuracy_error_pct": min(accuracies),
            })
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("📈 최종 성능 결과")
    print(f"총 테스트: {all_results['total_tests']}")
    print(f"서버 검증 성공: {all_results['successful_verifications']}")
    print(f"성공률: {(all_results['successful_verifications']/all_results['total_tests']*100):.1f}%")
    print(f"총 소요시간: {total_test_time:.1f}초")
    print(f"실제 처리속도: {len(test_values)/total_test_time:.2f} req/sec")
    
    if encryption_times:
        metrics = all_results['performance_metrics']
        print(f"\n⚡ 성능 메트릭:")
        print(f"  암호화 시간: 평균 {metrics['average_encryption_time_ms']:.1f}ms")
        print(f"  요청 시간: 평균 {metrics['average_request_time_ms']:.1f}ms")
        if server_response_times:
            print(f"  서버 처리: 평균 {metrics['average_server_time_ms']:.1f}ms")
        if accuracies:
            print(f"  정확도 오차: 평균 {metrics['average_accuracy_error_pct']:.3f}%")
    
    # 결과 파일로 저장
    timestamp = int(time.time())
    output_file = f"performance_1sensor_1rps_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 결과 저장됨: {output_file}")
    print("\n🎉 1센서 성능 테스트 완료!")

if __name__ == "__main__":
    main()
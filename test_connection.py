#!/usr/bin/env python3
"""
Connection Test for ICS Sensor Privacy System
다양한 알고리즘으로 서버 연결 및 암호화 테스트
"""

import argparse
import json
import time
import pandas as pd
from pathlib import Path


def test_ckks_connection(samples=10, sensor='DM-PIT01', server_port=8085):
    """CKKS 암호화 연결 테스트"""
    print(f"🔐 CKKS 연결 테스트 시작")
    print(f"   센서: {sensor}")
    print(f"   샘플 수: {samples}")
    print(f"   서버 포트: {server_port}")
    
    try:
        from crypto.ckks_baseline import CKKSBaseline
        
        # CKKS 클라이언트 초기화
        ckks = CKKSBaseline()
        server_url = f'http://192.168.0.11:{server_port}'
        
        print(f"🔑 서버 공개키 로드 중... ({server_url})")
        if not ckks.load_server_public_key_from_api(server_url):
            return {"success": False, "error": "공개키 로드 실패"}
        
        # HAI 데이터 로드
        print(f"📊 {sensor} 센서 데이터 로드 중...")
        csv_path = 'data/hai/haiend-23.05/end-train1.csv'
        df = pd.read_csv(csv_path)
        
        if sensor not in df.columns:
            return {"success": False, "error": f"센서 {sensor}가 HAI 데이터에 없음"}
        
        sensor_data = df[sensor].dropna().clip(0.0, 3.0)
        test_values = sensor_data.sample(n=samples).tolist()
        
        # 테스트 실행
        results = {
            "algorithm": "CKKS",
            "sensor_id": sensor,
            "server_url": server_url,
            "timestamp": int(time.time()),
            "total_tests": samples,
            "successful_tests": 0,
            "server_responses": []
        }
        
        for i, value in enumerate(test_values, 1):
            print(f"📤 테스트 {i}/{samples}: {value:.6f}")
            
            try:
                start_time = time.perf_counter()
                proof_data = ckks.generate_proof(value)
                generation_time = (time.perf_counter() - start_time) * 1000
                
                test_result = {
                    "test_num": i,
                    "value": value,
                    "generation_time": generation_time / 1000,  # 초 단위
                    "processing_time_ms": generation_time,
                    "encrypted_size_bytes": proof_data['encrypted_size_bytes'],
                    "success": True
                }
                
                results['server_responses'].append(test_result)
                results['successful_tests'] += 1
                print(f"   ✅ 성공 ({generation_time:.1f}ms)")
                
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                test_result = {
                    "test_num": i,
                    "value": value,
                    "error": str(e),
                    "success": False
                }
                results['server_responses'].append(test_result)
        
        # 결과 저장
        timestamp = int(time.time())
        output_file = f"connection_test_ckks_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        success_rate = results['successful_tests'] / results['total_tests'] * 100
        print(f"\n📈 CKKS 테스트 완료")
        print(f"   성공률: {success_rate:.1f}%")
        print(f"   결과 저장: {output_file}")
        
        return {"success": True, "results": results, "output_file": output_file}
        
    except ImportError:
        return {"success": False, "error": "TenSEAL이 설치되지 않음 - CKKS 사용 불가"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_bulletproofs_connection(samples=10, sensor='DM-PIT01'):
    """Bulletproofs 연결 테스트"""
    print(f"🛡️ Bulletproofs 연결 테스트 시작")
    print(f"   센서: {sensor}")
    print(f"   샘플 수: {samples}")
    
    try:
        from crypto.bulletproofs import BulletproofGenerator
        
        # Bulletproof 클라이언트 초기화
        bp = BulletproofGenerator(bit_length=32)
        
        # HAI 데이터 로드
        print(f"📊 {sensor} 센서 데이터 로드 중...")
        csv_path = 'data/hai/haiend-23.05/end-train1.csv'
        df = pd.read_csv(csv_path)
        
        if sensor not in df.columns:
            return {"success": False, "error": f"센서 {sensor}가 HAI 데이터에 없음"}
        
        sensor_data = df[sensor].dropna().clip(0.0, 3.0)
        test_values = sensor_data.sample(n=samples).tolist()
        
        # 테스트 실행
        results = {
            "algorithm": "Bulletproofs",
            "sensor_id": sensor,
            "timestamp": int(time.time()),
            "total_tests": samples,
            "successful_tests": 0,
            "test_results": []
        }
        
        for i, value in enumerate(test_values, 1):
            print(f"📤 테스트 {i}/{samples}: {value:.6f}")
            
            try:
                start_time = time.perf_counter()
                proof_data = bp.generate_range_proof(value, min_val=0, max_val=3)
                generation_time = (time.perf_counter() - start_time) * 1000
                
                test_result = {
                    "test_num": i,
                    "value": value,
                    "generation_time_ms": generation_time,
                    "proof_size_bytes": len(str(proof_data.get('proof', ''))),
                    "success": True
                }
                
                results['test_results'].append(test_result)
                results['successful_tests'] += 1
                print(f"   ✅ 성공 ({generation_time:.1f}ms)")
                
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                test_result = {
                    "test_num": i,
                    "value": value,
                    "error": str(e),
                    "success": False
                }
                results['test_results'].append(test_result)
        
        # 결과 저장
        timestamp = int(time.time())
        output_file = f"connection_test_bulletproofs_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        success_rate = results['successful_tests'] / results['total_tests'] * 100
        print(f"\n📈 Bulletproofs 테스트 완료")
        print(f"   성공률: {success_rate:.1f}%")
        print(f"   결과 저장: {output_file}")
        
        return {"success": True, "results": results, "output_file": output_file}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_hmac_connection(samples=10, sensor='DM-PIT01'):
    """HMAC 연결 테스트"""
    print(f"🔑 HMAC 연결 테스트 시작")
    print(f"   센서: {sensor}")
    print(f"   샘플 수: {samples}")
    
    try:
        from crypto.hmac_baseline import HMACBaseline
        
        # HMAC 클라이언트 초기화
        hmac = HMACBaseline()
        
        # HAI 데이터 로드
        print(f"📊 {sensor} 센서 데이터 로드 중...")
        csv_path = 'data/hai/haiend-23.05/end-train1.csv'
        df = pd.read_csv(csv_path)
        
        if sensor not in df.columns:
            return {"success": False, "error": f"센서 {sensor}가 HAI 데이터에 없음"}
        
        sensor_data = df[sensor].dropna().clip(0.0, 3.0)
        test_values = sensor_data.sample(n=samples).tolist()
        
        # 테스트 실행
        results = {
            "algorithm": "HMAC",
            "sensor_id": sensor,
            "timestamp": int(time.time()),
            "total_tests": samples,
            "successful_tests": 0,
            "test_results": []
        }
        
        for i, value in enumerate(test_values, 1):
            print(f"📤 테스트 {i}/{samples}: {value:.6f}")
            
            try:
                start_time = time.perf_counter()
                proof_data = hmac.generate_proof(value)
                generation_time = (time.perf_counter() - start_time) * 1000
                
                test_result = {
                    "test_num": i,
                    "value": value,
                    "generation_time_ms": generation_time,
                    "hmac_size_bytes": len(proof_data.get('hmac', '')),
                    "success": True
                }
                
                results['test_results'].append(test_result)
                results['successful_tests'] += 1
                print(f"   ✅ 성공 ({generation_time:.1f}ms)")
                
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                test_result = {
                    "test_num": i,
                    "value": value,
                    "error": str(e),
                    "success": False
                }
                results['test_results'].append(test_result)
        
        # 결과 저장
        timestamp = int(time.time())
        output_file = f"connection_test_hmac_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        success_rate = results['successful_tests'] / results['total_tests'] * 100
        print(f"\n📈 HMAC 테스트 완료")
        print(f"   성공률: {success_rate:.1f}%")
        print(f"   결과 저장: {output_file}")
        
        return {"success": True, "results": results, "output_file": output_file}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_ed25519_connection(samples=10, sensor='DM-PIT01'):
    """Ed25519 연결 테스트"""
    print(f"📝 Ed25519 연결 테스트 시작")
    print(f"   센서: {sensor}")
    print(f"   샘플 수: {samples}")
    
    try:
        from crypto.ed25519_baseline import Ed25519Baseline
        
        # Ed25519 클라이언트 초기화
        ed = Ed25519Baseline()
        
        # HAI 데이터 로드
        print(f"📊 {sensor} 센서 데이터 로드 중...")
        csv_path = 'data/hai/haiend-23.05/end-train1.csv'
        df = pd.read_csv(csv_path)
        
        if sensor not in df.columns:
            return {"success": False, "error": f"센서 {sensor}가 HAI 데이터에 없음"}
        
        sensor_data = df[sensor].dropna().clip(0.0, 3.0)
        test_values = sensor_data.sample(n=samples).tolist()
        
        # 테스트 실행
        results = {
            "algorithm": "Ed25519",
            "sensor_id": sensor,
            "timestamp": int(time.time()),
            "total_tests": samples,
            "successful_tests": 0,
            "test_results": []
        }
        
        for i, value in enumerate(test_values, 1):
            print(f"📤 테스트 {i}/{samples}: {value:.6f}")
            
            try:
                start_time = time.perf_counter()
                proof_data = ed.generate_proof(value)
                generation_time = (time.perf_counter() - start_time) * 1000
                
                test_result = {
                    "test_num": i,
                    "value": value,
                    "generation_time_ms": generation_time,
                    "signature_size_bytes": len(proof_data.get('signature', '')),
                    "success": True
                }
                
                results['test_results'].append(test_result)
                results['successful_tests'] += 1
                print(f"   ✅ 성공 ({generation_time:.1f}ms)")
                
            except Exception as e:
                print(f"   ❌ 실패: {e}")
                test_result = {
                    "test_num": i,
                    "value": value,
                    "error": str(e),
                    "success": False
                }
                results['test_results'].append(test_result)
        
        # 결과 저장
        timestamp = int(time.time())
        output_file = f"connection_test_ed25519_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        success_rate = results['successful_tests'] / results['total_tests'] * 100
        print(f"\n📈 Ed25519 테스트 완료")
        print(f"   성공률: {success_rate:.1f}%")
        print(f"   결과 저장: {output_file}")
        
        return {"success": True, "results": results, "output_file": output_file}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Connection Test for ICS Sensor Privacy System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  %(prog)s --algorithm ckks --samples 10
  %(prog)s --algorithm bulletproofs --sensor DM-FIT01 --samples 5
  %(prog)s --algorithm hmac --samples 20
  %(prog)s --algorithm ed25519 --samples 15
        """
    )
    
    parser.add_argument(
        '--algorithm',
        choices=['ckks', 'bulletproofs', 'hmac', 'ed25519'],
        required=True,
        help='테스트할 암호화 알고리즘'
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=10,
        help='테스트 샘플 수 (기본값: 10)'
    )
    
    parser.add_argument(
        '--sensor',
        default='DM-PIT01',
        help='HAI 센서 ID (기본값: DM-PIT01)'
    )
    
    parser.add_argument(
        '--server-port',
        type=int,
        default=8085,
        help='CKKS 서버 포트 (기본값: 8085)'
    )
    
    args = parser.parse_args()
    
    print("🧪 ICS 센서 프라이버시 연결 테스트")
    print("=" * 60)
    
    # 알고리즘별 테스트 실행
    if args.algorithm == 'ckks':
        result = test_ckks_connection(args.samples, args.sensor, args.server_port)
    elif args.algorithm == 'bulletproofs':
        result = test_bulletproofs_connection(args.samples, args.sensor)
    elif args.algorithm == 'hmac':
        result = test_hmac_connection(args.samples, args.sensor)
    elif args.algorithm == 'ed25519':
        result = test_ed25519_connection(args.samples, args.sensor)
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    if result["success"]:
        print(f"✅ {args.algorithm.upper()} 연결 테스트 성공")
        print(f"📁 결과 파일: {result.get('output_file', 'N/A')}")
    else:
        print(f"❌ {args.algorithm.upper()} 연결 테스트 실패")
        print(f"오류: {result['error']}")


if __name__ == "__main__":
    main()
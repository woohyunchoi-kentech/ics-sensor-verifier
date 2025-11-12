#!/usr/bin/env python3
"""
Reverse Engineer Server Requirements
"""

import requests
import json
from petlib.ec import EcGroup
from petlib.bn import Bn
from hashlib import sha256

def test_minimal():
    """최소한의 데이터로 테스트"""
    minimal_data = {
        "commitment": "02" + "00" * 32,
        "proof": {},
        "range_min": 0,
        "range_max": 1
    }
    
    result = send_test_request(minimal_data)
    print(f"  Minimal data: {result.get('error_message', 'No error')}")

def test_mathematical_consistency():
    """수학적 일관성 테스트"""
    
    group = EcGroup(714)
    g = group.generator()
    order = group.order()
    
    # Simple generators
    h_hash = sha256(g.export() + b"bulletproof_h").digest()
    h_scalar = Bn.from_binary(h_hash) % order
    h = h_scalar * g
    
    # Value = 0, small blinding
    v = Bn(0)
    gamma = Bn(1)
    V = v * g + gamma * h
    
    # Simple proof components
    A = g
    S = h
    T1 = g
    T2 = g
    
    # Simple challenges
    y = Bn(2)
    z = Bn(3)
    x = Bn(4)
    
    # Calculate for main equation
    n = 1
    delta_yz = (z - z*z) * Bn(1) - z*z*z * Bn(1)
    delta_yz = delta_yz % order
    
    t_hat = (z*z*v + delta_yz + x + x*x) % order
    tau_x = (z*z*gamma) % order
    
    test_data = {
        "commitment": V.export().hex(),
        "proof": {
            "A": A.export().hex(),
            "S": S.export().hex(),
            "T1": T1.export().hex(),
            "T2": T2.export().hex(), 
            "tau_x": tau_x.hex(),
            "mu": Bn(1).hex(),
            "t": t_hat.hex(),
            "inner_product_proof": {
                "L": [g.export().hex()],
                "R": [h.export().hex()],
                "a": Bn(0).hex(),
                "b": Bn(1).hex()
            }
        },
        "range_min": 0,
        "range_max": 1
    }
    
    print(f"  Math values: v={v}, gamma={gamma}, delta={delta_yz}")
    
    result = send_test_request(test_data)
    verified = result.get('verified', False)
    error = result.get('error_message', 'No error')
    
    print(f"  Result: {'SUCCESS' if verified else 'FAIL'}")
    print(f"  Error: {error}")
    
    return verified

def send_test_request(data):
    """서버에 테스트 요청 보내기"""
    try:
        response = requests.post(
            'http://192.168.0.11:8085/api/v1/verify/bulletproof',
            json=data,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Connection: {e}"}

def main():
    print("🔍 Reverse Engineering Server Requirements")
    print("=" * 60)
    
    print("\n🧪 Test 1: Minimal data")
    test_minimal()
    
    print("\n🧪 Test 2: Mathematical consistency") 
    test_mathematical_consistency()

if __name__ == "__main__":
    main()

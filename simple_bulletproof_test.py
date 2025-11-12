#!/usr/bin/env python3
"""
Simple Bulletproof server test
"""

import requests
import json

def test_server_compatibility():
    """Test different Bulletproof formats with server"""
    
    # Test 1: Minimal format
    test_data = {
        "commitment": "0344a159697dd765730cc9a3d8401f0130b4b2d71a120c3ffc11c1d6e151288df5",
        "proof": {
            "A": "0368f80f288e58e1e42127c928ae9e5ca4ef9bc70ad754d5373fa6832d3d17b4fc",
            "S": "02cc2b44dae7da3e24d9e228dc36efbdbd6c16fb7a527013d8f3dbc2edefcd68ac",
            "T1": "03814b852f2ff6d828e7a3f83eabc357ac2090c4ed162199c997a3ad4b04bb4b52",
            "T2": "03eac7594fd693d586f1de7c58ee630e71129cf650b0e0516daaf959f615ca408c",
            "tau_x": "123456",
            "mu": "789abc",
            "t": "def123",
            "inner_product_proof": {
                "L": ["024145beec2a5184f29900850b1bf758762a9691ed301c4a652cb2b9cd5e071823"],
                "R": ["02f3497c8cc95e640664020dd9e8fd7cd4658caaec5e4f2619301b6c590ab1cd0f"],
                "a": "abcdef",
                "b": "123456"
            }
        },
        "range_min": 0,
        "range_max": 100
    }
    
    print("🔧 Simple Bulletproof Server Test")
    print("=" * 50)
    
    try:
        response = requests.post(
            'http://192.168.0.11:8085/api/v1/verify/bulletproof',
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Server Response:")
            print(f"  verified: {result.get('verified', False)}")
            print(f"  success: {result.get('success', False)}")
            print(f"  algorithm: {result.get('algorithm', 'N/A')}")
            print(f"  processing_time_ms: {result.get('processing_time_ms', 0):.2f}")
            print(f"  error_message: {result.get('error_message', 'None')}")
            print(f"  details: {result.get('details', {})}")
            
            # Test with external format
            print("\n🔧 Testing external format...")
            external_format = {
                "T_1": "03814b852f2ff6d828e7a3f83eabc357ac2090c4ed162199c997a3ad4b04bb4b52",
                "T_2": "03eac7594fd693d586f1de7c58ee630e71129cf650b0e0516daaf959f615ca408c",
                "l_vec": [1, 0, 1, 0],
                "r_vec": [0, 1, 0, 1], 
                "challenges": [123, 456, 789],
                "range": [0, 100],
                "metadata": {"test": True}
            }
            
            response2 = requests.post(
                'http://192.168.0.11:8085/api/v1/verify/bulletproof',
                json=external_format,
                timeout=10
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ External Format Response:")
                print(f"  verified: {result2.get('verified', False)}")
                print(f"  error_message: {result2.get('error_message', 'None')}")
                print(f"  format_detected: {result2.get('details', {}).get('format_detected', 'N/A')}")
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_server_compatibility()
#!/usr/bin/env python3

import socket

# 간단한 서버 연결 테스트
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('192.168.0.11', 8085))
    sock.close()
    
    if result == 0:
        print('✅ 서버 연결됨 (192.168.0.11:8085)')
    else:
        print('❌ 서버 연결 실패 - 서버를 켜주세요')
        
except Exception as e:
    print(f'오류: {e}')
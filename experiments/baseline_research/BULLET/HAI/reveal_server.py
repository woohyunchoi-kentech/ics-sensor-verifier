#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAW Value Reveal Server (Selective Disclosure)

센서 클라이언트로부터 RAW 값을 받아 로컬 버퍼에 저장하고,
외부 서버의 요청에 따라 선택적으로 RAW 값을 공개하는 서버입니다.

Dependencies:
    pip3 install flask

Usage:
    python3 reveal_server.py

API Endpoints:
    POST /api/v1/store-raw   - 센서 클라이언트가 RAW 값을 저장
    POST /api/v1/reveal-raw  - 외부 서버가 RAW 값을 조회
    GET  /api/v1/buffer/stats - 버퍼 통계 조회
"""

import threading
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import OrderedDict

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Error: 'flask' library not found. Install with: pip3 install flask")
    exit(1)


class RAWValueBuffer:
    """로컬 메모리에 RAW 값을 TTL과 함께 저장하는 버퍼"""

    def __init__(self, ttl_seconds: int = 600):  # 기본 10분
        """
        Args:
            ttl_seconds: Time-To-Live in seconds (default: 600 = 10 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.buffer = OrderedDict()  # {(sensor_id, nonce): {event_ts, raw_value, stored_at, expires_at}}
        self.lock = threading.Lock()
        self._start_cleanup_thread()

    def store(self, sensor_id: str, event_ts: int, nonce: str, raw_value: float):
        """RAW 값을 버퍼에 저장"""
        key = (sensor_id, nonce)
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.ttl_seconds)

        with self.lock:
            self.buffer[key] = {
                "event_ts": event_ts,
                "raw_value": raw_value,
                "stored_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "expires_timestamp": expires_at.timestamp()
            }

        print(f"[STORE] sensor={sensor_id}, ts={event_ts}, nonce={nonce[:16]}..., value={raw_value:.6f}")

    def retrieve(self, sensor_id: str, nonce: str) -> Optional[Dict]:
        """버퍼에서 RAW 값을 검색"""
        key = (sensor_id, nonce)

        with self.lock:
            if key not in self.buffer:
                return None

            entry = self.buffer[key]

            # 만료 확인
            if datetime.now().timestamp() > entry["expires_timestamp"]:
                del self.buffer[key]
                return {"error": "expired"}

            return {
                "event_ts": entry["event_ts"],
                "raw_value": entry["raw_value"],
                "stored_at": entry["stored_at"],
                "expires_at": entry["expires_at"]
            }

    def cleanup_expired(self):
        """만료된 항목 제거"""
        now = datetime.now().timestamp()
        with self.lock:
            expired_keys = [k for k, v in self.buffer.items() if now > v["expires_timestamp"]]
            for key in expired_keys:
                del self.buffer[key]

            if expired_keys:
                print(f"[CLEANUP] {len(expired_keys)}개 만료 항목 삭제")

    def _cleanup_worker(self):
        """백그라운드 정리 스레드"""
        import time
        while True:
            time.sleep(60)  # 1분마다 실행
            self.cleanup_expired()

    def _start_cleanup_thread(self):
        """정리 스레드 시작"""
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()

    def get_stats(self) -> Dict:
        """버퍼 통계"""
        with self.lock:
            return {
                "total_entries": len(self.buffer),
                "ttl_seconds": self.ttl_seconds
            }


def create_app(buffer: RAWValueBuffer):
    """Flask 앱 생성"""
    app = Flask(__name__)
    app.logger.disabled = True  # Flask 기본 로그 비활성화

    @app.route('/api/v1/store-raw', methods=['POST'])
    def store_raw():
        """센서 클라이언트로부터 RAW 값을 받아 버퍼에 저장"""
        data = request.json

        if not data:
            return jsonify({"error": "invalid-request", "message": "No JSON body"}), 400

        sensor_id = data.get("sensor_id")
        event_ts = data.get("event_ts")
        nonce = data.get("nonce")
        raw_value = data.get("raw_value")

        if not all([sensor_id is not None, event_ts is not None, nonce is not None, raw_value is not None]):
            return jsonify({
                "error": "missing-fields",
                "message": "Required: sensor_id, event_ts, nonce, raw_value"
            }), 400

        # 버퍼에 저장
        buffer.store(sensor_id, event_ts, nonce, raw_value)

        return jsonify({"ok": True, "message": "Stored"}), 200

    @app.route('/api/v1/reveal-raw', methods=['POST'])
    def reveal_raw():
        """외부 서버의 요청에 따라 RAW 값 공개"""
        data = request.json

        if not data:
            return jsonify({"error": "invalid-request", "message": "No JSON body"}), 400

        sensor_id = data.get("sensor_id")
        nonce = data.get("nonce")

        if not all([sensor_id, nonce]):
            return jsonify({
                "error": "missing-fields",
                "message": "Required: sensor_id, nonce"
            }), 400

        print(f"[REVEAL] 요청: sensor={sensor_id}, nonce={nonce[:16]}...")

        # 버퍼에서 검색
        result = buffer.retrieve(sensor_id, nonce)

        if result is None:
            print(f"[REVEAL] 결과: not-found")
            return jsonify({"ok": False, "reason": "not-found"}), 404

        if "error" in result:
            print(f"[REVEAL] 결과: expired")
            return jsonify({"ok": False, "reason": "expired"}), 410  # 410 Gone (expired)

        print(f"[REVEAL] 결과: 성공, value={result['raw_value']:.6f}")
        return jsonify({
            "ok": True,
            "sensor_id": sensor_id,
            "event_ts": result["event_ts"],
            "nonce": nonce,
            "raw_value": result["raw_value"],
            "stored_at": result["stored_at"],
            "expires_at": result["expires_at"]
        }), 200

    @app.route('/api/v1/buffer/stats', methods=['GET'])
    def buffer_stats():
        """버퍼 통계"""
        return jsonify(buffer.get_stats()), 200

    return app


def main():
    parser = argparse.ArgumentParser(description="RAW Value Reveal Server")
    parser.add_argument("--port", type=int, default=9000, help="Server port (default: 9000)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--ttl", type=int, default=600, help="RAW value TTL in seconds (default: 600 = 10 min)")

    args = parser.parse_args()

    print("=" * 70)
    print("  RAW Value Reveal Server (Selective Disclosure)")
    print("=" * 70)
    print(f"[INIT] Host: {args.host}")
    print(f"[INIT] Port: {args.port}")
    print(f"[INIT] TTL: {args.ttl} seconds ({args.ttl/60:.1f} minutes)")
    print("=" * 70)
    print(f"[INFO] Store API:  POST http://{args.host}:{args.port}/api/v1/store-raw")
    print(f"[INFO] Reveal API: POST http://{args.host}:{args.port}/api/v1/reveal-raw")
    print(f"[INFO] Stats API:  GET  http://{args.host}:{args.port}/api/v1/buffer/stats")
    print("=" * 70)
    print()

    # 버퍼 생성
    buffer = RAWValueBuffer(ttl_seconds=args.ttl)

    # Flask 앱 생성 및 실행
    app = create_app(buffer)
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()

import json
import os
import socket
import time
import urllib.request

TIMEOUT = int(os.getenv("TIMEOUT_S", "120"))
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
MINIO_URL = os.getenv("MINIO_URL", "http://minio:9000")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def tcp_ok(host: str, port: int) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        return True
    except Exception:
        return False


def main() -> int:
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        ok_redis = tcp_ok(REDIS_HOST, REDIS_PORT)
        ok_qdrant = http_ok(QDRANT_URL.rstrip("/") + "/healthz")
        ok_minio = http_ok(MINIO_URL.rstrip("/") + "/minio/health/live")
        if ok_redis and ok_qdrant and ok_minio:
            print(json.dumps({"ready": True, "redis": ok_redis, "qdrant": ok_qdrant, "minio": ok_minio}))
            return 0
        time.sleep(2)
    print(json.dumps({"ready": False, "redis": ok_redis, "qdrant": ok_qdrant, "minio": ok_minio}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

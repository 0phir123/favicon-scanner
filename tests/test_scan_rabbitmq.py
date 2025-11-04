# tests/test_scan_rabbitmq.py
import os
import time

import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
RABBIT_HEALTH_URL = os.getenv("RABBIT_HEALTH_URL", "http://127.0.0.1:15673")  # host-mapped
SCAN_TARGET = os.getenv("SCAN_TARGET", "rabbitmq")  # container DNS
SCAN_PORT = int(os.getenv("SCAN_PORT", "15672"))


def wait_for_rabbit(timeout_sec: int = 120):
    deadline = time.time() + timeout_sec
    last = None
    while time.time() < deadline:
        try:
            last = requests.get(RABBIT_HEALTH_URL, timeout=2)
            if last.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(
        f"RabbitMQ UI never became ready at {RABBIT_HEALTH_URL} (last={getattr(last, 'status_code', None)})"
    )


def test_scan_detects_rabbitmq():
    wait_for_rabbit()
    r = requests.post(
        f"{API_URL}/scan", json={"targets": [SCAN_TARGET], "ports": [SCAN_PORT]}, timeout=30
    )
    assert r.status_code in {200, 202}, r.text
    scan_id = r.json()["scan_id"]

    for _ in range(90):
        time.sleep(1)
        resp = requests.get(f"{API_URL}/scan/{scan_id}", timeout=10)
        data = resp.json()
        if data.get("status") == "done":
            result = data.get("result", {})
            break
    else:
        raise AssertionError("Scan never reached status=done")

    assert "RabbitMQ" in str(result), f"No RabbitMQ match found in:\n{result}"


def test_api_health():
    r = requests.get(f"{API_URL}/docs", timeout=5)
    assert r.status_code == 200

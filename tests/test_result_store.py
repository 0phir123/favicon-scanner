# /tests/test_result_store.py
from __future__ import annotations
from app.adapters.system.redis_result_store import RedisResultStore

def test_store_lifecycle() -> None:
    # Requires a local Redis on db 15
    url = "redis://localhost:6379/15"
    s = RedisResultStore(url, prefix="testscan")
    s.set_pending("id1")
    assert s.get("id1")["status"] == "pending"
    s.set_result("id1", {"ok": True})
    v = s.get("id1")
    assert v["status"] == "done" and v["result"]["ok"] is True

# /app/adapters/system/redis_result_store.py
from __future__ import annotations
import json
import logging
from typing import Any

import redis

LOG = logging.getLogger("adapter.result_store.redis")

class RedisResultStore:
    def __init__(self, redis_url: str, prefix: str = "scan") -> None:
        self._r = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix

    def _key(self, scan_id: str) -> str:
        return f"{self._prefix}:{scan_id}"

    def set_pending(self, scan_id: str) -> None:
        self._r.hset(self._key(scan_id), mapping={"status": "pending"})
        LOG.info("store.set_pending", extra={"extra": {"scan_id": scan_id}})

    def set_error(self, scan_id: str, error: str) -> None:
        self._r.hset(self._key(scan_id), mapping={"status": "error", "error": error})
        LOG.warning("store.set_error", extra={"extra": {"scan_id": scan_id, "error": error}})

    def set_result(self, scan_id: str, result: dict) -> None:
        self._r.hset(self._key(scan_id), mapping={"status": "done", "result": json.dumps(result)})
        LOG.info("store.set_result", extra={"extra": {"scan_id": scan_id}})

    def get(self, scan_id: str) -> dict | None:
        data = self._r.hgetall(self._key(scan_id))
        if not data:
            return None
        out: dict[str, Any] = {"status": data.get("status")}
        if "error" in data:
            out["error"] = data["error"]
        if "result" in data and data["result"] is not None:
            try:
                out["result"] = json.loads(data["result"])
            except Exception:
                out["result"] = None
        return out

# tests/test_redis_result_store.py
import pytest

from app.adapters.system.redis_result_store import RedisResultStore


class FakeRedis:
    def __init__(self):
        self.db = {}

    def hset(self, key, mapping):
        self.db[key] = mapping

    def hgetall(self, key):
        return self.db.get(key, {})


@pytest.fixture
def store():
    r = FakeRedis()
    s = RedisResultStore.__new__(RedisResultStore)
    s._r = r
    s._prefix = "scan"
    return s, r


def test_set_and_get(store):
    s, r = store
    s.set_pending("id1")
    s.set_error("id2", "boom")
    s.set_result("id3", {"data": "x"})
    assert r.hgetall("scan:id1")["status"] == "pending"
    assert r.hgetall("scan:id2")["status"] == "error"
    assert r.hgetall("scan:id3")["status"] == "done" or "result" in r.hgetall("scan:id3")

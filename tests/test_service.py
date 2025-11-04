# /tests/test_service.py
from __future__ import annotations
import hashlib
import pytest
from app.domain.scan_service import ScanRequestDTO, ScanService
from app.config import settings

class FakeRepo:
    def __init__(self, hit_md5: str) -> None:
        self.hit = hit_md5
    def lookup_md5(self, md5: str) -> list[dict]:
        return [{"name": "Hit"}] if md5 == self.hit else []

class FakeFetcher:
    async def fetch(self, scheme: str, host: str, port: int, path: str):
        return 200, b"FAKEFAVICON", f"{scheme}://{host}:{port}{path}"

class FakeExpander:
    def expand(self, inputs, max_targets):  # type: ignore[no-untyped-def]
        return inputs

@pytest.mark.asyncio
async def test_service_happy_path() -> None:
    md5 = hashlib.md5(b"FAKEFAVICON").hexdigest()
    svc = ScanService(FakeRepo(md5), FakeFetcher(), FakeExpander(), default_ports=[80], max_targets=100)
    resp = await svc.scan(ScanRequestDTO(targets=["localhost"], ports=[80]))
    assert len(resp.results) == 1
    assert resp.results[0].matches[0]["name"] == "Hit"

@pytest.mark.asyncio
async def test_job_size_cap() -> None:
    old = settings.MAX_SOCKETS_PER_JOB
    settings.MAX_SOCKETS_PER_JOB = 1
    try:
        svc = ScanService(FakeRepo("dead"), FakeFetcher(), FakeExpander(), default_ports=[80, 443], max_targets=100)
        with pytest.raises(ValueError):
            await svc.scan(ScanRequestDTO(targets=["a","b"], ports=[80,443]))
    finally:
        settings.MAX_SOCKETS_PER_JOB = old

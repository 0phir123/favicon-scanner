# /app/ports/http_fetcher.py
from __future__ import annotations

from typing import Protocol


class HTTPFetcherPort(Protocol):
    async def fetch(self, scheme: str, host: str, port: int, path: str) -> tuple[int, bytes, str]:
        """Fetch bytes; return (status, body, final_url)."""

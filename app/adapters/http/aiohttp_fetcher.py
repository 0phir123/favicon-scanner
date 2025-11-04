# /app/adapters/http/aiohttp_fetcher.py
from __future__ import annotations

import asyncio
import logging

import aiohttp

from app.config import settings

LOG = logging.getLogger("adapter.http_fetcher")


class AiohttpFetcher:
    """
    Loop-aware aiohttp fetcher.
    Celery tasks use asyncio.run (new loop per task). We detect loop changes and
    rebuild the connector/session so we never hold a session tied to a closed loop.
    """

    def __init__(self) -> None:
        self._connector: aiohttp.TCPConnector | None = None
        self._timeout = aiohttp.ClientTimeout(total=settings.TIMEOUT_SECONDS)
        self._session: aiohttp.ClientSession | None = None
        self._sem = asyncio.Semaphore(settings.CONCURRENCY)
        self._max_bytes = settings.MAX_BYTES
        self._retries = settings.RETRIES
        self._backoff_ms = settings.RETRY_BACKOFF_MS
        self._loop: asyncio.AbstractEventLoop | None = None  # track owning loop

    async def _ensure_session(self) -> aiohttp.ClientSession:
        loop = asyncio.get_running_loop()
        loop_changed = self._loop is not None and self._loop is not loop

        if loop_changed:
            # old session belonged to a different (likely closed) loop -> close & reset
            try:
                if self._session and not self._session.closed:
                    await self._session.close()
            finally:
                self._session = None
                self._connector = None
                self._loop = None

        if self._session is None or self._session.closed:
            # (re)create for current loop
            self._connector = aiohttp.TCPConnector(
                limit=settings.CONCURRENCY,
                limit_per_host=settings.PER_HOST_LIMIT,
            )
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=self._timeout,
                raise_for_status=False,
            )
            self._loop = loop

        return self._session

    async def fetch(self, scheme: str, host: str, port: int, path: str) -> tuple[int, bytes, str]:
        """
        Returns (status, body, final_url). Enforces global/per-host limits, timeout,
        max bytes, and retries with exponential backoff.
        """
        url = f"{scheme}://{host}{'' if port in (80, 443) else f':{port}'}{path}"

        async with self._sem:
            sess = await self._ensure_session()
            attempt = 0
            while True:
                try:
                    LOG.info(
                        "fetching", extra={"extra": {"url": url, "verify_tls": settings.VERIFY_TLS}}
                    )
                    async with sess.get(url, ssl=settings.VERIFY_TLS, allow_redirects=True) as resp:
                        body = bytearray()
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            body.extend(chunk)
                            if len(body) > self._max_bytes:
                                LOG.warning(
                                    "body_truncated",
                                    extra={"extra": {"url": url, "max": self._max_bytes}},
                                )
                                break
                        return resp.status, bytes(body[: self._max_bytes]), str(resp.url)
                except (TimeoutError, aiohttp.ClientError):
                    if attempt >= self._retries:
                        raise
                    await asyncio.sleep((self._backoff_ms / 1000.0) * (2**attempt))
                    attempt += 1

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._connector = None
            self._loop = None

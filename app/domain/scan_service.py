# /app/domain/scan_service.py
from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from app.adapters.system.logging_cfg import configure_logger
from app.config import settings
from app.ports.fingerprint_repository import FingerprintRepositoryPort
from app.ports.http_fetcher import HTTPFetcherPort
from app.ports.target_expander import TargetExpanderPort

LOG = logging.getLogger("scan_service")
configure_logger()

# ==== DTOs ====


@dataclass(slots=True)
class ScanRequestDTO:
    targets: list[str]
    ports: list[int]


@dataclass(slots=True)
class ScanResultDTO:
    target: str  # "host:port"
    scheme: str
    byte_len: int
    md5: str | None
    status: int
    final_url: str | None
    matches: list[dict]


@dataclass(slots=True)
class ScanResponseDTO:
    results: list[ScanResultDTO]
    errors: list[dict]


# ==== Service ====


class ScanService:
    """Application service orchestrating scanning flow over injected ports."""

    def __init__(
        self,
        repo: FingerprintRepositoryPort,
        fetcher: HTTPFetcherPort,
        expander: TargetExpanderPort,
        *,
        default_ports: Sequence[int],
        max_targets: int,
    ) -> None:
        self.repo = repo
        self.fetcher = fetcher
        self.expander = expander
        self.default_ports = list(default_ports)
        self.max_targets = max_targets

    # --- small helpers to keep scan() simple ---

    @staticmethod
    def _scheme_for(port: int) -> str:
        # Default to http unless explicitly 443
        return "https" if port == 443 else "http"

    @staticmethod
    def _resolve_ports(req: ScanRequestDTO, default_ports: list[int]) -> list[int]:
        return req.ports or default_ports

    def _expand_hosts(self, targets: list[str]) -> list[str]:
        return self.expander.expand(targets, self.max_targets)

    @staticmethod
    def _validate_job_size(hosts_count: int, ports_count: int) -> None:
        total_pairs = hosts_count * ports_count
        if total_pairs > settings.MAX_SOCKETS_PER_JOB:
            raise ValueError(f"job too large: {total_pairs} > {settings.MAX_SOCKETS_PER_JOB}")

    async def _fetch_favicon(
        self, scheme: str, host: str, port: int
    ) -> tuple[int, bytes | None, str | None]:
        async with asyncio.timeout(settings.TIMEOUT_SECONDS + 0.5):
            return await self.fetcher.fetch(scheme, host, port, "/favicon.ico")

    def _make_result(
        self,
        *,
        host: str,
        port: int,
        scheme: str,
        status: int,
        body: bytes | None,
        final_url: str | None,
    ) -> ScanResultDTO:
        md5: str | None = None
        matches: list[dict] = []

        if 200 <= status < 300 and body:
            md5 = hashlib.md5(body).hexdigest()
            LOG.info("favicon.md5", extra={"extra": {"md5": md5}})
            matches = self.repo.lookup_md5(md5)

        return ScanResultDTO(
            target=f"{host}:{port}",
            scheme=scheme,
            byte_len=len(body) if body else 0,
            md5=md5,
            status=status,
            final_url=final_url,
            matches=matches,
        )

    async def _probe_one(
        self,
        host: str,
        port: int,
        results: list[ScanResultDTO],
        errors: list[dict],
        sem: asyncio.Semaphore,
    ) -> None:
        scheme = self._scheme_for(port)
        target = f"{host}:{port}"
        async with sem:
            try:
                status, body, final_url = await self._fetch_favicon(scheme, host, port)
            except Exception as e:
                errors.append({"target": target, "error": type(e).__name__, "detail": str(e)})
                return

            results.append(
                self._make_result(
                    host=host,
                    port=port,
                    scheme=scheme,
                    status=status,
                    body=body,
                    final_url=final_url,
                )
            )

    # --- primary entrypoint kept linear/simple ---

    async def scan(self, req: ScanRequestDTO) -> ScanResponseDTO:
        ports = self._resolve_ports(req, self.default_ports)
        hosts = self._expand_hosts(req.targets)
        self._validate_job_size(len(hosts), len(ports))

        results: list[ScanResultDTO] = []
        errors: list[dict] = []
        sem = asyncio.Semaphore(settings.CONCURRENCY)

        async with asyncio.TaskGroup() as tg:
            for h in hosts:
                for p in ports:
                    tg.create_task(self._probe_one(h, p, results, errors, sem))

        return ScanResponseDTO(results=results, errors=errors)

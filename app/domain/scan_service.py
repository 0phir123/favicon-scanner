# /app/domain/scan_service.py
from __future__ import annotations
import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Sequence, Protocol

from app.config import settings
from app.ports.fingerprint_repository import FingerprintRepositoryPort
from app.ports.http_fetcher import HTTPFetcherPort  
from app.ports.target_expander import TargetExpanderPort
from app.adapters.system.logging_cfg import configure_logger


LOG = logging.getLogger("scan_service")
configure_logger()

# ==== DTOs ====

@dataclass(slots=True)
class ScanRequestDTO:
    targets: list[str]
    ports: list[int]


@dataclass(slots=True)
class ScanResultDTO:
    target: str              # "host:port"
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

    async def scan(self, req: ScanRequestDTO) -> ScanResponseDTO:
        ports = req.ports or self.default_ports
        hosts = self.expander.expand(req.targets, self.max_targets)

        total_pairs = len(hosts) * len(ports)
        if total_pairs > settings.MAX_SOCKETS_PER_JOB:
            raise ValueError(f"job too large: {total_pairs} > {settings.MAX_SOCKETS_PER_JOB}")

        results: list[ScanResultDTO] = []
        errors: list[dict] = []

        def scheme_for(port: int) -> str:
            if port == 443:
                return "https"
            if port == 80:
                return "http"
            return "http"

        async def probe(host: str, port: int) -> None:
            scheme = scheme_for(port)
            target = f"{host}:{port}"
            try:
                async with asyncio.timeout(settings.TIMEOUT_SECONDS + 0.5):
                    status, body, final_url = await self.fetcher.fetch(scheme, host, port, "/favicon.ico")
            except Exception as e:
                errors.append({"target": target, "error": type(e).__name__, "detail": str(e)})
                return

            md5: str | None = None
            matches: list[dict] = []
            if 200 <= status < 300 and body:
                md5 = hashlib.md5(body).hexdigest()
              
                LOG.info(f"this is the md5 {md5}")
               
                matches = self.repo.lookup_md5(md5)

            results.append(
                ScanResultDTO(
                    target=target,
                    scheme=scheme,
                    byte_len=len(body) if body else 0,
                    md5=md5,
                    status=status,
                    final_url=final_url,
                    matches=matches,
                )
            )

        sem = asyncio.Semaphore(settings.CONCURRENCY)

        async def guarded_probe(h: str, p: int) -> None:
            async with sem:
                await probe(h, p)

        async with asyncio.TaskGroup() as tg:
            for h in hosts:
                for p in ports:
                    tg.create_task(guarded_probe(h, p))

        return ScanResponseDTO(results=results, errors=errors)

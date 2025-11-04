# /app/adapters/system/celery_app.py
from __future__ import annotations
import asyncio
import logging
from typing import Any

from celery import Celery

from app.config import settings
from app.adapters.system.logging_cfg import configure_logger
from app.adapters.http.aiohttp_fetcher import AiohttpFetcher
from app.adapters.repositories.rapid7_xml_repo import Rapid7XMLRepository
from app.adapters.system.redis_result_store import RedisResultStore
from app.adapters.system.target_expander_impl import TargetExpander
from app.domain.scan_service import ScanRequestDTO, ScanService

LOG = logging.getLogger("adapter.celery")
configure_logger()

celery_app = Celery("favicon_scanner", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=300,
)

# Lightweight objects are fine to create at import-time:
_store = RedisResultStore(settings.REDIS_URL)

# Heavy / event-loop dependent objects are created lazily:
_service: ScanService | None = None

def _get_service() -> ScanService:
    """
    Build ScanService the first time a task runs (when an event loop exists).
    """
    global _service
    if _service is None:
        repo = Rapid7XMLRepository(settings.FAVICONS_PATH)   # can raise if file missing (good)
        fetcher = AiohttpFetcher()                            # creates connector/session lazily
        expander = TargetExpander()
        _service = ScanService(
            repo=repo,
            fetcher=fetcher,
            expander=expander,
            default_ports=settings.DEFAULT_PORTS,
            max_targets=settings.MAX_TARGETS,
        )
    return _service

@celery_app.task(
    name="scan_job",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def scan_job(self, scan_id: str, payload: dict[str, Any]) -> str:
    """Execute the scan and persist the result or error."""
    try:
        LOG.info("scan.job.accepted", extra={"extra": {"scan_id": scan_id}})
        svc = _get_service()
        dto = ScanRequestDTO(
            targets=payload["targets"],
            ports=payload.get("ports") or settings.DEFAULT_PORTS,
        )

        async def _run() -> dict:
            resp = await svc.scan(dto)
            return {
                "results": [
                    {
                        "target": r.target,
                        "scheme": r.scheme,
                        "bytes": r.byte_len,
                        "md5": r.md5,
                        "status": r.status,
                        "final_url": r.final_url,
                        "matches": r.matches,
                    }
                    for r in resp.results
                ],
                "errors": resp.errors,
            }

        result_dict = asyncio.run(_run())
        _store.set_result(scan_id, result_dict)
        LOG.info("scan.job.done", extra={"extra": {"scan_id": scan_id}})
        return "ok"

    except Exception as e:
        _store.set_error(scan_id, str(e))
        LOG.exception("scan.job.error", extra={"extra": {"scan_id": scan_id}})
        raise

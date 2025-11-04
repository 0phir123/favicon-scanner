# mypy: ignore-errors
# /app/adapters/system/celery_app.py
from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery import Celery

from app.adapters.http.aiohttp_fetcher import AiohttpFetcher
from app.adapters.repositories.rapid7_recog_repo import Rapid7RecogRepository
from app.adapters.system.logging_cfg import configure_logger
from app.adapters.system.redis_result_store import RedisResultStore
from app.adapters.system.target_expander_impl import TargetExpander
from app.config import settings
from app.domain.scan_service import ScanRequestDTO, ScanService

LOG = logging.getLogger("adapter.celery")
configure_logger()

CELERY_BROKER_URL = settings.REDIS_URL
CELERY_BACKEND_URL = settings.REDIS_URL

celery_app = Celery("favicon_scanner", broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)
celery_app.conf.update(
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=300,
)

# Singleton-ish wiring per worker process

_repo = Rapid7RecogRepository(settings.FAVICONS_PATH)
_fetcher = AiohttpFetcher()
_expander = TargetExpander()
_store = RedisResultStore(settings.REDIS_URL)
_service = ScanService(
    repo=_repo,
    fetcher=_fetcher,
    expander=_expander,
    default_ports=settings.DEFAULT_PORTS,
    max_targets=settings.MAX_TARGETS,
)


@celery_app.task(
    name="scan_job",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def scan_job(self, scan_id: str, payload: dict[str, Any]) -> str:
    """Celery task: executes the scan and persists the result or error."""
    try:
        LOG.info("scan.job.accepted", extra={"extra": {"scan_id": scan_id}})
        dto = ScanRequestDTO(
            targets=payload["targets"], ports=payload.get("ports") or settings.DEFAULT_PORTS
        )

        async def _run() -> dict:
            resp = await _service.scan(dto)
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

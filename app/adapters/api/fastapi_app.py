# /app/adapters/api/fastapi_app.py
from __future__ import annotations
import logging
import uuid
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.adapters.system.logging_cfg import configure_logger
from app.adapters.system.redis_result_store import RedisResultStore
from app.adapters.system.celery_app import celery_app

LOG = logging.getLogger("adapter.api")
app = FastAPI(title="favicon-scanner")
configure_logger()

_store = RedisResultStore(settings.REDIS_URL)

class ScanRequestModel(BaseModel):
    targets: list[str]
    ports: Optional[list[int]] = None

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/scan")
async def scan_start(payload: ScanRequestModel, x_api_key: str | None = Header(default=None)) -> dict:
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    if not payload.targets:
        raise HTTPException(status_code=400, detail="targets required")

    ports = payload.ports or settings.DEFAULT_PORTS
    if any(p < 1 or p > 65535 for p in ports):
        raise HTTPException(status_code=400, detail="invalid port in request")

    if len(payload.targets) * len(ports) > settings.MAX_SOCKETS_PER_JOB:
        raise HTTPException(status_code=400, detail="request too large (sockets cap)")

    scan_id = str(uuid.uuid4())
    _store.set_pending(scan_id)

    job = celery_app.send_task("scan_job", args=[scan_id, payload.model_dump()], kwargs=None)
    LOG.info("scan.enqueued", extra={"extra": {"scan_id": scan_id, "job_id": job.id}})
    return {"scan_id": scan_id, "status": "pending", "job_id": job.id}

@app.get("/scan/{scan_id}")
async def scan_result(scan_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    entry = _store.get(scan_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="scan_id not found")
    return entry

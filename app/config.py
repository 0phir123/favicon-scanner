# /app/config.py
from __future__ import annotations

import os

from pydantic import BaseModel


class Settings(BaseModel):
    API_KEY: str | None = os.getenv("API_KEY")
    VERIFY_TLS: bool = os.getenv("VERIFY_TLS", "false").lower() == "true"

    # Concurrency / limits
    CONCURRENCY: int = int(os.getenv("CONCURRENCY", "200"))  # async slots per job
    PER_HOST_LIMIT: int = int(os.getenv("PER_HOST_LIMIT", "5"))  # sockets per host
    TIMEOUT_SECONDS: float = float(os.getenv("TIMEOUT_SECONDS", "3.0"))
    MAX_TARGETS: int = int(os.getenv("MAX_TARGETS", "2048"))
    MAX_SOCKETS_PER_JOB: int = int(os.getenv("MAX_SOCKETS_PER_JOB", "10000"))

    # Response safety
    MAX_BYTES: int = int(os.getenv("MAX_BYTES", "2097152"))  # 2 MB
    RETRIES: int = int(os.getenv("RETRIES", "1"))
    RETRY_BACKOFF_MS: int = int(os.getenv("RETRY_BACKOFF_MS", "250"))

    # Dataset / defaults
    FAVICONS_PATH: str = os.getenv("FAVICONS_PATH", "./data/favicons.xml")
    DEFAULT_PORTS: list[int] = [80, 443, 8080]

    # Celery / Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))


settings = Settings()

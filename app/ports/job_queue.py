# /app/ports/job_queue.py
from __future__ import annotations
from typing import Any, Mapping, Protocol

class JobQueuePort(Protocol):
    def enqueue(
        self,
        task_name: str,
        *,
        args: list[Any] | None = None,
        kwargs: Mapping[str, Any] | None = None,
    ) -> str:
        """Enqueue a background job and return a provider job id."""
        
# /app/adapters/system/logging_cfg.py
from __future__ import annotations

import json
import logging
import sys
from typing import Any


def configure_logger(level: int = logging.INFO) -> None:
    class JSONHandler(logging.StreamHandler):
        def emit(self, record: logging.LogRecord) -> None:
            payload: dict[str, Any] = {
                "level": record.levelname,
                "msg": record.getMessage(),
                "logger": record.name,
            }
            extra = getattr(record, "extra", None)
            if isinstance(extra, dict):
                payload.update(extra)
            self.stream.write(json.dumps(payload, default=str) + "\n")
            self.flush()

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(JSONHandler(stream=sys.stdout))

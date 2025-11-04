# /app/ports/fingerprint_repository.py
from __future__ import annotations

from typing import Protocol


class FingerprintRepositoryPort(Protocol):
    def lookup_md5(self, md5: str) -> list[dict]:
        """Return 0..N fingerprint dicts for MD5 (name/properties)."""

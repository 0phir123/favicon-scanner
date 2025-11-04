# /app/adapters/repositories/rapid7_recog_repo.py
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import xmltodict

LOG = logging.getLogger("adapter.repo.recog")

_HEX32 = re.compile(r"[0-9a-fA-F]{32}")

class Rapid7RecogRepository:
    """
    Parses Rapid7 recog http_favicon.xml.
    Builds a map: md5 (lowercase hex) -> list[ {name, properties} ].
    """
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._by_md5: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"recog XML not found: {self._path}")

        doc = xmltodict.parse(self._path.read_text(encoding="utf-8"))

        fps = (doc.get("fingerprints") or {}).get("fingerprint", [])
        if isinstance(fps, dict):
            fps = [fps]

        added = 0
        for fp in fps:
            pattern = fp.get("@pattern") or ""
            # Extract all 32-hex tokens from the regex like ^(?:aa|bb|cc)$
            md5s = _HEX32.findall(pattern)
            if not md5s:
                continue

            name = fp.get("description") or "unknown"
            params = fp.get("param") or []
            if isinstance(params, dict):
                params = [params]

            props: Dict[str, str] = {}
            for p in params:
                k = p.get("@name")
                v = p.get("@value")
                if k and v is not None:
                    props[k] = v

            entry = {"name": name, "properties": props}

            for m in md5s:
                self._by_md5.setdefault(m.lower(), []).append(entry)
                added += 1

        LOG.info("recog favicon fingerprints loaded", extra={"extra": {"md5_variants": added}})

    def lookup_md5(self, md5: str) -> list[dict]:
        return self._by_md5.get(md5.lower(), [])

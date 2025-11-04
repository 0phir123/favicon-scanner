# /app/adapters/repositories/rapid7_xml_repo.py
from __future__ import annotations
import logging
from pathlib import Path
import xmltodict

LOG = logging.getLogger("adapter.repo.rapid7xml")

class Rapid7XMLRepository:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._by_md5: dict[str, list[dict]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"favicons xml not found: {self._path}")
        doc = xmltodict.parse(self._path.read_text(encoding="utf-8"))
        items = doc.get("favicons", {}).get("favicon", [])
        count = 0
        for item in items:
            md5 = (item.get("md5") or "").lower()
            if not md5:
                continue
            entry = {"name": item.get("name", "unknown"), "properties": {}}
            props = (item.get("properties") or {}).get("property", [])
            if isinstance(props, dict):
                props = [props]
            for p in props:
                k = p.get("@name")
                v = p.get("#text")
                if k:
                    entry["properties"][k] = v
            self._by_md5.setdefault(md5, []).append(entry)
            count += 1
        LOG.info("rapid7 xml loaded", extra={"extra": {"records": count}})

    def lookup_md5(self, md5: str) -> list[dict]:
        return self._by_md5.get(md5.lower(), [])

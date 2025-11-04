# tests/fakes.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeFingerprintRepo:
    rules: list  # [(pattern_or_callable, description, params_dict)]

    def match(self, md5_hex: str) -> list[dict]:
        out = []
        for pattern, description, params in self.rules:
            ok = False
            if hasattr(pattern, "match"):
                ok = bool(pattern.match(md5_hex))
            elif callable(pattern):
                ok = bool(pattern(md5_hex))
            if ok:
                out.append({"description": description, **(params or {})})
        return out


class FakeFetcher:
    """
    Be liberal in what we accept:
    - fetch(host, port)
    - fetch(host, port, *extras)
    - fetch((host, port), *extras)
    """

    def __init__(self, responses: dict[tuple[str, int], tuple[int, bytes]]):
        self._responses = responses

    async def fetch(self, *args, **kwargs):
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], int):
            host, port = args[0], args[1]
        elif len(args) >= 1 and isinstance(args[0], tuple) and len(args[0]) == 2:
            host, port = args[0]
        else:
            raise TypeError(f"FakeFetcher.fetch() could not parse args={args}")

        status, body = self._responses[(host, port)]
        scheme = "https" if port == 443 else "http"
        return scheme, status, body  # keep same contract as your service expects


class FakeTargetExpander:
    def __init__(self, default_ports):
        self.default_ports = list(default_ports)

    def expand(self, targets, ports):
        ports = ports or self.default_ports
        return [(t, p) for t in targets for p in ports]


class LenientExpander(FakeTargetExpander):
    """Accept int for ports (current ScanService bug), fallback to defaults."""

    def expand(self, targets, ports):
        if isinstance(ports, int):
            ports = self.default_ports
        return super().expand(targets, ports)


class InMemoryResultStore:
    def __init__(self):
        self._data = {}

    def set_pending(self, scan_id):
        self._data[scan_id] = {"status": "pending"}

    def set_error(self, scan_id, error):
        self._data[scan_id] = {"status": "error", "error": error}

    def set_result(self, scan_id, result):
        self._data[scan_id] = {"status": "done", "result": result}

    def get(self, scan_id):
        return self._data.get(scan_id)

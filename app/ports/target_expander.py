# /app/ports/target_expander.py
from __future__ import annotations

from typing import Protocol


class TargetExpanderPort(Protocol):
    def expand(self, inputs: list[str], max_targets: int) -> list[str]:
        """Expand CIDR/IP/hostnames into a list of hosts."""

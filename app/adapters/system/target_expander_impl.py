# /app/adapters/system/target_expander_impl.py
from __future__ import annotations

import logging
from ipaddress import ip_address, ip_network

LOG = logging.getLogger("adapter.target_expander")


class TargetExpander:
    def expand(self, inputs: list[str], max_targets: int) -> list[str]:
        hosts: list[str] = []
        for item in inputs:
            s = item.strip()
            try:
                if "/" in s:
                    net = ip_network(s, strict=False)
                    for addr in net.hosts():
                        hosts.append(str(addr))
                else:
                    ip_address(s)  # validates or raises
                    hosts.append(s)
            except Exception:
                hosts.append(s)  # treat as hostname

        if len(hosts) > max_targets:
            LOG.warning("expanded targets exceed max", extra={"extra": {"max": max_targets}})
            raise ValueError("expanded targets exceed MAX_TARGETS")

        LOG.info("expanded targets", extra={"extra": {"in": len(inputs), "out": len(hosts)}})
        return hosts

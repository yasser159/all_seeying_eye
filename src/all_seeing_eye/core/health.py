from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PortHealth:
    host: str
    port: int
    listening: bool
    error: Optional[str] = None


def check_tcp_listener(host: str, port: int, timeout_s: float = 0.25) -> PortHealth:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            result = s.connect_ex((host, port))
            return PortHealth(host=host, port=port, listening=(result == 0), error=None)
    except Exception as exc:
        return PortHealth(host=host, port=port, listening=False, error=str(exc))


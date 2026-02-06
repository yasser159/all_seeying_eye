from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LogEntry:
    id: str
    timestamp: datetime
    level: str
    message: str
    data: Optional[Dict[str, Any]] = None
    source: str = "metro"

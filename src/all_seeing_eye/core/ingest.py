from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .log_types import LogEntry


DIAGNOSTICS_PREFIX = "[Diagnostics] "


def parse_diagnostics_line(line: str) -> Optional[Dict[str, Any]]:
    idx = line.find(DIAGNOSTICS_PREFIX)
    if idx == -1:
        return None
    payload = line[idx + len(DIAGNOSTICS_PREFIX) :].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def to_log_entry(payload: Dict[str, Any], source: str) -> LogEntry:
    timestamp = payload.get("ts") or payload.get("timestamp")
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.utcnow()
    else:
        dt = datetime.utcnow()

    return LogEntry(
        id=str(uuid.uuid4()),
        timestamp=dt,
        level=str(payload.get("level", "info")),
        message=str(payload.get("message", "")),
        data=payload.get("data") if isinstance(payload.get("data"), dict) else None,
        source=source,
    )

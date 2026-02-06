from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Dict


def emit(level: str, message: str, data: Dict[str, Any] | None = None) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "data": data or {},
    }
    sys.stdout.write(f"[AllSeeingEye] {json.dumps(payload, default=str)}\n")
    sys.stdout.flush()

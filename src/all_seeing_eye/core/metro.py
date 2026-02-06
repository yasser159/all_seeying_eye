from __future__ import annotations

import subprocess
from typing import Iterable, Optional

from .ingest import parse_diagnostics_line, to_log_entry
from .logger import emit
from .log_store import LogStore


class MetroTail:
    def __init__(self, store: LogStore) -> None:
        self._store = store
        self._proc: Optional[subprocess.Popen[str]] = None

    def start(self, project_dir: str) -> None:
        emit("info", "MetroStart", {"project": project_dir})
        self._proc = subprocess.Popen(
            ["npm", "run", "start"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if not self._proc.stdout:
            raise RuntimeError("Failed to attach to Metro stdout")
        self._tail(self._proc.stdout, source="metro")

    def tail_iter(self, lines: Iterable[str], source: str = "stdin") -> None:
        self._tail(lines, source=source)

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            emit("info", "MetroStop", {})
            self._proc.terminate()

    def _tail(self, lines: Iterable[str], source: str) -> None:
        for line in lines:
            payload = parse_diagnostics_line(line)
            if not payload:
                continue
            entry = to_log_entry(payload, source=source)
            self._store.add(entry)
            emit("debug", "LogIngested", {"level": entry.level, "message": entry.message})

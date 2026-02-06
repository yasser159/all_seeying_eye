from __future__ import annotations

import subprocess
import threading
from typing import Optional, Callable

from .ingest import parse_diagnostics_line, to_log_entry
from .logger import emit
from .log_store import LogStore


class MetroRunner:
    """
    Spawn `npm run start` in an Expo project and ingest `[Diagnostics]` JSON lines.
    Runs in a background thread so the UI thread isn't blocked.
    """

    def __init__(
        self,
        store: LogStore,
        on_state: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self._store = store
        self._proc: Optional[subprocess.Popen[str]] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._on_state = on_state

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, project_dir: str) -> None:
        if self._thread and self._thread.is_alive():
            return

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
            emit("error", "MetroStartFailed", {"error": "Failed to attach to Metro stdout"})
            self._set_running(False)
            return

        self._set_running(True)
        self._thread = threading.Thread(target=self._tail, args=(self._proc.stdout,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            emit("info", "MetroStop", {})
            self._proc.terminate()
        self._set_running(False)

    def _tail(self, stdout) -> None:
        try:
            for line in stdout:
                payload = parse_diagnostics_line(line)
                if not payload:
                    continue
                entry = to_log_entry(payload, source="metro")
                self._store.add(entry)
                emit("debug", "LogIngested", {"level": entry.level, "message": entry.message})
        except Exception as exc:
            emit("error", "MetroTailFailed", {"error": str(exc)})
        finally:
            self._set_running(False)

    def _set_running(self, value: bool) -> None:
        self._running = value
        if self._on_state:
            self._on_state(self._running)


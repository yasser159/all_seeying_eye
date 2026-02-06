from __future__ import annotations

from typing import Callable

from .log_types import LogEntry
from .logger import emit


class Notifier:
    def __init__(self, on_action: Callable[[str], None]) -> None:
        self._on_action = on_action

    def notify(self, entry: LogEntry) -> None:
        emit("info", "Notify", {"level": entry.level, "message": entry.message})

    def handle_action(self, action: str) -> None:
        self._on_action(action)

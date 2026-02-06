from __future__ import annotations

import threading
from typing import Callable, List

from .log_types import LogEntry

LogSubscriber = Callable[[LogEntry, List[LogEntry]], None]


class LogStore:
    def __init__(self, max_history: int = 1000) -> None:
        self._max_history = max_history
        self._history: List[LogEntry] = []
        self._subscribers: List[LogSubscriber] = []
        self._lock = threading.Lock()

    def add(self, entry: LogEntry) -> None:
        with self._lock:
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            snapshot = list(self._history)
            subscribers = list(self._subscribers)

        for subscriber in subscribers:
            subscriber(entry, snapshot)

    def get_all(self) -> List[LogEntry]:
        with self._lock:
            return list(self._history)

    def subscribe(self, subscriber: LogSubscriber) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

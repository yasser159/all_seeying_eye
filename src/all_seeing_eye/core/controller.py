from __future__ import annotations

from typing import Callable, Optional

from .log_store import LogStore
from .ws_server import WebSocketIngestServer


class IngestController:
    def __init__(self, store: LogStore, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._store = store
        self._host = host
        self._port = port
        self._ws_server: Optional[WebSocketIngestServer] = None
        self._on_status: Optional[Callable[[bool], None]] = None

    def set_status_callback(self, callback: Callable[[bool], None]) -> None:
        self._on_status = callback

    def start_ws(self) -> None:
        if self._ws_server and self._ws_server.is_running:
            return
        self._ws_server = WebSocketIngestServer(
            self._store, host=self._host, port=self._port, on_state=self._handle_state
        )
        self._ws_server.start()

    def stop_ws(self) -> None:
        if not self._ws_server:
            return
        self._ws_server.stop()

    def is_running(self) -> bool:
        return bool(self._ws_server and self._ws_server.is_running)

    def _handle_state(self, running: bool) -> None:
        if self._on_status:
            self._on_status(running)

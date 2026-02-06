from __future__ import annotations

from typing import Callable, Optional

from .log_store import LogStore
from .metro_runner import MetroRunner
from .ws_server import WebSocketIngestServer


class IngestController:
    def __init__(self, store: LogStore, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._store = store
        self._ws_host = host
        self._ws_port = port
        self._ws_server: Optional[WebSocketIngestServer] = None
        self._metro: Optional[MetroRunner] = None

        self._on_ws_status: Optional[Callable[[bool], None]] = None
        self._on_metro_status: Optional[Callable[[bool], None]] = None

    def set_ws_status_callback(self, callback: Callable[[bool], None]) -> None:
        self._on_ws_status = callback

    def set_metro_status_callback(self, callback: Callable[[bool], None]) -> None:
        self._on_metro_status = callback

    def configure_ws(self, host: str, port: int) -> None:
        self._ws_host = host
        self._ws_port = port

    def start_ws(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        if host is not None and port is not None:
            self.configure_ws(host, port)

        if self._ws_server and self._ws_server.is_running:
            return
        self._ws_server = WebSocketIngestServer(
            self._store,
            host=self._ws_host,
            port=self._ws_port,
            on_state=self._handle_ws_state,
        )
        self._ws_server.start()

    def stop_ws(self) -> None:
        if not self._ws_server:
            return
        self._ws_server.stop()

    def ws_running(self) -> bool:
        return bool(self._ws_server and self._ws_server.is_running)

    def start_metro(self, project_dir: str, command: Optional[list[str]] = None) -> None:
        if self._metro and self._metro.is_running:
            return
        self._metro = MetroRunner(self._store, on_state=self._handle_metro_state)
        if command:
            self._metro.start_with_command(project_dir, command)
        else:
            self._metro.start(project_dir)

    def stop_metro(self) -> None:
        if not self._metro:
            return
        self._metro.stop()

    def metro_running(self) -> bool:
        return bool(self._metro and self._metro.is_running)

    def _handle_ws_state(self, running: bool) -> None:
        if self._on_ws_status:
            self._on_ws_status(running)

    def _handle_metro_state(self, running: bool) -> None:
        if self._on_metro_status:
            self._on_metro_status(running)

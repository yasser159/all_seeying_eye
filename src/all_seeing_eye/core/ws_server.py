from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional, Callable

from websockets.server import serve

from .ingest import parse_diagnostics_line, to_log_entry
from .logger import emit
from .log_store import LogStore


class WebSocketIngestServer:
    def __init__(
        self,
        store: LogStore,
        host: str = "127.0.0.1",
        port: int = 8765,
        on_state: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self._store = store
        self._host = host
        self._port = port
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._on_state = on_state

    def start(self) -> None:
        if self._thread:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self._shutdown()))
        self._set_running(False)

    @property
    def is_running(self) -> bool:
        return self._running

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:
            emit("error", "WebSocketStartFailed", {"error": str(exc)})
            self._set_running(False)
            return
        self._loop.run_forever()

    async def _serve(self) -> None:
        emit("info", "WebSocketStart", {"host": self._host, "port": self._port})
        self._server = await serve(self._handler, self._host, self._port)
        self._set_running(True)

    async def _shutdown(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._loop:
            self._loop.stop()
        self._set_running(False)

    async def _handler(self, websocket) -> None:
        async for message in websocket:
            self._handle_message(message)

    def _handle_message(self, message: str) -> None:
        payload = None
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            payload = parse_diagnostics_line(message)
        if not payload:
            return
        entry = to_log_entry(payload, source="websocket")
        self._store.add(entry)
        emit("debug", "LogIngested", {"level": entry.level, "message": entry.message})

    def _set_running(self, value: bool) -> None:
        self._running = value
        if self._on_state:
            self._on_state(self._running)

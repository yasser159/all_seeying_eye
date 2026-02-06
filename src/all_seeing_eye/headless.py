from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from .core.ingest import parse_diagnostics_line, to_log_entry
from .core.log_store import LogStore
from .core.logger import emit
from .core.metro import MetroTail
from .core.ws_server import WebSocketIngestServer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="All Seeing Eye headless ingest")
    parser.add_argument("--project", help="Path to Expo project (runs Metro)")
    parser.add_argument("--stdin", action="store_true", help="Read logs from stdin")
    parser.add_argument("--ws", action="store_true", help="Start WebSocket ingest server")
    parser.add_argument("--ws-host", default="127.0.0.1", help="WebSocket host")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    store = LogStore(max_history=2000)

    def on_entry(entry, _history):
        emit("info", "HeadlessLog", {"level": entry.level, "message": entry.message})

    store.subscribe(on_entry)

    if args.project:
        tail = MetroTail(store)
        tail.start(args.project)
    elif args.stdin:
        emit("info", "StdinMode", {})
        for line in sys.stdin:
            payload = parse_diagnostics_line(line)
            if not payload:
                continue
            entry = to_log_entry(payload, source="stdin")
            store.add(entry)
    elif args.ws:
        server = WebSocketIngestServer(store, host=args.ws_host, port=args.ws_port)
        server.start()
        emit("info", "WebSocketReady", {"host": args.ws_host, "port": args.ws_port})
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            server.stop()
    else:
        emit("warn", "NoSourceConfigured", {})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

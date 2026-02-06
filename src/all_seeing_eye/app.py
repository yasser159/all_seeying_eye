from __future__ import annotations

import argparse
import sys
from typing import Optional

from PySide6 import QtCore, QtWidgets

from .core.controller import IngestController
from .core.ingest import parse_diagnostics_line, to_log_entry
from .core.log_store import LogStore
from .core.logger import emit
from .core.notifier import Notifier
from .core.notifier_macos import MacOSNotifier
from .ui.main_window import MainWindow


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="All Seeing Eye diagnostics viewer")
    parser.add_argument("--project", help="Path to Expo project (runs Metro)")
    parser.add_argument("--stdin", action="store_true", help="Read logs from stdin")
    parser.add_argument("--ws", action="store_true", help="Start WebSocket ingest server")
    parser.add_argument("--ws-host", default="127.0.0.1", help="WebSocket host")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    store = LogStore(max_history=2000)

    app = QtWidgets.QApplication(sys.argv)
    controller = IngestController(store, host=args.ws_host, port=args.ws_port)
    window = MainWindow(store, controller)

    def handle_action(action: str) -> None:
        if action == "open_diagnostics":
            window.focus_diagnostics()

    notifier: Notifier
    notifier = MacOSNotifier(handle_action)

    def on_entry(entry, _history):
        if entry.level in {"error", "warn"}:
            notifier.notify(entry)

    store.subscribe(on_entry)

    if args.project:
        controller.start_metro(args.project)
    elif args.stdin:
        emit("info", "StdinMode", {})
        for line in sys.stdin:
            payload = parse_diagnostics_line(line)
            if not payload:
                continue
            entry = to_log_entry(payload, source="stdin")
            store.add(entry)
    elif args.ws:
        controller.start_ws()
    else:
        emit("warn", "NoSourceConfigured", {})

    window.show()
    # macOS can launch the app without focusing the first window (especially from Finder).
    QtCore.QTimer.singleShot(0, window.focus_diagnostics)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

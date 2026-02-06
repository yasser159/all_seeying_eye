from __future__ import annotations

import json
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.controller import IngestController
from ..core.log_store import LogStore
from .models import LogListModel


class _LogBridge(QtCore.QObject):
    entry_received = QtCore.Signal(object)


class _StatusBridge(QtCore.QObject):
    ws_changed = QtCore.Signal(bool)
    metro_changed = QtCore.Signal(bool)


class _LogFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._query = ""
        self._levels = {"debug", "info", "warn", "error"}

    def set_query(self, query: str) -> None:
        self._query = (query or "").strip().lower()
        self.invalidateFilter()

    def set_levels(self, levels: set[str]) -> None:
        self._levels = set(levels)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:  # type: ignore[override]
        model = self.sourceModel()
        if model is None:
            return True
        idx = model.index(source_row, 0, source_parent)
        level = model.data(idx, LogListModel.LevelRole)
        message = model.data(idx, LogListModel.MessageRole) or ""
        source = model.data(idx, LogListModel.SourceRole) or ""

        if level not in self._levels:
            return False

        if not self._query:
            return True

        hay = f"{level} {source} {message}".lower()
        return self._query in hay


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, store: LogStore, controller: IngestController) -> None:
        super().__init__()
        self.setWindowTitle("All Seeing Eye")
        self.resize(1100, 720)

        self._store = store
        self._controller = controller

        self._paused = False
        self._auto_scroll = True
        self._last_ingest: datetime | None = None

        self._model = LogListModel(store.get_all())
        self._proxy = _LogFilterProxy()
        self._proxy.setSourceModel(self._model)

        self._bridge = _LogBridge()
        self._bridge.entry_received.connect(self._append_log)

        self._status_bridge = _StatusBridge()
        self._status_bridge.ws_changed.connect(self._set_ws_running)
        self._status_bridge.metro_changed.connect(self._set_metro_running)

        self._build_ui()
        self._wire_controller()

        self._store.subscribe(self._on_log_entry)

        # Initial state
        self._set_ws_running(self._controller.ws_running())
        self._set_metro_running(self._controller.metro_running())
        self._refresh_statusbar()

        self._build_menu()

    def focus_diagnostics(self) -> None:
        self.raise_()
        self.activateWindow()
        self.show()

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")

        action_howto = QtGui.QAction("How To Use", self)
        action_howto.triggered.connect(self._show_howto)
        help_menu.addAction(action_howto)

        action_about = QtGui.QAction("About", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)

    def _build_ui(self) -> None:
        toolbar = QtWidgets.QHBoxLayout()

        self._clear_button = QtWidgets.QPushButton("Clear")
        self._pause_button = QtWidgets.QPushButton("Pause")
        self._pause_button.setCheckable(True)
        self._autoscroll_cb = QtWidgets.QCheckBox("Auto-scroll")
        self._autoscroll_cb.setChecked(True)
        self._copy_button = QtWidgets.QPushButton("Copy Selected JSON")

        toolbar.addWidget(self._clear_button)
        toolbar.addWidget(self._pause_button)
        toolbar.addWidget(self._autoscroll_cb)
        toolbar.addWidget(self._copy_button)
        toolbar.addStretch(1)

        self._sources = QtWidgets.QTabWidget()
        self._sources.addTab(self._build_ws_tab(), "WebSocket")
        self._sources.addTab(self._build_metro_tab(), "Metro")

        filter_row = QtWidgets.QHBoxLayout()
        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Filter logs (message/source/level)...")

        self._lvl_debug = QtWidgets.QCheckBox("debug")
        self._lvl_info = QtWidgets.QCheckBox("info")
        self._lvl_warn = QtWidgets.QCheckBox("warn")
        self._lvl_error = QtWidgets.QCheckBox("error")
        for cb in (self._lvl_debug, self._lvl_info, self._lvl_warn, self._lvl_error):
            cb.setChecked(True)

        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._lvl_debug)
        filter_row.addWidget(self._lvl_info)
        filter_row.addWidget(self._lvl_warn)
        filter_row.addWidget(self._lvl_error)

        self._list = QtWidgets.QListView()
        self._list.setModel(self._proxy)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._details = QtWidgets.QTextEdit()
        self._details.setReadOnly(True)
        self._details.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._list)
        splitter.addWidget(self._details)
        splitter.setSizes([640, 460])

        root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(root)
        layout.addLayout(toolbar)
        layout.addWidget(self._sources)
        layout.addLayout(filter_row)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)

        self.setStatusBar(QtWidgets.QStatusBar())

        # Wire UI events
        self._clear_button.clicked.connect(self._clear_logs)
        self._pause_button.toggled.connect(self._set_paused)
        self._autoscroll_cb.toggled.connect(self._set_autoscroll)
        self._copy_button.clicked.connect(self._copy_selected)

        self._search.textChanged.connect(self._on_filter_changed)
        self._lvl_debug.toggled.connect(self._on_filter_changed)
        self._lvl_info.toggled.connect(self._on_filter_changed)
        self._lvl_warn.toggled.connect(self._on_filter_changed)
        self._lvl_error.toggled.connect(self._on_filter_changed)

        self._list.selectionModel().selectionChanged.connect(self._on_selection)

        self._status_timer = QtCore.QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._refresh_statusbar)
        self._status_timer.start()

    def _show_howto(self) -> None:
        text = (
            "Quick Start\n"
            "1) WebSocket mode (recommended)\n"
            "   - Open the WebSocket tab.\n"
            "   - Click Start Listening.\n"
            "   - Copy the ws:// URL and have your app send JSON logs to it.\n"
            "\n"
            "2) Metro mode\n"
            "   - Open the Metro tab.\n"
            "   - Set your Expo project directory.\n"
            "   - Click Start Metro (spawns `npm run start`).\n"
            "   - The app will ingest `[Diagnostics] { ... }` JSON lines.\n"
            "\n"
            "Controls\n"
            "- Pause: freezes the view (ingest continues in the background).\n"
            "- Auto-scroll: keep the newest log visible.\n"
            "- Filter: search + level toggles.\n"
            "- Copy Selected JSON: copies the selected entry as JSON.\n"
        )
        QtWidgets.QMessageBox.information(self, "How To Use", text)

    def _show_about(self) -> None:
        text = (
            "All Seeing Eye\n"
            "Desktop diagnostics viewer for structured app logs.\n"
            "Sources: WebSocket, Metro.\n"
        )
        QtWidgets.QMessageBox.information(self, "About", text)

    def _build_ws_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(w)

        self._ws_host = QtWidgets.QLineEdit("127.0.0.1")
        self._ws_port = QtWidgets.QSpinBox()
        self._ws_port.setRange(1, 65535)
        self._ws_port.setValue(8765)

        self._ws_button = QtWidgets.QPushButton("Start Listening")
        self._ws_dot = QtWidgets.QLabel("●")
        self._ws_dot.setStyleSheet("color: #9aa0a6;")
        self._ws_label = QtWidgets.QLabel("Stopped")
        self._ws_url = QtWidgets.QLineEdit("ws://127.0.0.1:8765")
        self._ws_url.setReadOnly(True)
        self._ws_copy_url = QtWidgets.QPushButton("Copy URL")

        layout.addWidget(QtWidgets.QLabel("Host"), 0, 0)
        layout.addWidget(self._ws_host, 0, 1)
        layout.addWidget(QtWidgets.QLabel("Port"), 0, 2)
        layout.addWidget(self._ws_port, 0, 3)
        layout.addWidget(self._ws_button, 0, 4)
        layout.addWidget(self._ws_dot, 0, 5)
        layout.addWidget(self._ws_label, 0, 6)
        layout.addWidget(QtWidgets.QLabel("Listen URL"), 1, 0)
        layout.addWidget(self._ws_url, 1, 1, 1, 4)
        layout.addWidget(self._ws_copy_url, 1, 5, 1, 2)

        self._ws_button.clicked.connect(self._toggle_ws)
        self._ws_copy_url.clicked.connect(self._copy_ws_url)
        self._ws_host.textChanged.connect(self._update_ws_url)
        self._ws_port.valueChanged.connect(self._update_ws_url)

        return w

    def _build_metro_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(w)

        self._metro_project = QtWidgets.QLineEdit("/Users/yasser159/code/React/diabetic_watch_react")
        self._metro_browse = QtWidgets.QPushButton("Browse")
        self._metro_button = QtWidgets.QPushButton("Start Metro")
        self._metro_dot = QtWidgets.QLabel("●")
        self._metro_dot.setStyleSheet("color: #9aa0a6;")
        self._metro_label = QtWidgets.QLabel("Stopped")

        layout.addWidget(QtWidgets.QLabel("Project"), 0, 0)
        layout.addWidget(self._metro_project, 0, 1, 1, 4)
        layout.addWidget(self._metro_browse, 0, 5)
        layout.addWidget(self._metro_button, 0, 6)
        layout.addWidget(self._metro_dot, 0, 7)
        layout.addWidget(self._metro_label, 0, 8)

        self._metro_browse.clicked.connect(self._browse_project)
        self._metro_button.clicked.connect(self._toggle_metro)

        return w

    def _wire_controller(self) -> None:
        self._controller.set_ws_status_callback(self._status_bridge.ws_changed.emit)
        self._controller.set_metro_status_callback(self._status_bridge.metro_changed.emit)

    def _on_log_entry(self, entry, _history) -> None:
        self._bridge.entry_received.emit(entry)

    @QtCore.Slot(object)
    def _append_log(self, entry) -> None:
        self._last_ingest = datetime.utcnow()
        self._model.append_entry(entry)
        if self._paused:
            return
        if self._auto_scroll:
            self._list.scrollToBottom()

    def _clear_logs(self) -> None:
        # Minimal-impact: reset model based on current store history without mutating store internals.
        self._details.clear()
        self._model.set_entries([])

    def _set_paused(self, paused: bool) -> None:
        self._paused = paused
        if not paused:
            # Re-sync UI from store
            self._model.set_entries(self._store.get_all())

    def _set_autoscroll(self, enabled: bool) -> None:
        self._auto_scroll = enabled

    def _on_filter_changed(self, *_args) -> None:
        levels = set()
        if self._lvl_debug.isChecked():
            levels.add("debug")
        if self._lvl_info.isChecked():
            levels.add("info")
        if self._lvl_warn.isChecked():
            levels.add("warn")
        if self._lvl_error.isChecked():
            levels.add("error")
        self._proxy.set_levels(levels)
        self._proxy.set_query(self._search.text())

    def _on_selection(self, selected, _deselected) -> None:
        if not selected.indexes():
            self._details.clear()
            return
        proxy_index = selected.indexes()[0]
        source_index = self._proxy.mapToSource(proxy_index)
        entry_obj = self._model.data(source_index, LogListModel.EntryRole)
        if not entry_obj:
            self._details.clear()
            return
        self._details.setPlainText(json.dumps(entry_obj, indent=2, default=str))

    def _copy_selected(self) -> None:
        text = self._details.toPlainText().strip()
        if not text:
            return
        QtWidgets.QApplication.clipboard().setText(text)

    def _update_ws_url(self, *_args) -> None:
        host = self._ws_host.text().strip() or "127.0.0.1"
        port = int(self._ws_port.value())
        self._ws_url.setText(f"ws://{host}:{port}")

    def _copy_ws_url(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self._ws_url.text().strip())

    def _toggle_ws(self) -> None:
        host = self._ws_host.text().strip() or "127.0.0.1"
        port = int(self._ws_port.value())
        if self._controller.ws_running():
            self._controller.stop_ws()
        else:
            self._controller.start_ws(host=host, port=port)

    def _toggle_metro(self) -> None:
        project = self._metro_project.text().strip()
        if not project:
            return
        if self._controller.metro_running():
            self._controller.stop_metro()
        else:
            self._controller.start_metro(project)

    def _browse_project(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Expo Project Directory")
        if path:
            self._metro_project.setText(path)

    @QtCore.Slot(bool)
    def _set_ws_running(self, running: bool) -> None:
        if running:
            self._ws_label.setText("Listening")
            self._ws_dot.setStyleSheet("color: #10b981;")
            self._ws_button.setText("Stop Listening")
        else:
            self._ws_label.setText("Stopped")
            self._ws_dot.setStyleSheet("color: #9aa0a6;")
            self._ws_button.setText("Start Listening")

    @QtCore.Slot(bool)
    def _set_metro_running(self, running: bool) -> None:
        if running:
            self._metro_label.setText("Running")
            self._metro_dot.setStyleSheet("color: #10b981;")
            self._metro_button.setText("Stop Metro")
        else:
            self._metro_label.setText("Stopped")
            self._metro_dot.setStyleSheet("color: #9aa0a6;")
            self._metro_button.setText("Start Metro")

    def _refresh_statusbar(self) -> None:
        total = self._model.rowCount()
        ws = "on" if self._controller.ws_running() else "off"
        metro = "on" if self._controller.metro_running() else "off"
        paused = "paused" if self._paused else "live"
        last = self._last_ingest.isoformat(timespec="seconds") + "Z" if self._last_ingest else "-"
        self.statusBar().showMessage(
            f"ingest: ws={ws} metro={metro} | view: {paused} | logs: {total} | last: {last}"
        )

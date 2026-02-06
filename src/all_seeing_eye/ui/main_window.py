from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.controller import IngestController
from ..core.log_store import LogStore
from .models import LogListModel


class _LogBridge(QtCore.QObject):
    entry_received = QtCore.Signal(object)


class _StatusBridge(QtCore.QObject):
    status_changed = QtCore.Signal(bool)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, store: LogStore, controller: IngestController) -> None:
        super().__init__()
        self.setWindowTitle("All Seeing Eye — Diagnostics")
        self.resize(960, 640)

        self._store = store
        self._controller = controller
        self._model = LogListModel(store.get_all())

        self._start_button = QtWidgets.QPushButton("Start Intercept")
        self._status_label = QtWidgets.QLabel("Stopped")
        self._status_dot = QtWidgets.QLabel("●")
        self._status_dot.setStyleSheet("color: #9aa0a6;")

        header = QtWidgets.QHBoxLayout()
        header.addWidget(self._start_button)
        header.addStretch(1)
        header.addWidget(self._status_dot)
        header.addWidget(self._status_label)

        self._list = QtWidgets.QListView()
        self._list.setModel(self._model)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._details = QtWidgets.QTextEdit()
        self._details.setReadOnly(True)
        self._details.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._list)
        splitter.addWidget(self._details)
        splitter.setSizes([520, 440])

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addLayout(header)
        layout.addWidget(splitter)

        self.setCentralWidget(container)

        self._bridge = _LogBridge()
        self._bridge.entry_received.connect(self._append_log)
        self._status_bridge = _StatusBridge()
        self._status_bridge.status_changed.connect(self._set_running)

        self._list.selectionModel().selectionChanged.connect(self._on_selection)
        self._store.subscribe(self._on_log_entry)
        self._start_button.clicked.connect(self._toggle_intercept)
        self._controller.set_status_callback(self._status_bridge.status_changed.emit)
        self._set_running(self._controller.is_running())

    def focus_diagnostics(self) -> None:
        self.raise_()
        self.activateWindow()
        self.show()

    def _on_log_entry(self, entry, history):
        self._bridge.entry_received.emit(entry)

    @QtCore.Slot(object)
    def _append_log(self, entry):
        self._model.append_entry(entry)
        self._list.scrollToBottom()

    def _on_selection(self, selected, _deselected):
        if not selected.indexes():
            self._details.clear()
            return
        index = selected.indexes()[0]
        data = self._model.data(index, self._model.DataRole)
        if not data:
            self._details.clear()
            return
        pretty = QtCore.QJsonDocument.fromVariant(data).toJson(QtCore.QJsonDocument.Indented)
        self._details.setPlainText(bytes(pretty).decode("utf-8"))

    @QtCore.Slot()
    def _toggle_intercept(self) -> None:
        if self._controller.is_running():
            self._controller.stop_ws()
        else:
            self._controller.start_ws()

    @QtCore.Slot(bool)
    def _set_running(self, running: bool) -> None:
        if running:
            self._status_label.setText("Intercepting")
            self._status_dot.setStyleSheet("color: #10b981;")
            self._start_button.setText("Stop Intercept")
        else:
            self._status_label.setText("Stopped")
            self._status_dot.setStyleSheet("color: #9aa0a6;")
            self._start_button.setText("Start Intercept")

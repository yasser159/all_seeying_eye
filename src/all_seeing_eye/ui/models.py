from __future__ import annotations

from typing import List

from PySide6 import QtCore

from ..core.log_types import LogEntry


class LogListModel(QtCore.QAbstractListModel):
    TimestampRole = QtCore.Qt.ItemDataRole.UserRole + 1
    LevelRole = QtCore.Qt.ItemDataRole.UserRole + 2
    MessageRole = QtCore.Qt.ItemDataRole.UserRole + 3
    DataRole = QtCore.Qt.ItemDataRole.UserRole + 4

    def __init__(self, entries: List[LogEntry] | None = None) -> None:
        super().__init__()
        self._entries: List[LogEntry] = entries or []

    def rowCount(self, parent=QtCore.QModelIndex()):  # type: ignore[override]
        return len(self._entries)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return f"{entry.timestamp.isoformat()}  {entry.level.upper()}  {entry.message}"
        if role == self.TimestampRole:
            return entry.timestamp.isoformat()
        if role == self.LevelRole:
            return entry.level
        if role == self.MessageRole:
            return entry.message
        if role == self.DataRole:
            return entry.data
        return None

    def roles(self):  # type: ignore[override]
        return {
            self.TimestampRole: b"timestamp",
            self.LevelRole: b"level",
            self.MessageRole: b"message",
            self.DataRole: b"data",
        }

    def set_entries(self, entries: List[LogEntry]) -> None:
        self.beginResetModel()
        self._entries = entries
        self.endResetModel()

    def append_entry(self, entry: LogEntry) -> None:
        self.beginInsertRows(QtCore.QModelIndex(), len(self._entries), len(self._entries))
        self._entries.append(entry)
        self.endInsertRows()

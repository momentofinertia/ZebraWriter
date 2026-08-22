from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from thermal_app.domain.models import Preset


class PresetPanel(QWidget):
    refresh_requested = Signal()
    print_requested = Signal(str)
    load_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("presetPanel")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(("Ad", "Şablon", "Kağıt"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        refresh = QPushButton("Yenile")
        one_click = QPushButton("Tek tık yazdır")
        load = QPushButton("Editörde aç")
        delete = QPushButton("Sil")
        refresh.clicked.connect(self.refresh_requested)
        one_click.clicked.connect(lambda: self._emit_selected(self.print_requested))
        load.clicked.connect(lambda: self._emit_selected(self.load_requested))
        delete.clicked.connect(lambda: self._emit_selected(self.delete_requested))
        buttons = QHBoxLayout()
        for button in (refresh, one_click, load, delete):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel("Dashboard — hazır örnekler ve kullanıcı presetleri"))
        layout.addLayout(buttons)
        layout.addWidget(self.table, 1)

    def set_presets(self, presets: list[Preset]) -> None:
        self.table.setRowCount(0)
        for preset in presets:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (preset.name, preset.template_id, preset.paper_profile_id)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(256, preset.id)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _selected(self) -> str | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is None:
            return None
        return str(item.data(256))

    def _emit_selected(self, signal: Signal) -> None:
        selected = self._selected()
        if selected:
            signal.emit(selected)

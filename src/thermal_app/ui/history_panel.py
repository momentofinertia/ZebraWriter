from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from thermal_app.domain.models import PrintJob
from thermal_app.ui.localization import tr


class HistoryPanel(QWidget):
    refresh_requested = Signal()
    preview_requested = Signal(str)
    reprint_requested = Signal(str)
    edit_requested = Signal(str)
    cancel_requested = Signal(str)
    delete_requested = Signal(str)
    delete_filtered_requested = Signal()
    delete_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Tarih", "Şablon", "Durum", "Kuyruk işi", "Kaynak"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        refresh = QPushButton("Yenile")
        preview = QPushButton("Önizle")
        reprint = QPushButton("Tekrar yazdır / retry")
        edit = QPushButton("Kopyala ve düzenle")
        cancel = QPushButton("Kuyruktan iptal et")
        delete = QPushButton("Geçmişten sil")
        self.start_date = QLineEdit()
        self.start_date.setPlaceholderText("Başlangıç YYYY-AA-GG")
        self.end_date = QLineEdit()
        self.end_date.setPlaceholderText("Bitiş YYYY-AA-GG")
        self.status_filter = QComboBox()
        self.status_filter.addItem("Tüm durumlar", "")
        for value, label in (
            ("ready", "Hazır"),
            ("submitting", "Kuyruğa gönderiliyor"),
            ("submitted", "Gönderildi"),
            ("failed", "Başarısız"),
            ("cancelled", "İptal edildi"),
        ):
            self.status_filter.addItem(label, value)
        filtered_delete = QPushButton("Filtreli geçmişi sil")
        all_delete = QPushButton("Tüm geçmişi sil")
        refresh.clicked.connect(self.refresh_requested)
        preview.clicked.connect(lambda: self._emit_selected(self.preview_requested))
        reprint.clicked.connect(lambda: self._emit_selected(self.reprint_requested))
        edit.clicked.connect(lambda: self._emit_selected(self.edit_requested))
        cancel.clicked.connect(lambda: self._emit_selected(self.cancel_requested))
        delete.clicked.connect(lambda: self._emit_selected(self.delete_requested))
        filtered_delete.clicked.connect(self.delete_filtered_requested)
        all_delete.clicked.connect(self.delete_all_requested)
        buttons = QHBoxLayout()
        for button in (refresh, preview, reprint, edit, cancel, delete):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel("Baskı geçmişi — ‘gönderildi’ fiziksel baskı garantisi değildir."))
        layout.addLayout(buttons)
        filters = QHBoxLayout()
        filters.addWidget(self.start_date)
        filters.addWidget(self.end_date)
        filters.addWidget(self.status_filter)
        refresh_filters = QPushButton("Filtrele")
        refresh_filters.clicked.connect(self.refresh_requested)
        filters.addWidget(refresh_filters)
        filters.addWidget(filtered_delete)
        filters.addWidget(all_delete)
        layout.addLayout(filters)
        self.summary = QLabel("0 kayıt")
        layout.addWidget(self.summary)
        layout.addWidget(self.table, 1)

    def set_jobs(self, jobs: list[PrintJob]) -> None:
        self.table.setRowCount(0)
        for job in jobs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                job.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                job.template_id,
                tr(job.status.value),
                job.transport_job_id or "—",
                job.source,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(256, job.id)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.summary.setText(f"{len(jobs)} " + ("records" if tr("Hazır") == "Ready" else "kayıt"))

    def filter_values(self) -> tuple[str, str, str]:
        return (
            self.start_date.text().strip(),
            self.end_date.text().strip(),
            str(self.status_filter.currentData() or ""),
        )

    def _emit_selected(self, signal: Signal) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            signal.emit(str(item.data(256)))

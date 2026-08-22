from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from thermal_app.application.dto import TodoistSyncResult
from thermal_app.ui.localization import tr


class TodoistPanel(QWidget):
    connect_requested = Signal(str)
    disconnect_requested = Signal()
    sync_requested = Signal(str, object, str)
    use_todo_requested = Signal(object)
    use_shopping_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("todoistPanel")
        self._result: TodoistSyncResult | None = None
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("Kişisel API tokenı — yalnızca keyring’e kaydedilir")
        connect = QPushButton("Bağlan ve doğrula")
        disconnect = QPushButton("Bağlantıyı kaldır")
        connect.clicked.connect(lambda: self.connect_requested.emit(self.token.text()))
        disconnect.clicked.connect(self.disconnect_requested)
        self.mode = QComboBox()
        self.mode.addItem("Bugün", "today")
        self.mode.addItem("Geciken", "overdue")
        self.mode.addItem("Bugün + geciken", "today_overdue")
        self.mode.addItem("Yaklaşan 7 gün", "upcoming")
        self.mode.addItem("Proje", "project")
        self.mode.addItem("Etiket", "label")
        self.mode.addItem("Öncelik", "priority")
        self.mode.addItem("Özel filtre", "custom")
        self.filter_value = QLineEdit()
        self.filter_value.setPlaceholderText("Etiket, 1-4 öncelik veya Todoist filtre sorgusu")
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self.projects = QComboBox()
        sync = QPushButton("Senkronize et")
        sync.clicked.connect(self._sync)
        self.status = QLabel("Todoist bağlı değil")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Görev", "Tarih", "Saat", "Proje", "Öncelik"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        use_todo = QPushButton("Todo şablonuna aktar")
        use_shopping = QPushButton("Alışveriş şablonuna aktar")
        use_todo.clicked.connect(lambda: self.use_todo_requested.emit(self._result))
        use_shopping.clicked.connect(lambda: self.use_shopping_requested.emit(self._result))
        credentials = QHBoxLayout()
        credentials.addWidget(connect)
        credentials.addWidget(disconnect)
        filters = QFormLayout()
        filters.addRow("Filtre", self.mode)
        filters.addRow("Proje", self.projects)
        filters.addRow("Filtre değeri", self.filter_value)
        filters.addRow("", sync)
        actions = QHBoxLayout()
        actions.addWidget(use_todo)
        actions.addWidget(use_shopping)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel("Todoist kişisel token bağlantısı"))
        layout.addWidget(self.token)
        layout.addLayout(credentials)
        layout.addLayout(filters)
        layout.addWidget(self.status)
        layout.addWidget(self.table, 1)
        layout.addLayout(actions)
        self._mode_changed()

    def set_connected(self, connected: bool, detail: str = "") -> None:
        self.status.setText(detail or tr("Todoist bağlı" if connected else "Todoist bağlı değil"))
        if connected:
            self.token.clear()

    def set_projects(self, projects: dict[str, str]) -> None:
        current = self.projects.currentData()
        self.projects.clear()
        for project_id, name in sorted(projects.items(), key=lambda item: item[1].casefold()):
            self.projects.addItem(name, project_id)
        if current:
            index = self.projects.findData(current)
            if index >= 0:
                self.projects.setCurrentIndex(index)

    def set_result(self, result: TodoistSyncResult) -> None:
        self._result = result
        self.projects.blockSignals(True)
        self.set_projects(result.projects)
        self.projects.blockSignals(False)
        self.table.setRowCount(0)
        for task in result.tasks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (task.title, task.due_date or "", task.due_time or "", task.project or "", str(task.priority))
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        prefix = tr("ESKİ CACHE" if result.stale else "Güncel")
        warning = f" — {result.warning}" if result.warning else ""
        task_word = "tasks" if tr("Görev") == "Task" else "görev"
        self.status.setText(f"{prefix}: {result.synced_at:%d.%m.%Y %H:%M} — {len(result.tasks)} {task_word}{warning}")

    def _sync(self) -> None:
        mode = str(self.mode.currentData())
        project_id = self.projects.currentData() if mode == "project" else None
        self.sync_requested.emit(mode, project_id, self.filter_value.text().strip())

    def _mode_changed(self) -> None:
        mode = str(self.mode.currentData())
        self.projects.setEnabled(mode == "project")
        self.filter_value.setEnabled(mode in {"label", "priority", "custom"})

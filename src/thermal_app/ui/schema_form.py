from __future__ import annotations

from collections.abc import Mapping
import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from thermal_app.domain.models import TemplateDefinition
from thermal_app.ui.localization import tr


class ImageField(QWidget):
    changed = Signal()

    def __init__(self, default: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.path = QLineEdit(default)
        browse = QPushButton(tr("Seç…"))
        browse.clicked.connect(self._browse)
        self.path.textChanged.connect(self.changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.path, 1)
        layout.addWidget(browse)

    def _browse(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            tr("Fotoğraf seç"),
            "",
            tr("Görseller (*.png *.jpg *.jpeg *.bmp *.webp)"),
        )
        if selected:
            self.path.setText(selected)

    def value(self) -> str:
        return self.path.text().strip()


class TableField(QWidget):
    changed = Signal()

    def __init__(self, columns: list[Mapping[str, object]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = columns
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels([str(column.get("label", column["key"])) for column in columns])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(130)
        self.table.cellChanged.connect(self.changed)
        add = QPushButton(tr("Satır ekle"))
        remove = QPushButton(tr("Seçili satırı sil"))
        add.clicked.connect(self.add_row)
        remove.clicked.connect(self.remove_selected)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(remove)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self.add_row()

    def add_row(self) -> None:
        self.table.insertRow(self.table.rowCount())
        self.changed.emit()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def value(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row_index in range(self.table.rowCount()):
            row: dict[str, str] = {}
            for column_index, column in enumerate(self._columns):
                item = self.table.item(row_index, column_index)
                row[str(column["key"])] = item.text().strip() if item else ""
            if any(row.values()):
                rows.append(row)
        return rows

    def set_value(self, rows: object) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        values = rows if isinstance(rows, list) else []
        for raw_row in values:
            if not isinstance(raw_row, Mapping):
                continue
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)
            for column_index, column in enumerate(self._columns):
                self.table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(str(raw_row.get(str(column["key"]), ""))),
                )
        if self.table.rowCount() == 0:
            self.table.insertRow(0)
        self.table.blockSignals(False)
        self.changed.emit()


class SchemaForm(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("schemaForm")
        self._form = QFormLayout(self)
        self._form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self._form.setHorizontalSpacing(14)
        self._form.setVerticalSpacing(10)
        self._widgets: dict[str, tuple[str, QWidget]] = {}

    def set_definition(self, definition: TemplateDefinition) -> None:
        while self._form.count():
            item = self._form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._widgets.clear()
        for key, raw_spec in definition.input_schema.items():
            spec = dict(raw_spec)
            field_type = str(spec["type"])
            widget = self._create_widget(field_type, spec)
            self._widgets[key] = (field_type, widget)
            self._form.addRow(tr(str(spec.get("label", key))), widget)

    def _create_widget(self, field_type: str, spec: Mapping[str, object]) -> QWidget:
        default = spec.get("default")
        if field_type == "text":
            widget = QLineEdit(str(default or ""))
            widget.textChanged.connect(self.changed)
            return widget
        if field_type in {"multiline", "list"}:
            widget = QPlainTextEdit()
            widget.setMaximumHeight(110)
            if field_type == "list":
                widget.setPlaceholderText(tr("Her satıra bir öğe"))
                widget.setPlainText("\n".join(str(item) for item in (default or [])))
            else:
                widget.setPlainText(str(default or ""))
            widget.textChanged.connect(self.changed)
            return widget
        if field_type == "boolean":
            widget = QCheckBox()
            widget.setChecked(bool(default))
            widget.toggled.connect(self.changed)
            return widget
        if field_type == "choice":
            widget = QComboBox()
            choices = [str(choice) for choice in spec.get("choices", [])]
            widget.addItems(choices)
            if default in choices:
                widget.setCurrentText(str(default))
            widget.currentTextChanged.connect(self.changed)
            return widget
        if field_type == "table":
            widget = TableField(list(spec.get("columns", [])))
            widget.set_value(default)
            widget.changed.connect(self.changed)
            return widget
        if field_type == "image":
            widget = ImageField(str(default or ""))
            widget.changed.connect(self.changed)
            return widget
        if field_type == "blocks":
            widget = QPlainTextEdit()
            widget.setReadOnly(True)
            widget.setMaximumHeight(130)
            widget.setPlainText(json.dumps(default or [], ensure_ascii=False, indent=2))
            return widget
        raise ValueError(f"{tr('Desteklenmeyen form alanı: ')}{field_type}")

    def values(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, (field_type, widget) in self._widgets.items():
            if field_type == "text":
                result[key] = widget.text()
            elif field_type == "multiline":
                result[key] = widget.toPlainText()
            elif field_type == "list":
                result[key] = [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]
            elif field_type == "boolean":
                result[key] = widget.isChecked()
            elif field_type == "choice":
                result[key] = widget.currentText()
            elif field_type == "table":
                result[key] = widget.value()
            elif field_type == "image":
                result[key] = widget.value()
            elif field_type == "blocks":
                try:
                    decoded = json.loads(widget.toPlainText())
                except json.JSONDecodeError:
                    decoded = []
                result[key] = decoded if isinstance(decoded, list) else []
        return result

    def set_values(self, values: Mapping[str, object]) -> None:
        for key, value in values.items():
            entry = self._widgets.get(key)
            if entry is None:
                continue
            field_type, widget = entry
            if field_type == "text":
                widget.setText(str(value or ""))
            elif field_type == "multiline":
                widget.setPlainText(str(value or ""))
            elif field_type == "list":
                items = value if isinstance(value, list) else []
                widget.setPlainText("\n".join(str(item) for item in items))
            elif field_type == "boolean":
                widget.setChecked(bool(value))
            elif field_type == "choice":
                widget.setCurrentText(str(value))
            elif field_type == "table":
                widget.set_value(value)
            elif field_type == "image":
                widget.path.setText(str(value or ""))
            elif field_type == "blocks":
                widget.setPlainText(json.dumps(value if isinstance(value, list) else [], ensure_ascii=False, indent=2))

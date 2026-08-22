from __future__ import annotations

from io import BytesIO
from pathlib import Path
from collections.abc import Mapping
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from thermal_app.application.template_catalog import custom_definition
from thermal_app.application.services.document_import_service import DocumentImportService
from thermal_app.application.services.custom_template_service import CustomTemplateService
from thermal_app.application.dto import RenderOptions
from thermal_app.domain.models import PaperProfile, TemplateDefinition
from thermal_app.domain.template_schema import normalize_template_input
from thermal_app.ui.schema_form import SchemaForm
from thermal_app.infrastructure.artifacts.local_artifact_store import document_to_image
from thermal_app.ui.localization import localize_widget_tree, tr


BLOCK_TYPES = (
    ("text", "Metin"),
    ("heading", "Başlık"),
    ("divider", "Ayraç"),
    ("spacer", "Boşluk"),
    ("section_band", "Bölüm bandı"),
    ("key_value", "Anahtar / değer"),
    ("checklist", "Checkbox satırı"),
    ("image", "Görsel"),
    ("qr", "QR"),
)


class CustomDesignerPanel(QWidget):
    template_saved = Signal(str)
    template_deleted = Signal(str)
    open_requested = Signal(str)
    design_changed = Signal()
    preset_save_requested = Signal()

    def __init__(
        self,
        templates: CustomTemplateService,
        document_importer: DocumentImportService,
        renderer: object,
        paper_provider: Callable[[], PaperProfile | None],
        template_provider: Callable[[], list[TemplateDefinition]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("designerPanel")
        self._templates = templates
        self._document_importer = document_importer
        self._renderer = renderer
        self._paper_provider = paper_provider
        self._template_provider = template_provider or (lambda: [])
        self._template_id: str | None = None
        self._active_definition: TemplateDefinition | None = None
        self._builtin_mode = False
        self._source_reference: str | None = None
        self._blocks: list[dict[str, object]] = []
        self._render_options_data: dict[str, object] = {}
        self._loading = False

        self._template_combo = QComboBox()
        self._name = QLineEdit()
        self._category = QLineEdit(tr("Özel"))
        self._style = QComboBox()
        self._style.addItem("Sade", "plain")
        self._style.addItem("Grafikli", "graphic")
        new_button = QPushButton("Yeni")
        import_button = QPushButton("Belge aktar")
        save_button = QPushButton("Kaydet")
        delete_button = QPushButton("Sil")
        open_button = QPushButton("Yazdırma ekranına geç")
        preset_button = QPushButton("Preset olarak kaydet")
        self._save_button = save_button
        self._delete_button = delete_button
        new_button.clicked.connect(self.new_template)
        import_button.clicked.connect(self.import_document)
        save_button.clicked.connect(self.save_template)
        delete_button.clicked.connect(self.delete_template)
        open_button.clicked.connect(self.open_in_editor)
        preset_button.clicked.connect(self.preset_save_requested)

        header = QFormLayout()
        header.addRow("Şablon", self._template_combo)
        header.addRow("Ad", self._name)
        header.addRow("Kategori", self._category)
        header.addRow("Görsel stil", self._style)
        actions = QHBoxLayout()
        for button in (new_button, import_button, save_button, delete_button, open_button, preset_button):
            actions.addWidget(button)
        left = QVBoxLayout()
        left.addLayout(header)
        left.addLayout(actions)
        self._schema_form = SchemaForm()
        self._schema_form.changed.connect(self._schema_changed)
        left.addWidget(self._schema_form, 1)
        self._block_list = QListWidget()
        self._block_list.currentRowChanged.connect(self._load_selected_block)
        block_section = QWidget()
        block_section_layout = QVBoxLayout(block_section)
        block_section_layout.setContentsMargins(0, 0, 0, 0)
        block_section_layout.addWidget(QLabel("Bloklar"))
        block_section_layout.addWidget(self._block_list, 1)
        block_actions = QHBoxLayout()
        add = QPushButton("Blok ekle")
        duplicate = QPushButton("Çoğalt")
        up = QPushButton("Yukarı")
        down = QPushButton("Aşağı")
        remove = QPushButton("Sil")
        add.clicked.connect(self.add_block)
        duplicate.clicked.connect(self.duplicate_block)
        up.clicked.connect(lambda: self.move_block(-1))
        down.clicked.connect(lambda: self.move_block(1))
        remove.clicked.connect(self.remove_block)
        for button in (add, duplicate, up, down, remove):
            block_actions.addWidget(button)
        block_section_layout.addLayout(block_actions)
        left.addWidget(block_section, 1)
        self._block_section = block_section

        self._block_type = QComboBox()
        for value, label in BLOCK_TYPES:
            self._block_type.addItem(label, value)
        self._value = QLineEdit()
        self._secondary = QLineEdit()
        self._style_field = QComboBox()
        self._style_field.addItems(("body", "small", "heading", "title"))
        self._align = QComboBox()
        self._align.addItems(("left", "center", "right"))
        self._checked = QCheckBox("İşaretli")
        self._number = QSpinBox()
        self._number.setRange(2, 240)
        self._number.setValue(12)
        self._block_form = QFormLayout()
        self._block_form.addRow("Tip", self._block_type)
        self._block_form.addRow("Değer / metin", self._value)
        self._block_form.addRow("İkincil değer", self._secondary)
        self._block_form.addRow("Metin stili", self._style_field)
        self._block_form.addRow("Hizalama", self._align)
        self._block_form.addRow("Boşluk / kalınlık (dot)", self._number)
        self._block_form.addRow("Checkbox", self._checked)
        for widget, signal in (
            (self._block_type, "currentIndexChanged"),
            (self._value, "textChanged"),
            (self._secondary, "textChanged"),
            (self._style_field, "currentIndexChanged"),
            (self._align, "currentIndexChanged"),
            (self._number, "valueChanged"),
            (self._checked, "toggled"),
        ):
            getattr(widget, signal).connect(self._apply_selected_block)
        right = QVBoxLayout()
        self._block_properties = QWidget()
        block_properties_layout = QVBoxLayout(self._block_properties)
        block_properties_layout.setContentsMargins(0, 0, 0, 0)
        block_properties_layout.addWidget(QLabel("Seçili blok"))
        block_properties_layout.addLayout(self._block_form)
        right.addWidget(self._block_properties)
        self._preview = QLabel("Önizleme hazırlanmadı")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumWidth(320)
        right.addWidget(self._preview, 1)
        self._status = QLabel("Yeni bir özel şablon oluşturun veya belge aktarın.")
        right.addWidget(self._status)

        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([520, 520])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(splitter)
        self._template_combo.currentIndexChanged.connect(self._load_template)
        self._style.currentIndexChanged.connect(self._style_changed)
        self._schema_form.setVisible(False)
        self.refresh_templates()
        self.new_template()
        localize_widget_tree(self)

    def refresh_templates(self) -> None:
        current = self._template_id
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        for template in self._template_provider():
            self._template_combo.addItem(template.name, template.id)
        self._template_combo.blockSignals(False)
        if current:
            index = self._template_combo.findData(current)
            if index >= 0:
                self._template_combo.setCurrentIndex(index)

    def new_template(self) -> None:
        self._template_id = None
        self._active_definition = None
        self._builtin_mode = False
        self._source_reference = None
        self._name.setText(tr("Yeni fiş"))
        self._category.setText(tr("Özel"))
        self._name.setReadOnly(False)
        self._category.setReadOnly(False)
        self._blocks = [
            {"type": "heading", "value": tr("Yeni fiş")},
            {"type": "text", "value": tr("İçeriğinizi buraya yazın.")},
        ]
        self._schema_form.setVisible(False)
        self._block_section.setVisible(True)
        self._block_properties.setVisible(True)
        self._save_button.setEnabled(True)
        self._delete_button.setEnabled(False)
        self._rebuild_block_list()
        self._render_preview()
        self.design_changed.emit()

    def _load_template(self) -> None:
        if self._loading:
            return
        template_id = self._template_combo.currentData()
        if not template_id:
            return
        template = next(
            (item for item in self._template_provider() if item.id == str(template_id)),
            None,
        )
        if template is None:
            return
        self.set_design(template.id, {}, self._render_options_data)

    def set_design(
        self,
        template_id: str,
        data: Mapping[str, object] | None = None,
        render_options: Mapping[str, object] | None = None,
        *,
        source: str = "manual-template",
        source_reference: str | None = None,
    ) -> None:
        template = next(
            (item for item in self._template_provider() if item.id == template_id),
            None,
        )
        if template is None:
            return
        self._loading = True
        self._template_id = template.id
        self._active_definition = template
        self._builtin_mode = not template.id.startswith("custom-") and template.renderer_key != "custom.blocks"
        self._source_reference = source_reference
        self._render_options_data = dict(render_options or {})
        style = str(self._render_options_data.get("visual_style", "plain"))
        style_index = self._style.findData(style)
        self._style.setCurrentIndex(style_index if style_index >= 0 else 0)
        self._name.setText(template.name)
        self._category.setText(template.category)
        if self._builtin_mode:
            values = normalize_template_input(template, data or {})
            self._schema_form.set_definition(template)
            self._schema_form.set_values(values)
            self._schema_form.setVisible(True)
            self._block_section.setVisible(False)
            self._block_properties.setVisible(False)
            self._save_button.setEnabled(False)
            self._delete_button.setEnabled(False)
            self._name.setReadOnly(True)
            self._category.setReadOnly(True)
        else:
            custom = self._templates.get(template.id)
            self._blocks = [dict(block) for block in (custom.blocks if custom else (data or {}).get("blocks", []))]
            self._schema_form.setVisible(False)
            self._block_section.setVisible(True)
            self._block_properties.setVisible(True)
            self._save_button.setEnabled(True)
            self._delete_button.setEnabled(bool(self._template_id))
            self._name.setReadOnly(False)
            self._category.setReadOnly(False)
            self._rebuild_block_list()
        combo_index = self._template_combo.findData(template.id)
        if combo_index >= 0:
            self._template_combo.setCurrentIndex(combo_index)
        self._loading = False
        self._render_preview()
        self.design_changed.emit()

    def current_design(self) -> tuple[str, dict[str, object], dict[str, object], str, str | None] | None:
        if self._active_definition is None or self._template_id is None:
            return None
        if self._builtin_mode:
            data = self._schema_form.values()
        else:
            data = {"blocks": [dict(block) for block in self._blocks]}
        source = "document-import" if self._source_reference else "manual-template"
        return self._template_id, data, dict(self._render_options_data), source, self._source_reference

    def set_render_options(self, values: Mapping[str, object]) -> None:
        self._render_options_data = dict(values)
        style = str(values.get("visual_style", "plain"))
        index = self._style.findData(style)
        if index >= 0:
            self._style.blockSignals(True)
            self._style.setCurrentIndex(index)
            self._style.blockSignals(False)
        self._render_preview()

    def _schema_changed(self) -> None:
        if self._loading:
            return
        self._render_preview()
        self.design_changed.emit()

    def _style_changed(self) -> None:
        self._render_options_data["visual_style"] = str(self._style.currentData())
        self._render_preview()
        self.design_changed.emit()

    def _rebuild_block_list(self) -> None:
        self._block_list.blockSignals(True)
        self._block_list.clear()
        for index, block in enumerate(self._blocks, 1):
            label = str(block.get("value") or block.get("label") or block.get("type") or "blok")
            self._block_list.addItem(QListWidgetItem(f"{index}. {block.get('type', 'text')} — {label[:50]}"))
        self._block_list.blockSignals(False)
        if self._blocks:
            self._block_list.setCurrentRow(max(0, min(self._block_list.currentRow(), len(self._blocks) - 1)))

    def _load_selected_block(self, row: int) -> None:
        if row < 0 or row >= len(self._blocks):
            return
        block = self._blocks[row]
        self._loading = True
        index = self._block_type.findData(block.get("type", "text"))
        self._block_type.setCurrentIndex(max(index, 0))
        self._value.setText(str(block.get("value", "")))
        self._secondary.setText(str(block.get("secondary", "")))
        self._style_field.setCurrentText(str(block.get("style", "body")))
        self._align.setCurrentText(str(block.get("align", "left")))
        self._number.setValue(int(block.get("height", block.get("thickness", 12))))
        self._checked.setChecked(bool(block.get("checked", False)))
        self._loading = False

    def _apply_selected_block(self) -> None:
        if self._loading:
            return
        row = self._block_list.currentRow()
        if row < 0 or row >= len(self._blocks):
            return
        kind = str(self._block_type.currentData())
        block: dict[str, object] = {"type": kind, "value": self._value.text().strip()}
        if kind in {"text", "heading"}:
            block["style"] = self._style_field.currentText()
            block["align"] = self._align.currentText()
        if kind in {"key_value", "checklist", "qr"}:
            block["secondary"] = self._secondary.text().strip()
        if kind == "checklist":
            block["checked"] = self._checked.isChecked()
        if kind == "divider":
            block["thickness"] = self._number.value()
        if kind == "spacer":
            block["height"] = self._number.value()
        self._blocks[row] = block
        self._rebuild_block_list()
        self._block_list.setCurrentRow(row)
        self._render_preview()
        self.design_changed.emit()

    def add_block(self) -> None:
        self._blocks.append({"type": "text", "value": tr("Yeni metin")})
        self._rebuild_block_list()
        self._block_list.setCurrentRow(len(self._blocks) - 1)
        self._render_preview()
        self.design_changed.emit()

    def duplicate_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0:
            return
        self._blocks.insert(row + 1, dict(self._blocks[row]))
        self._rebuild_block_list()
        self._block_list.setCurrentRow(row + 1)
        self._render_preview()
        self.design_changed.emit()

    def move_block(self, delta: int) -> None:
        row = self._block_list.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= len(self._blocks):
            return
        self._blocks[row], self._blocks[target] = self._blocks[target], self._blocks[row]
        self._rebuild_block_list()
        self._block_list.setCurrentRow(target)
        self._render_preview()
        self.design_changed.emit()

    def remove_block(self) -> None:
        row = self._block_list.currentRow()
        if row < 0:
            return
        self._blocks.pop(row)
        self._rebuild_block_list()
        self._render_preview()
        self.design_changed.emit()

    def import_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Belge aktar"),
            "",
            tr("Belgeler (*.pdf *.epub *.docx)"),
        )
        if not path:
            return
        try:
            document = self._document_importer.import_document(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Belge aktarılamadı"), str(exc))
            return
        self._template_id = None
        self._source_reference = str(path)
        self._name.setText(document.title)
        self._category.setText(tr("Belge"))
        self._blocks = [dict(block) for block in document.blocks]
        self._rebuild_block_list()
        warning = " ".join(document.warnings)
        if tr("Hazır") == "Ready":
            self._status.setText(f"Imported {document.source_format.upper()}: {len(self._blocks)} blocks. {warning}")
        else:
            self._status.setText(f"{document.source_format.upper()} aktarıldı: {len(self._blocks)} blok. {warning}")
        self._render_preview()

    @property
    def source_reference(self) -> str | None:
        return self._source_reference

    def save_template(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, tr("Eksik ad"), tr("Özel şablon adı boş olamaz."))
            return
        if not self._blocks:
            QMessageBox.warning(self, tr("Blok yok"), tr("En az bir blok ekleyin."))
            return
        template = self._templates.save(name, self._category.text(), tuple(self._blocks), self._template_id)
        self._template_id = template.id
        self._delete_button.setEnabled(True)
        self.refresh_templates()
        prefix = "Saved" if tr("Hazır") == "Ready" else "Kaydedildi"
        self._status.setText(f"{prefix}: {template.name}")
        self._render_preview()
        self.template_saved.emit(template.id)

    def delete_template(self) -> None:
        if not self._template_id:
            return
        deleted_id = self._template_id
        if QMessageBox.question(self, tr("Özel şablonu sil"), tr("Bu özel şablon silinsin mi?")) != QMessageBox.Yes:
            return
        self._templates.delete(self._template_id)
        self.template_deleted.emit(deleted_id)
        self._template_id = None
        self.refresh_templates()
        self.new_template()

    def open_in_editor(self) -> None:
        if self._template_id:
            self.open_requested.emit(self._template_id)
        else:
            self.save_template()
            if self._template_id:
                self.open_requested.emit(self._template_id)

    def _render_preview(self) -> None:
        paper = self._paper_provider()
        if paper is None:
            return
        try:
            if self._builtin_mode and self._active_definition is not None:
                definition = self._active_definition
                data = self._schema_form.values()
            else:
                definition = custom_definition("custom.preview", self._name.text() or "Özel fiş", "Özel", self._blocks)
                data = {"blocks": self._blocks}
            document = self._renderer.render(
                definition,
                data,
                paper,
                RenderOptions(visual_style=str(self._style.currentData())),
            )
            output = BytesIO()
            document_to_image(document).save(output, "PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(output.getvalue(), "PNG")
            self._preview.setPixmap(pixmap.scaled(380, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as exc:
            prefix = "Preview error" if tr("Hazır") == "Ready" else "Önizleme hatası"
            self._preview.setText(f"{prefix}: {exc}")

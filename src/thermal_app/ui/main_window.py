from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, replace
from datetime import datetime, time, timedelta
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QColor, QPalette, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from thermal_app.application.dto import RenderOptions, TodoistSyncResult
from thermal_app import __version__
from thermal_app.application.services.print_service import TEST_PAGE_TEMPLATE
from thermal_app.application.template_catalog import custom_definition
from thermal_app.bootstrap import ApplicationContext
from thermal_app.domain.errors import (
    ThermalAppError,
    TodoistAuthError,
    TodoistNetworkError,
    TodoistRateLimitError,
)
from thermal_app.domain.models import (
    CALIBRATION_OFFSET_LIMIT_DOTS,
    PaperProfile,
    Preset,
    PrinterProfile,
    PrintJob,
    TemplateDefinition,
)
from thermal_app.domain.enums import PrintJobStatus
from thermal_app.rendering.thermal import DITHERING_ALGORITHMS
from thermal_app.ui.history_panel import HistoryPanel
from thermal_app.ui.custom_designer_panel import CustomDesignerPanel
from thermal_app.ui.collapsible_section import CollapsibleSection
from thermal_app.ui.paper_dialog import CustomPaperDialog
from thermal_app.ui.preset_panel import PresetPanel
from thermal_app.ui.schema_form import SchemaForm
from thermal_app.ui.settings_panel import SettingsPanel
from thermal_app.ui.todoist_panel import TodoistPanel
from thermal_app.ui.workers import Worker
from thermal_app.ui.localization import localize_widget_tree, set_language, tr


LOGGER = logging.getLogger("thermal_app.ui")


class MainWindow(QMainWindow):
    def __init__(self, context: ApplicationContext) -> None:
        super().__init__()
        app = QApplication.instance()
        # Keep the platform palette untouched so that switching back to
        # "system" can restore it after an explicit light/dark selection.
        self._system_palette = QPalette(app.palette()) if app is not None else QPalette()
        self._context = context
        set_language(context.settings_service.language())
        self._pool = QThreadPool.globalInstance()
        self._workers: list[Worker] = []
        self._preview_pixmap: QPixmap | None = None
        self._latest_job: PrintJob | None = None
        self._editor_integration_profile_id: str | None = None
        self._editor_filter_spec: dict[str, object] = {}
        self._editor_source = "manual-template"
        self._editor_source_reference: str | None = None
        self._preview_request = 0
        self.setWindowTitle("ZebraWriter — GC420t")
        self.resize(1180, 820)

        self._printer_combo = QComboBox()
        self._paper_combo = QComboBox()
        self._template_combo = QComboBox()
        self._refresh_button = QPushButton("Yazıcıyı yenile")
        self._new_paper_button = QPushButton("Yeni")
        self._edit_paper_button = QPushButton("Düzenle")
        self._delete_paper_button = QPushButton("Sil")
        self._save_preset_button = QPushButton("Preset kaydet")
        self._refresh_button.setObjectName("secondaryButton")
        self._new_paper_button.setObjectName("secondaryButton")
        self._edit_paper_button.setObjectName("secondaryButton")
        self._delete_paper_button.setObjectName("dangerButton")
        self._save_preset_button.setObjectName("secondaryButton")
        self._form = SchemaForm()

        self._calibration_panel = QFrame()
        self._calibration_panel.setObjectName("calibrationCard")
        self._calibration_offset = QSpinBox()
        self._calibration_offset.setObjectName("horizontalCalibrationOffset")
        self._calibration_offset.setSuffix(" dot")
        self._calibration_left_button = QPushButton("1 dot sola")
        self._calibration_right_button = QPushButton("1 dot sağa")
        self._calibration_save_button = QPushButton("Ofseti kağıt profiline kaydet")
        calibration_layout = QVBoxLayout(self._calibration_panel)
        calibration_layout.setContentsMargins(10, 10, 10, 10)
        calibration_layout.addWidget(QLabel("Yatay baskı kalibrasyonu"))
        calibration_hint = QLabel("Negatif değer sola, pozitif değer sağa taşır.")
        calibration_hint.setWordWrap(True)
        calibration_layout.addWidget(calibration_hint)
        calibration_warning = QLabel(
            "±12 dot dışındaki değerler 56 mm kağıtta içeriğin bir bölümünü sınır dışına taşıyabilir."
        )
        calibration_warning.setWordWrap(True)
        calibration_layout.addWidget(calibration_warning)
        calibration_layout.addWidget(self._calibration_offset)
        calibration_buttons = QHBoxLayout()
        calibration_buttons.addWidget(self._calibration_left_button)
        calibration_buttons.addWidget(self._calibration_right_button)
        calibration_layout.addLayout(calibration_buttons)
        calibration_layout.addWidget(self._calibration_save_button)
        self._calibration_panel.setVisible(False)

        self._dithering = QComboBox()
        for algorithm in DITHERING_ALGORITHMS:
            self._dithering.addItem(algorithm.replace("-", " ").title(), algorithm)
        self._visual_style = QComboBox()
        self._visual_style.addItem("Sade", "plain")
        self._visual_style.addItem("Grafikli", "graphic")
        self._brightness = QDoubleSpinBox()
        self._contrast = QDoubleSpinBox()
        for spin in (self._brightness, self._contrast):
            spin.setRange(0.2, 2.0)
            spin.setSingleStep(0.1)
            spin.setValue(1.0)
        self._threshold = QSpinBox()
        self._threshold.setRange(0, 255)
        self._threshold.setValue(160)
        self._sharpen = QCheckBox("Keskinleştir")
        self._invert = QCheckBox("Ters çevir")
        self._zoom = QComboBox()
        self._zoom.addItem("Genişliğe sığdır", "fit-width")
        self._zoom.addItem("Pencereye sığdır", "fit-window")
        self._zoom.addItem("100%", "100")
        self._zoom.addItem("200%", "200")

        self._preview_button = QPushButton("Önizle")
        self._preview_button.setObjectName("accentButton")
        self._toggle_preview_button = QPushButton("Önizlemeyi gizle")
        self._toggle_preview_button.setObjectName("secondaryButton")
        self._print_button = QPushButton("YAZDIR")
        self._print_button.setObjectName("primaryButton")
        self._status = QLabel("GC420t aranıyor…")
        self._status.setObjectName("statusLabel")
        self._preview = QLabel("Önizleme hazırlanmadı")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setObjectName("previewCanvas")
        self._preview.setStyleSheet("background: #e3e1dc; color: #697077;")
        self._preview_padding = 24

        controls = QFrame()
        controls.setObjectName("controlCard")
        controls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setSizeConstraint(QLayout.SetMinimumSize)
        controls_layout.setAlignment(Qt.AlignTop)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        page_title = QLabel("Baskı oluştur")
        page_title.setObjectName("pageTitle")
        page_hint = QLabel("Şablonu düzenleyin ve sonucu baskıdan önce kontrol edin.")
        page_hint.setObjectName("sectionHint")
        page_hint.setWordWrap(True)
        controls_layout.addWidget(page_title)
        controls_layout.addWidget(page_hint)

        device_card = CollapsibleSection("1 · Yazıcı ve kağıt")
        device_layout = device_card.content_layout
        printer_label = QLabel("Zebra GC420t")
        printer_label.setObjectName("fieldLabel")
        device_layout.addWidget(printer_label)
        printer_row = QHBoxLayout()
        printer_row.addWidget(self._printer_combo, 1)
        printer_row.addWidget(self._refresh_button)
        device_layout.addLayout(printer_row)
        paper_label = QLabel("Kağıt profili")
        paper_label.setObjectName("fieldLabel")
        device_layout.addWidget(paper_label)
        device_layout.addWidget(self._paper_combo)
        paper_buttons = QHBoxLayout()
        paper_buttons.addWidget(self._new_paper_button)
        paper_buttons.addWidget(self._edit_paper_button)
        paper_buttons.addWidget(self._delete_paper_button)
        device_layout.addLayout(paper_buttons)
        controls_layout.addWidget(device_card)
        self._device_card = device_card

        content_card = QFrame()
        content_card.setObjectName("sectionCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(8)
        content_title = QLabel("2 · İçerik")
        content_title.setObjectName("sectionTitle")
        content_layout.addWidget(content_title)
        template_label = QLabel("Şablon")
        template_label.setObjectName("fieldLabel")
        content_layout.addWidget(template_label)
        content_layout.addWidget(self._template_combo)
        content_layout.addWidget(self._calibration_panel)

        content_layout.addWidget(self._form)
        designer_hint = QLabel("İçerik ve şablon düzenleme artık Tasarımcı sekmesinden yapılır.")
        designer_hint.setObjectName("sectionHint")
        designer_hint.setWordWrap(True)
        content_layout.addWidget(designer_hint)
        designer_button = QPushButton("Tasarımcıyı aç")
        designer_button.setObjectName("accentButton")
        designer_button.clicked.connect(self._open_designer)
        content_layout.addWidget(designer_button)
        self._template_combo.setVisible(False)
        self._form.setVisible(False)
        controls_layout.addWidget(content_card)

        options_card = CollapsibleSection("3 · Görüntü ayarları")
        options_layout = options_card.content_layout
        options_hint = QLabel("Fotoğraf ve grafiklerin termal baskı yoğunluğunu ayarlayın.")
        options_hint.setObjectName("sectionHint")
        options_hint.setWordWrap(True)
        options_layout.addWidget(options_hint)
        options = QGridLayout()
        options.setHorizontalSpacing(12)
        options.setVerticalSpacing(8)
        options.addWidget(QLabel("Görsel stil"), 0, 0)
        options.addWidget(self._visual_style, 0, 1)
        options.addWidget(QLabel("Tarama yöntemi"), 1, 0)
        options.addWidget(self._dithering, 1, 1)
        options.addWidget(QLabel("Parlaklık"), 2, 0)
        options.addWidget(self._brightness, 2, 1)
        options.addWidget(QLabel("Kontrast"), 3, 0)
        options.addWidget(self._contrast, 3, 1)
        options.addWidget(QLabel("Siyah eşiği"), 4, 0)
        options.addWidget(self._threshold, 4, 1)
        checks = QHBoxLayout()
        checks.addWidget(self._sharpen)
        checks.addWidget(self._invert)
        checks.addStretch(1)
        options_layout.addLayout(options)
        options_layout.addLayout(checks)
        controls_layout.addWidget(options_card)
        self._options_card = options_card

        preview_scroll = QScrollArea()
        preview_scroll.setObjectName("previewScroll")
        preview_scroll.setWidgetResizable(False)
        preview_scroll.setAlignment(Qt.AlignCenter)
        preview_scroll.setWidget(self._preview)
        self._preview_scroll = preview_scroll

        preview_card = QFrame()
        preview_card.setObjectName("previewCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(10)
        preview_toolbar = QHBoxLayout()
        preview_title = QLabel("Baskı önizlemesi")
        preview_title.setObjectName("sectionTitle")
        zoom_label = QLabel("Yakınlaştırma")
        zoom_label.setObjectName("fieldLabel")
        self._zoom.setMinimumWidth(175)
        preview_toolbar.addWidget(preview_title)
        preview_toolbar.addStretch(1)
        preview_toolbar.addWidget(zoom_label)
        preview_toolbar.addWidget(self._zoom)
        preview_layout.addLayout(preview_toolbar)
        preview_layout.addWidget(preview_scroll, 1)
        preview_card.setMinimumWidth(300)
        self._preview_card = preview_card

        actions_card = QFrame()
        actions_card.setObjectName("actionBar")
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setContentsMargins(12, 10, 12, 10)
        actions_layout.setSpacing(7)
        secondary_actions = QHBoxLayout()
        secondary_actions.addWidget(self._preview_button)
        secondary_actions.addWidget(self._toggle_preview_button)
        secondary_actions.addWidget(self._save_preset_button)
        actions_layout.addLayout(secondary_actions)
        actions_layout.addWidget(self._print_button)
        actions_layout.addWidget(self._status)

        body = QWidget()
        body.setObjectName("editorBody")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(18, 18, 18, 18)
        body_layout.setSpacing(0)
        controls_scroll = QScrollArea()
        controls_scroll.setObjectName("controlsScroll")
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.NoFrame)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_scroll.setWidget(controls)
        self._controls = controls
        self._controls_scroll = controls_scroll

        editor_panel = QWidget()
        editor_panel.setObjectName("editorPanel")
        editor_panel.setMinimumWidth(460)
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(10)
        editor_layout.addWidget(controls_scroll, 1)
        editor_layout.addWidget(actions_card)
        self._action_bar = actions_card

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("editorSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.addWidget(editor_panel)
        splitter.addWidget(preview_card)
        splitter.setStretchFactor(0, 58)
        splitter.setStretchFactor(1, 42)
        splitter.setSizes([580, 420])
        self._editor_panel = editor_panel
        self._splitter = splitter
        self._last_visible_splitter_sizes = [580, 420]
        body_layout.addWidget(splitter)
        self._tabs = QTabWidget()
        self._preset_panel = PresetPanel()
        self._history_panel = HistoryPanel()
        self._todoist_panel = TodoistPanel()
        self._settings_panel = SettingsPanel(
            str(context.paths.root),
            str(context.paths.previews.parent),
            __version__,
        )
        self._designer_panel = CustomDesignerPanel(
            context.custom_template_service,
            context.document_import_service,
            context.renderer,
            self.current_paper,
            lambda: [TEST_PAGE_TEMPLATE, *context.template_catalog.list_all()],
        )
        self._tabs.addTab(self._preset_panel, "Dashboard")
        self._editor_tab_index = self._tabs.addTab(body, "Yazdır")
        self._designer_tab_index = self._tabs.addTab(self._designer_panel, "Tasarımcı")
        self._history_tab_index = self._tabs.addTab(self._history_panel, "Geçmiş")
        self._tabs.addTab(self._todoist_panel, "Todoist")
        self._tabs.addTab(self._settings_panel, "Ayarlar")
        self.setCentralWidget(self._tabs)

        self.setStyleSheet(
            """
            QMainWindow { background: #f0efeb; }
            QFrame#controlCard { background: transparent; border: none; }
            QFrame#sectionCard, QFrame#previewCard, QFrame#actionBar { background: #fbfaf7; border: 1px solid #c7c5be; border-radius: 12px; }
            QFrame#calibrationCard { background: #f6f5f1; border: 1px solid #c7c5be; border-radius: 8px; }
            QLabel#pageTitle { color: #27313a; font-size: 21px; font-weight: 700; }
            QLabel#sectionTitle { color: #27313a; font-size: 14px; font-weight: 700; }
            QLabel#sectionHint, QLabel#fieldLabel { color: #5f6870; }
            QToolButton#sectionToggle { border: none; font-size: 14px; font-weight: 700; text-align: left; }
            QComboBox, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox { min-height: 32px; border-radius: 7px; }
            QPushButton#primaryButton { background: #3e638f; color: white; font-weight: 700; border-radius: 8px; padding: 9px; }
            QPushButton#primaryButton:disabled { background: #9ca3af; }
            QPushButton#accentButton { color: #3e638f; border-color: #9eb0c3; font-weight: 700; }
            QPushButton#dangerButton { color: #b91c1c; }
            QLabel#statusLabel { color: #5f6870; padding-top: 5px; }
            """
        )

        self._refresh_button.clicked.connect(self.refresh_printers)
        self._new_paper_button.clicked.connect(self.create_custom_paper)
        self._edit_paper_button.clicked.connect(self.edit_current_paper)
        self._delete_paper_button.clicked.connect(self.delete_current_paper)
        self._preview_button.clicked.connect(self.prepare_preview)
        self._toggle_preview_button.clicked.connect(self.toggle_preview_panel)
        self._save_preset_button.clicked.connect(self.save_current_preset)
        self._print_button.clicked.connect(self.print_document)
        self._paper_combo.currentIndexChanged.connect(self._selection_changed)
        self._printer_combo.currentIndexChanged.connect(self._selection_changed)
        self._template_combo.currentIndexChanged.connect(self._template_changed)
        self._calibration_offset.valueChanged.connect(self._calibration_offset_changed)
        self._calibration_left_button.clicked.connect(
            lambda: self._calibration_offset.setValue(self._calibration_offset.value() - 1)
        )
        self._calibration_right_button.clicked.connect(
            lambda: self._calibration_offset.setValue(self._calibration_offset.value() + 1)
        )
        self._calibration_save_button.clicked.connect(self.save_calibration_offset)
        self._form.changed.connect(self._schedule_preview)
        for widget, signal_name in (
            (self._visual_style, "currentIndexChanged"),
            (self._dithering, "currentIndexChanged"),
            (self._brightness, "valueChanged"),
            (self._contrast, "valueChanged"),
            (self._threshold, "valueChanged"),
            (self._sharpen, "toggled"),
            (self._invert, "toggled"),
        ):
            getattr(widget, signal_name).connect(self._render_options_changed)
        self._zoom.currentTextChanged.connect(self._apply_zoom)
        self._splitter.splitterMoved.connect(self._splitter_moved)

        self._preset_panel.refresh_requested.connect(self.refresh_presets)
        self._preset_panel.print_requested.connect(self.print_preset)
        self._preset_panel.load_requested.connect(self.load_preset)
        self._preset_panel.delete_requested.connect(self.delete_preset)
        self._history_panel.refresh_requested.connect(self.refresh_history)
        self._history_panel.preview_requested.connect(self.preview_history_job)
        self._history_panel.reprint_requested.connect(self.reprint_job)
        self._history_panel.edit_requested.connect(self.edit_history_job)
        self._history_panel.cancel_requested.connect(self.cancel_history_job)
        self._history_panel.delete_requested.connect(self.delete_history_job)
        self._history_panel.delete_filtered_requested.connect(self.delete_filtered_history)
        self._history_panel.delete_all_requested.connect(self.delete_all_history)
        self._todoist_panel.connect_requested.connect(self.connect_todoist)
        self._todoist_panel.disconnect_requested.connect(self.disconnect_todoist)
        self._todoist_panel.sync_requested.connect(self.sync_todoist)
        self._todoist_panel.use_todo_requested.connect(self.use_todoist_as_todo)
        self._todoist_panel.use_shopping_requested.connect(self.use_todoist_as_shopping)
        self._settings_panel.theme_changed.connect(self.change_theme)
        self._settings_panel.language_changed.connect(self.change_language)
        self._settings_panel.preview_visibility_changed.connect(self._set_preview_panel_visible)
        self._settings_panel.reset_editor_layout_requested.connect(self.reset_editor_layout)
        self._designer_panel.template_saved.connect(self._custom_template_saved)
        self._designer_panel.template_deleted.connect(self._custom_template_deleted)
        self._designer_panel.open_requested.connect(self._custom_template_open_requested)
        self._designer_panel.design_changed.connect(self._designer_changed)
        self._designer_panel.preset_save_requested.connect(self.save_current_preset)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(220)
        self._preview_timer.timeout.connect(self.prepare_preview)

        self.reload_papers()
        self.reload_templates()
        self.refresh_presets()
        self.refresh_history()
        self._load_settings()
        profile = self._context.todoist_service.profile()
        self._todoist_panel.set_connected(bool(profile and profile.enabled))
        self.refresh_printers()
        localize_widget_tree(self)

    def current_printer(self) -> PrinterProfile | None:
        value = self._printer_combo.currentData()
        return value if isinstance(value, PrinterProfile) else None

    def current_paper(self) -> PaperProfile | None:
        paper = self._selected_paper()
        template = self.current_template()
        if paper is not None and template is not None and template.id == "system.calibration":
            return replace(
                paper,
                horizontal_content_offset_dots=self._calibration_offset.value(),
            )
        return paper

    def _selected_paper(self) -> PaperProfile | None:
        value = self._paper_combo.currentData()
        return value if isinstance(value, PaperProfile) else None

    def current_template(self) -> TemplateDefinition | None:
        value = self._template_combo.currentData()
        return value if isinstance(value, TemplateDefinition) else None

    def _designer_state(self) -> tuple[str, dict[str, object], dict[str, object], str, str | None] | None:
        return self._designer_panel.current_design()

    def _current_input_data(self) -> dict[str, object]:
        state = self._designer_state()
        if state is not None:
            return dict(state[1])
        return self._form.values()

    def _designer_changed(self) -> None:
        state = self._designer_state()
        if state is None:
            return
        template_id, data, render_options, source, source_reference = state
        template_index = next(
            (index for index in range(self._template_combo.count())
             if getattr(self._template_combo.itemData(index), "id", None) == template_id),
            -1,
        )
        if template_index >= 0:
            self._template_combo.blockSignals(True)
            self._template_combo.setCurrentIndex(template_index)
            self._template_combo.blockSignals(False)
        template = self.current_template()
        if template is not None:
            self._form.set_definition(template)
            self._form.set_values(data)
            self._calibration_panel.setVisible(template.id == "system.calibration")
            self._print_button.setText(tr("KALİBRASYON YAZDIR" if template.id == "system.calibration" else "YAZDIR"))
        self._editor_source = source
        self._editor_source_reference = source_reference
        self._apply_render_options(render_options)
        self._sync_calibration_offset()
        self._schedule_preview()

    def _open_designer(self) -> None:
        self._tabs.setCurrentIndex(self._designer_tab_index)

    def reload_papers(self, select_id: str | None = None) -> None:
        self._paper_combo.blockSignals(True)
        self._paper_combo.clear()
        selected = 0
        for index, paper in enumerate(self._context.paper_service.list_profiles()):
            self._paper_combo.addItem(f"{paper.name} — {paper.printable_width_dots} dot", paper)
            if paper.id == select_id:
                selected = index
        self._paper_combo.setCurrentIndex(selected)
        self._paper_combo.blockSignals(False)
        self._sync_calibration_offset()
        localize_widget_tree(self._paper_combo)

    def reload_templates(self) -> None:
        for template in self._context.custom_template_service.list_all():
            self._context.template_catalog.register_custom(
                custom_definition(template.id, template.name, template.category, list(template.blocks))
            )
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        self._template_combo.addItem(TEST_PAGE_TEMPLATE.name, TEST_PAGE_TEMPLATE)
        for template in self._context.template_catalog.list_all():
            self._template_combo.addItem(template.name, template)
        self._template_combo.blockSignals(False)
        self._designer_panel.refresh_templates()
        localize_widget_tree(self._template_combo)
        self._template_changed()
        if self._designer_panel.current_design() is None:
            template = self._template_combo.itemData(1) if self._template_combo.count() > 1 else self.current_template()
            if template is not None:
                self._designer_panel.set_design(template.id, {}, {})

    def _custom_template_saved(self, template_id: str) -> None:
        template = self._context.custom_template_service.get(template_id)
        if template is None:
            return
        self._context.template_catalog.register_custom(
            custom_definition(template.id, template.name, template.category, list(template.blocks))
        )
        self.reload_templates()

    def _custom_template_open_requested(self, template_id: str) -> None:
        state = self._designer_panel.current_design()
        if state is None or state[0] != template_id:
            return
        _, data, options, source, source_reference = state
        template = next((item for item in self._context.template_catalog.list_all() if item.id == template_id), None)
        if template is None:
            return
        self._load_editor_state(
            template_id,
            self._selected_paper().id if self._selected_paper() else "paper-56mm",
            data,
            options,
            source=source,
            source_reference=source_reference,
        )
        # This action is explicitly the hand-off from the Designer to the
        # print workflow.  _load_editor_state normally opens the Designer so
        # that imported/preset data can be edited there; after this button is
        # clicked the user must land on the Yazdır tab instead.
        self._tabs.setCurrentIndex(self._editor_tab_index)

    def _custom_template_deleted(self, template_id: str) -> None:
        self._context.template_catalog.remove_custom(template_id)
        self._designer_panel.refresh_templates()
        self.reload_templates()

    def refresh_printers(self) -> None:
        self._set_busy(True, "GC420t aranıyor…")
        self._run(self._context.printer_service.discover_gc420t, self._printers_loaded)

    def _printers_loaded(self, profiles: object) -> None:
        self._printer_combo.blockSignals(True)
        self._printer_combo.clear()
        for printer in profiles if isinstance(profiles, list) else []:
            self._printer_combo.addItem(f"{printer.spooler_name} — {printer.port_name}", printer)
        self._printer_combo.blockSignals(False)
        if self._printer_combo.count() == 0:
            self._set_busy(False, "GC420t bulunamadı")
            return
        self._set_busy(False, "GC420t hazır")
        self._schedule_preview()

    def _template_changed(self) -> None:
        template = self.current_template()
        if template:
            self._form.set_definition(template)
            is_calibration = template.id == "system.calibration"
            self._calibration_panel.setVisible(is_calibration)
            self._print_button.setText(tr("KALİBRASYON YAZDIR" if is_calibration else "YAZDIR"))
            self._sync_calibration_offset()
        self._schedule_preview()

    def _selection_changed(self) -> None:
        self._latest_job = None
        self._sync_calibration_offset()
        self._schedule_preview()

    def _sync_calibration_offset(self) -> None:
        paper = self._selected_paper()
        if paper is None:
            return
        self._calibration_offset.blockSignals(True)
        self._calibration_offset.setRange(
            -CALIBRATION_OFFSET_LIMIT_DOTS,
            CALIBRATION_OFFSET_LIMIT_DOTS,
        )
        self._calibration_offset.setValue(paper.horizontal_content_offset_dots)
        self._calibration_offset.blockSignals(False)

    def _calibration_offset_changed(self) -> None:
        self._latest_job = None
        prefix = "Calibration trial" if tr("Hazır") == "Ready" else "Kalibrasyon denemesi"
        self._status.setText(f"{prefix}: {self._calibration_offset.value():+d} dot")
        self._schedule_preview()

    def save_calibration_offset(self) -> None:
        printer = self.current_printer()
        paper = self._selected_paper()
        if printer is None or paper is None:
            QMessageBox.information(self, tr("Eksik seçim"), tr("GC420t ve kağıt profili seçilmelidir."))
            return
        calibrated = replace(
            paper,
            horizontal_content_offset_dots=self._calibration_offset.value(),
        )
        try:
            self._context.paper_service.save_profile(calibrated, printer)
        except Exception as exc:
            self._show_error(exc)
            return
        self.reload_papers(calibrated.id)
        if tr("Hazır") == "Ready":
            self._status.setText(
                f"Saved horizontal offset for {calibrated.name}: {calibrated.horizontal_content_offset_dots:+d} dots"
            )
        else:
            self._status.setText(
                f"{calibrated.name} yatay ofseti kaydedildi: {calibrated.horizontal_content_offset_dots:+d} dot"
            )
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        if self.current_printer() and self.current_paper() and self.current_template():
            self._preview_timer.start()

    def _render_options_changed(self) -> None:
        self._designer_panel.set_render_options(asdict(self._render_options()))
        self._schedule_preview()

    def create_custom_paper(self) -> None:
        self._edit_paper(None)

    def edit_current_paper(self) -> None:
        self._edit_paper(self.current_paper())

    def _edit_paper(self, profile: PaperProfile | None) -> None:
        printer = self.current_printer()
        if printer is None:
            QMessageBox.information(self, tr("GC420t gerekli"), tr("Önce Zebra GC420t kuyruğu bulunmalıdır."))
            return
        dialog = CustomPaperDialog(self, profile)
        if dialog.exec() and dialog.profile:
            try:
                self._context.paper_service.save_profile(dialog.profile, printer)
            except Exception as exc:
                self._show_error(exc)
                return
            self.reload_papers(dialog.profile.id)
            self._schedule_preview()

    def delete_current_paper(self) -> None:
        paper = self.current_paper()
        if paper is None:
            return
        question = f"Delete {paper.name}?" if tr("Hazır") == "Ready" else f"{paper.name} silinsin mi?"
        answer = QMessageBox.question(self, tr("Kağıt profilini sil"), question)
        if answer != QMessageBox.Yes:
            return
        try:
            self._context.paper_service.delete_profile(paper.id)
        except Exception as exc:
            self._show_error(exc)
            return
        self.reload_papers()
        self._schedule_preview()

    def _render_options(self) -> RenderOptions:
        return RenderOptions(
            brightness=self._brightness.value(),
            contrast=self._contrast.value(),
            threshold=self._threshold.value(),
            dithering=str(self._dithering.currentData()),
            sharpen=self._sharpen.isChecked(),
            invert=self._invert.isChecked(),
            visual_style=str(self._visual_style.currentData()),
        )

    def _apply_render_options(self, values: object) -> None:
        if not isinstance(values, dict):
            return
        dithering = str(values.get("dithering", "threshold"))
        index = self._dithering.findData(dithering)
        if index >= 0:
            self._dithering.setCurrentIndex(index)
        visual_style = str(values.get("visual_style", "plain"))
        style_index = self._visual_style.findData(visual_style)
        self._visual_style.setCurrentIndex(style_index if style_index >= 0 else 0)
        self._brightness.setValue(float(values.get("brightness", 1.0)))
        self._contrast.setValue(float(values.get("contrast", 1.0)))
        self._threshold.setValue(int(values.get("threshold", 160)))
        self._sharpen.setChecked(bool(values.get("sharpen", False)))
        self._invert.setChecked(bool(values.get("invert", False)))

    def save_current_preset(self) -> None:
        printer, paper, template = self.current_printer(), self.current_paper(), self.current_template()
        if printer is None or paper is None or template is None:
            return
        name, accepted = QInputDialog.getText(self, tr("Preset kaydet"), tr("Preset adı"))
        if not accepted or not name.strip():
            return
        try:
            self._context.preset_service.save_new(
                name,
                template.id,
                paper.id,
                self._current_input_data(),
                asdict(self._render_options()),
                printer_profile_id=printer.id,
                integration_profile_id=self._editor_integration_profile_id,
                filter_spec=self._editor_filter_spec,
                pinned=False,
            )
        except Exception as exc:
            self._show_error(exc)
            return
        self.refresh_presets()
        prefix = "Preset saved" if tr("Hazır") == "Ready" else "Preset kaydedildi"
        self._status.setText(f"{prefix}: {name.strip()}")

    def refresh_presets(self) -> None:
        self._preset_panel.set_presets(self._context.preset_service.list_all())

    def _preset(self, preset_id: str) -> Preset | None:
        return next(
            (preset for preset in self._context.preset_service.list_all() if preset.id == preset_id),
            None,
        )

    def load_preset(self, preset_id: str) -> None:
        preset = self._preset(preset_id)
        if preset is None:
            return
        self._load_editor_state(
            preset.template_id,
            preset.paper_profile_id,
            preset.input_data,
            preset.render_options,
            integration_profile_id=preset.integration_profile_id,
            filter_spec=preset.filter_spec,
        )

    def print_preset(self, preset_id: str) -> None:
        preset = self._preset(preset_id)
        if preset is not None and preset.integration_profile_id == "todoist-personal":
            mode = str(preset.filter_spec.get("mode", "today"))
            project_id = preset.filter_spec.get("project_id")
            filter_value = str(preset.filter_spec.get("filter_value", ""))
            self._set_busy(True, tr("Preset için Todoist senkronize ediliyor…"))
            self._run(
                lambda: self._context.todoist_service.sync(
                    mode,
                    project_id=str(project_id) if project_id else None,
                    filter_value=filter_value,
                ),
                lambda value: self._todoist_preset_synced(preset, value),
                self._show_error,
            )
            return
        if preset is not None:
            self._submit_preset(preset, preset.input_data)

    def _todoist_preset_synced(self, preset: Preset, value: object) -> None:
        if not isinstance(value, TodoistSyncResult):
            self._set_busy(False, tr("Todoist sonucu alınamadı"))
            return
        self._todoist_panel.set_result(value)
        if value.stale:
            self._set_busy(False, tr("Preset için yalnızca eski Todoist cache’i bulundu"))
            answer = QMessageBox.question(
                self,
                tr("Eski Todoist cache’i"),
                (
                    f"Last sync: {value.synced_at:%d.%m.%Y %H:%M}. Print this stale data?"
                    if tr("Hazır") == "Ready"
                    else f"Son senkronizasyon {value.synced_at:%d.%m.%Y %H:%M}. Bu eski veri yazdırılsın mı?"
                ),
            )
            if answer != QMessageBox.Yes:
                return
        if preset.template_id == "shopping.basic":
            project_name = next((task.project for task in value.tasks if task.project), preset.name)
            data = self._context.todoist_service.to_shopping_input(value, str(project_name))
        else:
            data = self._context.todoist_service.to_todo_input(value, preset.name)
        self._submit_preset(preset, data)

    def _submit_preset(self, preset: Preset, input_data: object) -> None:
        printer = self.current_printer()
        paper = next(
            (item for item in self._context.paper_service.list_profiles() if item.id == preset.paper_profile_id),
            None,
        )
        if printer is None or paper is None or not isinstance(input_data, dict):
            QMessageBox.information(self, tr("Preset yazdırılamadı"), tr("Yazıcı veya kağıt profili bulunamadı."))
            return
        option_names = RenderOptions.__dataclass_fields__.keys()
        options = RenderOptions(
            **{key: value for key, value in preset.render_options.items() if key in option_names}
        )

        def prepare_and_submit() -> PrintJob:
            job = self._context.print_service.prepare(
                printer,
                paper,
                preset.template_id,
                data=input_data,
                options=options,
                source="preset",
                source_reference=preset.id,
            )
            return self._context.print_service.submit(job.id)

        self._set_busy(True, tr("Preset kuyruğa gönderiliyor…"))
        self._run(prepare_and_submit, self._print_submitted, self._show_error)

    def delete_preset(self, preset_id: str) -> None:
        if QMessageBox.question(self, tr("Preset sil"), tr("Seçili preset silinsin mi?")) != QMessageBox.Yes:
            return
        try:
            self._context.preset_service.delete(preset_id)
        except Exception as exc:
            self._show_error(exc)
            return
        self.refresh_presets()

    def refresh_history(self) -> None:
        filters = self._history_filters()
        if filters is None:
            return
        start_at, end_at, statuses = filters
        self._history_panel.set_jobs(
            self._context.print_service.list_history(
                start_at=start_at,
                end_at=end_at,
                statuses=statuses,
            )
        )

    def _history_filters(self) -> tuple[datetime | None, datetime | None, tuple[PrintJobStatus, ...] | None] | None:
        start_text, end_text, status_value = self._history_panel.filter_values()
        try:
            start_at = datetime.combine(datetime.strptime(start_text, "%Y-%m-%d").date(), time.min).astimezone() if start_text else None
            end_at = (
                datetime.combine(datetime.strptime(end_text, "%Y-%m-%d").date(), time.max).astimezone()
                if end_text
                else None
            )
        except ValueError:
            QMessageBox.warning(self, tr("Geçersiz tarih"), tr("Tarihleri YYYY-AA-GG biçiminde girin."))
            return None
        if start_at and end_at and start_at > end_at:
            QMessageBox.warning(self, tr("Geçersiz aralık"), tr("Başlangıç tarihi bitiş tarihinden sonra olamaz."))
            return None
        statuses = (PrintJobStatus(status_value),) if status_value else None
        return start_at, end_at, statuses

    def preview_history_job(self, job_id: str) -> None:
        job = self._context.print_service.get_job(job_id)
        if job is None or job.preview_artifact_path is None or not job.preview_artifact_path.exists():
            QMessageBox.information(self, tr("Önizleme yok"), tr("Bu baskı işinin önizleme artefaktı bulunamadı."))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{tr('Baskı önizlemesi')} — {job.template_id}")
        dialog.resize(620, 720)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(QPixmap(str(job.preview_artifact_path)))
        scroll = QScrollArea()
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(label)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(tr("Bu görüntü encoder'a verilen 1-bit raster artefaktıdır.")))
        layout.addWidget(scroll, 1)
        dialog.exec()

    def reprint_job(self, job_id: str) -> None:
        self._set_busy(True, tr("Geçmiş işi yeniden hazırlanıyor…"))
        self._run(
            lambda: self._context.print_service.reprint(job_id),
            self._print_submitted,
            self._show_error,
        )

    def edit_history_job(self, job_id: str) -> None:
        job = self._context.print_service.get_job(job_id)
        if job is None:
            return
        self._load_editor_state(
            job.template_id,
            job.paper_profile_id,
            job.input_data,
            job.render_options,
        )

    def cancel_history_job(self, job_id: str) -> None:
        def cancelled(value: object) -> None:
            self._set_busy(False, tr("Kuyruk işi iptal edildi" if value else "İş artık kuyrukta değil"))
            self.refresh_history()

        self._set_busy(True, tr("Kuyruk işi iptal ediliyor…"))
        self._run(lambda: self._context.print_service.cancel(job_id), cancelled, self._show_error)

    def delete_history_job(self, job_id: str) -> None:
        if QMessageBox.question(self, tr("Geçmiş kaydını sil"), tr("Kayıt ve ilişkili PNG/bitmap/ZPL artefaktları silinsin mi?")) != QMessageBox.Yes:
            return
        result = self._context.print_service.delete_history_filtered(job_ids=[job_id])
        if result.skipped_active_jobs:
            QMessageBox.information(self, tr("İş aktif"), tr("Gönderim devam eden iş silinmedi."))
        self.refresh_history()

    def delete_filtered_history(self) -> None:
        filters = self._history_filters()
        if filters is None:
            return
        start_at, end_at, statuses = filters
        jobs = self._context.print_service.list_history(
            limit=100000, start_at=start_at, end_at=end_at, statuses=statuses
        )
        if not jobs:
            QMessageBox.information(self, tr("Geçmiş boş"), tr("Bu filtrelerle silinecek kayıt yok."))
            return
        if QMessageBox.question(
            self,
            tr("Filtreli geçmişi sil"),
            (
                f"Permanently delete {len(jobs)} record(s) and related artifacts?"
                if tr("Hazır") == "Ready"
                else f"{len(jobs)} kayıt ve ilişkili artefaktlar kalıcı olarak silinsin mi?"
            ),
        ) != QMessageBox.Yes:
            return
        result = self._context.print_service.delete_history_filtered(
            start_at=start_at, end_at=end_at, statuses=statuses
        )
        self.refresh_history()
        if tr("Hazır") == "Ready":
            self._status.setText(f"Deleted {result.deleted_jobs} history record(s) and {result.deleted_artifacts} artifact(s)")
        else:
            self._status.setText(f"{result.deleted_jobs} geçmiş kaydı silindi; {result.deleted_artifacts} artefakt temizlendi")
        if result.skipped_active_jobs:
            QMessageBox.information(self, tr("Aktif işler korunuyor"), f"{result.skipped_active_jobs} {tr('aktif iş silinmedi.')}")

    def delete_all_history(self) -> None:
        jobs = self._context.print_service.list_history(limit=100000)
        if not jobs:
            QMessageBox.information(self, tr("Geçmiş boş"), tr("Silinecek geçmiş kaydı yok."))
            return
        if QMessageBox.question(
            self,
            tr("Tüm geçmişi sil"),
            (
                f"Permanently delete {len(jobs)} record(s) and related PNG/bitmap/ZPL artifacts?"
                if tr("Hazır") == "Ready"
                else f"{len(jobs)} kayıt ve ilişkili PNG/bitmap/ZPL artefaktları kalıcı olarak silinsin mi?"
            ),
        ) != QMessageBox.Yes:
            return
        result = self._context.print_service.delete_history_filtered()
        self.refresh_history()
        if tr("Hazır") == "Ready":
            self._status.setText(f"Deleted {result.deleted_jobs} history record(s) and {result.deleted_artifacts} artifact(s)")
        else:
            self._status.setText(f"{result.deleted_jobs} geçmiş kaydı silindi; {result.deleted_artifacts} artefakt temizlendi")
        if result.skipped_active_jobs:
            QMessageBox.information(self, tr("Aktif işler korunuyor"), f"{result.skipped_active_jobs} {tr('aktif iş silinmedi.')}")

    def _load_editor_state(
        self,
        template_id: str,
        paper_profile_id: str,
        input_data: object,
        render_options: object,
        *,
        integration_profile_id: str | None = None,
        filter_spec: object = None,
        source: str = "manual-template",
        source_reference: str | None = None,
    ) -> None:
        paper_index = next(
            (index for index in range(self._paper_combo.count()) if getattr(self._paper_combo.itemData(index), "id", None) == paper_profile_id),
            -1,
        )
        template_index = next(
            (index for index in range(self._template_combo.count()) if getattr(self._template_combo.itemData(index), "id", None) == template_id),
            -1,
        )
        if paper_index >= 0:
            self._paper_combo.setCurrentIndex(paper_index)
        if template_index >= 0:
            self._template_combo.setCurrentIndex(template_index)
        if isinstance(input_data, dict):
            self._form.set_values(input_data)
        self._apply_render_options(render_options)
        self._editor_integration_profile_id = integration_profile_id
        self._editor_filter_spec = dict(filter_spec) if isinstance(filter_spec, dict) else {}
        self._editor_source = source
        self._editor_source_reference = source_reference
        self._designer_panel.set_design(
            template_id,
            input_data if isinstance(input_data, dict) else {},
            render_options if isinstance(render_options, dict) else {},
            source=source,
            source_reference=source_reference,
        )
        self._tabs.setCurrentIndex(self._designer_tab_index)
        self._schedule_preview()

    def connect_todoist(self, token: str) -> None:
        self._set_busy(True, "Todoist tokenı doğrulanıyor…")

        def connected(value: object) -> None:
            self._set_busy(False, "Todoist bağlantısı doğrulandı")
            self._todoist_panel.set_connected(True, tr("Todoist bağlı — API v1"))
            self._run(
                self._context.todoist_service.list_projects,
                lambda projects: self._todoist_panel.set_projects(projects if isinstance(projects, dict) else {}),
                self._show_todoist_error,
            )

        self._run(lambda: self._context.todoist_service.connect(token), connected, self._show_todoist_error)

    def disconnect_todoist(self) -> None:
        try:
            self._context.todoist_service.disconnect()
        except Exception as exc:
            self._show_error(exc)
            return
        self._todoist_panel.set_connected(False)

    def sync_todoist(self, mode: str, project_id: object, filter_value: str) -> None:
        self._set_busy(True, tr("Todoist senkronize ediliyor…"))

        def synced(value: object) -> None:
            if isinstance(value, TodoistSyncResult):
                self._todoist_panel.set_result(value)
                self._editor_filter_spec = {
                    "mode": mode,
                    "project_id": str(project_id) if project_id else None,
                    "filter_value": filter_value,
                }
                if tr("Hazır") == "Ready":
                    state = "stale cache" if value.stale else "current"
                    self._set_busy(False, f"Todoist: {len(value.tasks)} tasks — {state}")
                else:
                    state = "eski cache" if value.stale else "güncel"
                    self._set_busy(False, f"Todoist: {len(value.tasks)} görev — {state}")

        self._run(
            lambda: self._context.todoist_service.sync(
                mode,
                project_id=str(project_id) if project_id else None,
                filter_value=filter_value,
            ),
            synced,
            self._show_todoist_error,
        )

    def _show_todoist_error(self, error: object) -> None:
        if isinstance(error, TodoistAuthError):
            state = "Kimlik doğrulama süresi doldu veya token geçersiz"
        elif isinstance(error, TodoistRateLimitError):
            state = "İstek sınırına ulaşıldı"
        elif isinstance(error, TodoistNetworkError):
            state = "Çevrimdışı — uygun cache varsa ayrıca gösterilir"
        else:
            state = "Todoist API hatası"
        self._todoist_panel.status.setText(tr(state))
        self._show_error(error)

    def use_todoist_as_todo(self, value: object) -> None:
        if not isinstance(value, TodoistSyncResult):
            return
        title = {"online": "Bugünün İşleri", "cache": "Bugünün İşleri (Cache)"}.get(value.source, "Todoist")
        data = self._context.todoist_service.to_todo_input(value, title)
        paper = self.current_paper()
        self._load_editor_state(
            "todo.basic",
            paper.id if paper else "paper-56mm",
            data,
            {},
            integration_profile_id="todoist-personal",
            filter_spec=self._editor_filter_spec,
        )

    def use_todoist_as_shopping(self, value: object) -> None:
        if not isinstance(value, TodoistSyncResult):
            return
        project_name = next((task.project for task in value.tasks if task.project), "Todoist Alışveriş")
        data = self._context.todoist_service.to_shopping_input(value, str(project_name))
        paper = self.current_paper()
        self._load_editor_state(
            "shopping.basic",
            paper.id if paper else "paper-56mm",
            data,
            {},
            integration_profile_id="todoist-personal",
            filter_spec=self._editor_filter_spec,
        )

    def _load_settings(self) -> None:
        theme = self._context.settings_service.theme()
        language = self._context.settings_service.language()
        preview_visible = self._context.settings_service.preview_visible()
        self._settings_panel.set_values(theme, preview_visible, language)
        self._apply_theme(theme)
        sizes = list(self._context.settings_service.editor_splitter_sizes())
        self._last_visible_splitter_sizes = sizes
        self._splitter.setSizes(sizes)
        self._set_preview_panel_visible(preview_visible, persist=False)

    def reset_editor_layout(self) -> None:
        sizes = [580, 420]
        self._last_visible_splitter_sizes = sizes
        self._context.settings_service.set_editor_splitter_sizes(*sizes)
        self._splitter.setSizes(sizes)
        self._set_preview_panel_visible(True)
        self._status.setText(tr("Editör yerleşimi varsayılana döndürüldü"))

    def toggle_preview_panel(self) -> None:
        self._set_preview_panel_visible(self._preview_card.isHidden())

    def _set_preview_panel_visible(self, visible: bool, *, persist: bool = True) -> None:
        if visible:
            self._preview_card.show()
            self._splitter.setSizes(self._last_visible_splitter_sizes)
            self._toggle_preview_button.setText(tr("Önizlemeyi gizle"))
            QTimer.singleShot(0, self._apply_zoom)
        else:
            sizes = self._splitter.sizes()
            if len(sizes) == 2 and sizes[0] >= 460 and sizes[1] >= 300:
                self._last_visible_splitter_sizes = sizes
            self._preview_card.hide()
            self._toggle_preview_button.setText(tr("Önizlemeyi göster"))
        if hasattr(self, "_settings_panel"):
            self._settings_panel.preview_visible.blockSignals(True)
            self._settings_panel.preview_visible.setChecked(visible)
            self._settings_panel.preview_visible.blockSignals(False)
        if persist:
            self._context.settings_service.set_preview_visible(visible)

    def _splitter_moved(self, *_args: object) -> None:
        if self._preview_card.isHidden():
            return
        sizes = self._splitter.sizes()
        if len(sizes) == 2 and sizes[0] >= 460 and sizes[1] >= 300:
            self._last_visible_splitter_sizes = sizes
            self._context.settings_service.set_editor_splitter_sizes(*sizes)

    def change_theme(self, theme: str) -> None:
        self._context.settings_service.set_theme(theme)
        self._apply_theme(theme)

    def change_language(self, language: str) -> None:
        self._context.settings_service.set_language(language)
        set_language(language)
        localize_widget_tree(self)
        self._status.setText(tr("Uygulama dili değiştirildi."))

    def _apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        system_dark = self._system_palette.color(QPalette.Window).lightness() < 128
        dark = theme == "dark" or (theme == "system" and system_dark)
        background = "#111827" if dark else "#f0efeb"
        card = "#1f2937" if dark else "#fbfaf7"
        text = "#f9fafb" if dark else "#27313a"
        border = "#4b5563" if dark else "#c7c5be"
        field = "#374151" if dark else "#f6f5f1"
        muted = "#cbd5e1" if dark else "#5f6870"
        accent = "#60a5fa" if dark else "#3e638f"
        accent_hover = "#3b82f6" if dark else "#324f73"
        danger = "#fca5a5" if dark else "#b91c1c"
        if app is not None:
            if theme == "system":
                app.setPalette(QPalette(self._system_palette))
            else:
                palette = QPalette(self._system_palette)
                palette_colors = {
                    QPalette.Window: background,
                    QPalette.WindowText: text,
                    QPalette.Base: card,
                    QPalette.AlternateBase: field,
                    QPalette.Text: text,
                    QPalette.Button: field,
                    QPalette.ButtonText: text,
                    QPalette.Highlight: accent,
                    QPalette.HighlightedText: "#ffffff",
                    QPalette.Link: accent,
                    QPalette.PlaceholderText: muted,
                    QPalette.ToolTipBase: card,
                    QPalette.ToolTipText: text,
                    QPalette.Mid: border,
                    QPalette.Dark: border,
                    QPalette.BrightText: "#ffffff",
                }
                for role, color in palette_colors.items():
                    palette.setColor(role, QColor(color))
                app.setPalette(palette)
        self.setStyleSheet(
            f"""
            QMainWindow, QTabWidget::pane, QWidget#editorBody, QWidget#editorPanel {{ background: {background}; color: {text}; }}
            QWidget#presetPanel, QWidget#designerPanel, QWidget#historyPanel, QWidget#todoistPanel {{ background: {background}; color: {text}; }}
            QWidget {{ color: {text}; }}
            QTabBar::tab {{
                background: {card}; color: {muted}; border: 1px solid {border};
                padding: 9px 16px; min-width: 74px;
            }}
            QTabBar::tab:selected {{
                background: {background}; color: {accent}; font-weight: 700;
                border-bottom: 2px solid {accent};
            }}
            QScrollArea#controlsScroll {{ background: {background}; border: none; }}
            QWidget#schemaForm {{ background: {card}; border: none; }}
            QScrollArea#previewScroll {{ background: {background}; border: 1px solid {border}; border-radius: 8px; }}
            QFrame#controlCard {{ background: transparent; border: none; }}
            QFrame#sectionCard, QFrame#previewCard, QFrame#actionBar {{ background: {card}; border: 1px solid {border}; border-radius: 12px; }}
            QFrame#settingsCard {{ background: {card}; border: 1px solid {border}; border-radius: 12px; }}
            QFrame#calibrationCard {{ background: {field}; border: 1px solid {border}; border-radius: 8px; }}
            QLabel#pageTitle {{ color: {text}; font-size: 21px; font-weight: 700; }}
            QLabel#sectionTitle {{ color: {text}; font-size: 14px; font-weight: 700; }}
            QLabel#sectionHint, QLabel#fieldLabel {{ color: {muted}; }}
            QToolButton#sectionToggle {{
                min-height: 28px; background: transparent; color: {text}; border: none;
                font-size: 14px; font-weight: 700; text-align: left;
            }}
            QSplitter#editorSplitter::handle {{ background: {border}; margin: 0 3px; border-radius: 2px; }}
            QComboBox, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTableWidget {{
                min-height: 32px; background: {field}; color: {text}; border: 1px solid {border};
                border-radius: 7px; padding: 3px 7px;
            }}
            QComboBox QAbstractItemView, QAbstractItemView, QListWidget, QMenu, QDialog, QMessageBox, QInputDialog {{
                background: {card}; color: {text};
            }}
            QComboBox QAbstractItemView {{
                selection-background-color: {accent}; selection-color: white;
                border: 1px solid {border}; padding: 2px;
            }}
            QMenu {{ border: 1px solid {border}; padding: 4px; }}
            QMenu::item {{ padding: 6px 22px 6px 8px; }}
            QMenu::item:selected {{ background: {accent}; color: white; }}
            QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; padding: 4px; }}
            QScrollBar:vertical, QScrollBar:horizontal {{ background: {field}; border: none; }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; }}
            QTableWidget {{ gridline-color: {border}; alternate-background-color: {card}; }}
            QTableWidget::item:selected {{ background: {accent}; color: white; }}
            QHeaderView::section {{ background: {field}; color: {text}; border: 1px solid {border}; padding: 6px; font-weight: 700; }}
            QCheckBox {{ color: {text}; spacing: 7px; }}
            QLineEdit:read-only {{ background: {card}; color: {muted}; }}
            QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton:hover {{ border-color: {accent}; }}
            QPushButton#primaryButton {{ background: {accent}; color: white; font-weight: 700; border: none; border-radius: 8px; padding: 9px; }}
            QPushButton#primaryButton:hover {{ background: {accent_hover}; }}
            QPushButton#primaryButton:disabled {{ background: #9ca3af; }}
            QPushButton:disabled {{ color: {muted}; background: {background}; border-color: {border}; }}
            QPushButton#accentButton {{ color: {accent}; border-color: {accent}; font-weight: 700; }}
            QPushButton#dangerButton {{ color: {danger}; }}
            QLabel#statusLabel {{ color: {muted}; padding-top: 5px; }}
            QLabel#previewCanvas {{ background: {"#d9dce1" if dark else "#e3e1dc"}; color: {"#59616d" if dark else "#697077"}; }}
            """
        )

    def prepare_preview(self) -> None:
        printer, paper, template = self.current_printer(), self.current_paper(), self.current_template()
        if printer is None or paper is None or template is None:
            return
        self._preview_request += 1
        request_id = self._preview_request
        data = self._current_input_data()
        options = self._render_options()
        self._set_busy(True, "Önizleme hazırlanıyor…")

        def ready(value: object) -> None:
            if request_id == self._preview_request:
                self._preview_ready(value)

        def failed(error: object) -> None:
            if request_id == self._preview_request:
                self._show_preview_error(error)

        self._run(
            lambda: self._context.print_service.prepare(
                printer,
                paper,
                template.id,
                data=data,
                options=options,
                source=self._editor_source,
                source_reference=self._editor_source_reference,
                persist_paper_profile=template.id != "system.calibration",
            ),
            ready,
            failed,
        )

    def _preview_ready(self, value: object) -> None:
        if not isinstance(value, PrintJob) or value.preview_artifact_path is None:
            self._set_busy(False, "Önizleme oluşturulamadı")
            return
        self._latest_job = value
        self._show_preview(value.preview_artifact_path)
        ready = "Ready" if tr("Hazır") == "Ready" else "Hazır"
        self._set_busy(False, f"{ready} — {value.canvas_width} × {value.canvas_height} dot")

    def _show_preview(self, path: Path) -> None:
        self._preview_pixmap = QPixmap(str(path))
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        if self._preview_pixmap is None:
            return
        mode = str(self._zoom.currentData())
        size = self._preview_scroll.viewport().size()
        available_width = max(1, size.width() - (self._preview_padding * 2) - 24)
        available_height = max(1, size.height() - (self._preview_padding * 2) - 24)
        if mode == "fit-width":
            target = self._preview_pixmap.scaledToWidth(
                available_width,
                Qt.SmoothTransformation,
            )
        elif mode == "fit-window":
            target = self._preview_pixmap.scaled(
                available_width,
                available_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        else:
            factor = 2 if mode == "200" else 1
            target = self._preview_pixmap.scaled(
                self._preview_pixmap.width() * factor,
                self._preview_pixmap.height() * factor,
                Qt.KeepAspectRatio,
                Qt.FastTransformation,
            )
        self._preview.setPixmap(target)
        self._preview.resize(
            target.width() + self._preview_padding * 2,
            target.height() + self._preview_padding * 2,
        )

    def print_document(self) -> None:
        printer, paper, template = self.current_printer(), self.current_paper(), self.current_template()
        if printer is None or paper is None or template is None:
            QMessageBox.information(self, tr("Eksik seçim"), tr("GC420t, kağıt ve şablon seçilmelidir."))
            return
        data = self._current_input_data()
        options = self._render_options()

        def prepare_and_submit() -> PrintJob:
            job = self._context.print_service.prepare(
                printer,
                paper,
                template.id,
                data=data,
                options=options,
                source=self._editor_source,
                source_reference=self._editor_source_reference,
                persist_paper_profile=template.id != "system.calibration",
            )
            return self._context.print_service.submit(job.id)

        self._set_busy(True, tr("Belge kuyruğa gönderiliyor…"))
        self._run(prepare_and_submit, self._print_submitted, self._show_error)

    def _print_submitted(self, value: object) -> None:
        if isinstance(value, PrintJob):
            if tr("Hazır") == "Ready":
                self._set_busy(False, f"Submitted to the printer queue — Job #{value.transport_job_id}")
            else:
                self._set_busy(False, f"Yazıcı kuyruğuna gönderildi — İş #{value.transport_job_id}")
            self.refresh_history()

    def _set_busy(self, busy: bool, message: str) -> None:
        self._status.setText(tr(message))
        disabled = busy or self.current_printer() is None
        self._print_button.setDisabled(disabled)
        self._preview_button.setDisabled(disabled)
        self._save_preset_button.setDisabled(disabled)
        self._refresh_button.setDisabled(busy)
        self._calibration_save_button.setDisabled(disabled)
        self._calibration_left_button.setDisabled(busy)
        self._calibration_right_button.setDisabled(busy)

    def _run(
        self,
        function: Callable[[], Any],
        callback: Callable[[object], None],
        error_callback: Callable[[object], None] | None = None,
    ) -> None:
        worker = Worker(function)
        self._workers.append(worker)
        worker.signals.result.connect(callback)
        worker.signals.error.connect(error_callback or self._show_error)
        worker.signals.finished.connect(lambda: self._release_worker(worker))
        self._pool.start(worker)

    def _release_worker(self, worker: Worker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def _show_preview_error(self, error: object) -> None:
        message = str(error) if isinstance(error, ThermalAppError) else "Önizleme oluşturulamadı."
        self._set_busy(False, message)

    def _show_error(self, error: object) -> None:
        message = (
            str(error)
            if isinstance(error, (ThermalAppError, ValueError, KeyError))
            else "Beklenmeyen bir hata oluştu."
        )
        LOGGER.error(
            "operation_failed error_type=%s safe_message=%s",
            type(error).__name__,
            message,
        )
        self._set_busy(False, message)
        QMessageBox.warning(self, tr("İşlem tamamlanamadı"), message)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if str(self._zoom.currentData()).startswith("fit-"):
            QTimer.singleShot(0, self._apply_zoom)

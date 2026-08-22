from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from thermal_app.ui.localization import tr


class SettingsPanel(QWidget):
    theme_changed = Signal(str)
    language_changed = Signal(str)
    preview_visibility_changed = Signal(bool)
    reset_editor_layout_requested = Signal()

    def __init__(
        self,
        data_path: str,
        artifacts_path: str | None = None,
        app_version: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._data_path = Path(data_path)
        self._artifacts_path = Path(artifacts_path) if artifacts_path else self._data_path / "artifacts"

        title = QLabel("Ayarlar")
        title.setObjectName("pageTitle")
        subtitle = QLabel("ZebraWriter görünümünü, editör davranışını ve yerel verileri yönetin.")
        subtitle.setObjectName("sectionHint")
        subtitle.setWordWrap(True)

        appearance = self._card("Görünüm ve editör")
        appearance_layout = appearance.layout()
        theme_row = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItem("Sistem", "system")
        self.theme.addItem("Açık", "light")
        self.theme.addItem("Koyu", "dark")
        self.theme.currentIndexChanged.connect(
            lambda: self.theme_changed.emit(str(self.theme.currentData()))
        )
        theme_row.addRow("Tema", self.theme)
        self.language = QComboBox()
        self.language.addItem("Türkçe", "tr")
        self.language.addItem("English", "en")
        self.language.currentIndexChanged.connect(
            lambda: self.language_changed.emit(str(self.language.currentData()))
        )
        theme_row.addRow("Dil", self.language)
        appearance_layout.addLayout(theme_row)

        self.preview_visible = QCheckBox("Yazdırma ekranında önizlemeyi göster")
        self.preview_visible.setChecked(True)
        self.preview_visible.toggled.connect(self.preview_visibility_changed)
        appearance_layout.addWidget(self.preview_visible)
        reset_layout = QPushButton("Editör yerleşimini varsayılana döndür")
        reset_layout.setObjectName("secondaryButton")
        reset_layout.clicked.connect(self.reset_editor_layout_requested)
        appearance_layout.addWidget(reset_layout)

        storage = self._card("Veri ve artefaktlar")
        storage_layout = storage.layout()
        storage_hint = QLabel("Presetler, özel şablonlar, geçmiş ve ayarlar yalnızca bu bilgisayarda tutulur.")
        storage_hint.setObjectName("sectionHint")
        storage_hint.setWordWrap(True)
        storage_layout.addWidget(storage_hint)
        storage_form = QFormLayout()
        storage_form.addRow("Uygulama verileri", self._path_field(self._data_path))
        storage_form.addRow("Baskı artefaktları", self._path_field(self._artifacts_path))
        storage_layout.addLayout(storage_form)
        path_actions = QHBoxLayout()
        open_data = QPushButton("Veri klasörünü aç")
        open_artifacts = QPushButton("Artefakt klasörünü aç")
        open_data.clicked.connect(lambda: self._open_path(self._data_path))
        open_artifacts.clicked.connect(lambda: self._open_path(self._artifacts_path))
        path_actions.addWidget(open_data)
        path_actions.addWidget(open_artifacts)
        storage_layout.addLayout(path_actions)

        printing = self._card("Yazdırma ve güvenlik")
        printing_layout = printing.layout()
        for text in (
            "• Windows yazıcı kuyruğuna teslim edilen iş, fiziksel baskı garantisi anlamına gelmez.",
            "• PNG, bitmap ve ZPL artefaktları geçmiş kaydıyla birlikte güvenli yerel klasörde tutulur.",
            "• Todoist tokenı veritabanına veya loglara yazılmaz; Windows kimlik bilgileri kasası kullanılır.",
        ):
            label = QLabel(text)
            label.setObjectName("sectionHint")
            label.setWordWrap(True)
            printing_layout.addWidget(label)

        about = self._card("Uygulama")
        about_layout = about.layout()
        version_label = QLabel(f"{tr('Sürüm')}: {app_version or tr('geliştirme')}")
        version_label.setObjectName("sectionHint")
        about_layout.addWidget(version_label)
        about_layout.addWidget(QLabel("Referans yazıcı: Zebra GC420t · RAW/ZPL · 203 DPI"))
        about_layout.addWidget(QLabel("Destek: Windows 10/11 · Türkçe karakterli termal çıktılar"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(appearance)
        layout.addWidget(storage)
        layout.addWidget(printing)
        layout.addWidget(about)
        layout.addStretch(1)

    @staticmethod
    def _card(title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        return card

    @staticmethod
    def _path_field(path: Path) -> QLineEdit:
        field = QLineEdit(str(path))
        field.setReadOnly(True)
        field.setCursorPosition(0)
        return field

    @staticmethod
    def _open_path(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def set_values(self, theme: str, preview_visible: bool = True, language: str = "tr") -> None:
        self.theme.blockSignals(True)
        index = self.theme.findData(theme)
        self.theme.setCurrentIndex(max(0, index))
        self.theme.blockSignals(False)
        self.language.blockSignals(True)
        language_index = self.language.findData(language)
        self.language.setCurrentIndex(max(0, language_index))
        self.language.blockSignals(False)
        self.preview_visible.blockSignals(True)
        self.preview_visible.setChecked(preview_visible)
        self.preview_visible.blockSignals(False)

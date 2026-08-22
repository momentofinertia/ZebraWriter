from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QTabWidget, QVBoxLayout, QWidget

from thermal_app.ui.localization import localize_widget_tree, set_language, tr


def test_translation_lookup_and_language_fallback() -> None:
    set_language("en")
    assert tr("Ayarlar") == "Settings"
    assert tr("Unknown value") == "Unknown value"

    set_language("invalid")
    assert tr("Ayarlar") == "Ayarlar"


def test_widget_tree_can_switch_between_english_and_turkish() -> None:
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel("Ayarlar")
    combo = QComboBox()
    combo.addItem("Sistem", "system")
    tabs = QTabWidget()
    page = QWidget()
    tabs.addTab(page, "Geçmiş")
    layout.addWidget(label)
    layout.addWidget(combo)
    layout.addWidget(tabs)

    set_language("en")
    localize_widget_tree(root)
    assert label.text() == "Settings"
    assert combo.itemText(0) == "System"
    assert tabs.tabText(0) == "History"

    set_language("tr")
    localize_widget_tree(root)
    assert label.text() == "Ayarlar"
    assert combo.itemText(0) == "Sistem"
    assert tabs.tabText(0) == "Geçmiş"

    root.deleteLater()
    app.processEvents()

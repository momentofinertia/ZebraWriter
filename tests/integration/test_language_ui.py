from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow


def test_english_interface_has_no_turkish_chrome(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    context = build_context(AppPaths.under(tmp_path / "language-ui"))
    context.settings_service.set_language("en")
    window = MainWindow(context)
    app.processEvents()

    visible_chrome = [
        widget.text()
        for widget in [
            *window.findChildren(QLabel),
            *window.findChildren(QAbstractButton),
        ]
        if widget.text()
    ]
    untranslated = sorted(
        {text for text in visible_chrome if any(character in text for character in "çğıöşüÇĞİÖŞÜ")}
    )

    assert context.settings_service.language() == "en"
    assert window._tabs.tabText(window._history_tab_index) == "History"
    assert untranslated == []

    window.close()
    QThreadPool.globalInstance().waitForDone(2000)
    app.processEvents()

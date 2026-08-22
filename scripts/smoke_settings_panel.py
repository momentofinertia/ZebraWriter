from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QFrame

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow
from thermal_app.ui.theme import configure_application_font


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "settings-smoke"
    app = QApplication([])
    configure_application_font(app)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    context = build_context(AppPaths.under(output / f"app-data-{stamp}"))
    window = MainWindow(context)
    window.resize(900, 650)
    window.show()
    window.change_theme("light")
    window._tabs.setCurrentWidget(window._settings_panel)

    def verify() -> None:
        panel = window._settings_panel
        cards = panel.findChildren(QFrame)
        screenshot = output / "settings-light.png"
        output.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(screenshot))
        card_count = sum(1 for card in cards if card.objectName() == "settingsCard")
        palette = QApplication.palette()
        palette_ok = (
            palette.color(QPalette.Window).name() == "#f0efeb"
            and palette.color(QPalette.Base).name() == "#fbfaf7"
            and palette.color(QPalette.Text).name() == "#27313a"
        )
        window.change_theme("dark")
        dark_palette_ok = QApplication.palette().color(QPalette.Window).name() == "#111827"
        window.change_theme("light")
        restored_light_ok = QApplication.palette().color(QPalette.Window).name() == "#f0efeb"
        panel.language.setCurrentIndex(panel.language.findData("en"))
        app.processEvents()
        english_screenshot = output / "settings-light-en.png"
        window.grab().save(str(english_screenshot))
        language_english_ok = window._tabs.tabText(window._history_tab_index) == "History"
        language_saved_ok = context.settings_service.language() == "en"
        panel.language.setCurrentIndex(panel.language.findData("tr"))
        language_turkish_ok = window._tabs.tabText(window._history_tab_index) == "Geçmiş"
        ok = (
            card_count == 4
            and panel.preview_visible.isChecked()
            and panel.theme.count() == 3
            and panel.language.count() == 2
            and palette_ok
            and dark_palette_ok
            and restored_light_ok
            and language_english_ok
            and language_saved_ok
            and language_turkish_ok
        )
        print(f"settings_cards={card_count} themes={panel.theme.count()} languages={panel.language.count()} preview_default={panel.preview_visible.isChecked()} palette_ok={palette_ok} dark_palette_ok={dark_palette_ok} restored_light_ok={restored_light_ok} language_english_ok={language_english_ok} language_saved_ok={language_saved_ok} language_turkish_ok={language_turkish_ok} screenshot={screenshot} english_screenshot={english_screenshot}")
        app.exit(0 if ok else 1)

    QTimer.singleShot(900, verify)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

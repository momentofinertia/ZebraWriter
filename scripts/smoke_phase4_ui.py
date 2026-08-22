from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow
from thermal_app.ui.theme import configure_application_font


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    output = Path(__file__).resolve().parents[1] / "output"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    paths = AppPaths.under(output / f"phase4-ui-data-{stamp}")
    app = QApplication([])
    configure_application_font(app)
    context = build_context(paths)
    context.settings_service.set_theme("light")
    if not context.preset_service.list_all():
        context.preset_service.save_new(
            "Günlük hızlı not",
            "note.quick",
            "paper-56mm",
            {
                "title": "Hatırlatma",
                "text": "ZebraWriter Faz 4 UI smoke",
                "date_time": "22.08.2026 14:00",
                "include_qr": False,
            },
            {},
            pinned=True,
        )
    window = MainWindow(context)
    window.show()

    captures = [
        (0, output / "phase4-dashboard.png"),
        (1, output / "phase4-editor.png"),
        (2, output / "phase4-designer.png"),
        (3, output / "phase4-history.png"),
        (4, output / "phase4-todoist.png"),
        (5, output / "phase4-settings.png"),
    ]

    def capture(index: int = 0) -> None:
        if index >= len(captures):
            print(
                f"tabs={window._tabs.count()} printers={window._printer_combo.count()} "
                f"presets={window._preset_panel.table.rowCount()} "
                f"history={window._history_panel.table.rowCount()}"
            )
            app.quit()
            return
        tab, path = captures[index]
        window._tabs.setCurrentIndex(tab)
        app.processEvents()
        window.grab().save(str(path))
        QTimer.singleShot(250, lambda: capture(index + 1))

    QTimer.singleShot(1800, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

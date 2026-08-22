from __future__ import annotations

import os
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1.5")

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow
from thermal_app.ui.theme import configure_application_font


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "template-examples-smoke"
    app = QApplication([])
    configure_application_font(app)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    context = build_context(AppPaths.under(output / f"app-data-{stamp}"))
    window = MainWindow(context)
    window.resize(1280, 860)
    window.show()

    def open_recipe_preset() -> None:
        dashboard = output / "preset-examples-dashboard.png"
        window.grab().save(str(dashboard))
        window.load_preset("builtin.example.recipe")
        window._visual_style.setCurrentIndex(window._visual_style.findData("graphic"))

    def verify() -> None:
        pixmap = window._preview.pixmap()
        job = window._latest_job
        preset_names = [
            window._preset_panel.table.item(row, 0).text()
            for row in range(window._preset_panel.table.rowCount())
        ]
        ten_examples = len([name for name in preset_names if name.startswith("Örnek —")]) == 10
        has_preview = pixmap is not None and not pixmap.isNull() and job is not None
        border_x = window._preview.width() - (pixmap.width() if pixmap else 0)
        border_y = window._preview.height() - (pixmap.height() if pixmap else 0)
        full_receipt = bool(job and job.canvas_height >= 900)
        graphic_style = window._visual_style.currentData() == "graphic"
        screenshot = output / "recipe-example-ui.png"
        output.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(screenshot))
        print(
            f"has_preview={has_preview} canvas={getattr(job, 'canvas_width', 0)}x"
            f"{getattr(job, 'canvas_height', 0)} label_border={border_x}x{border_y} "
                f"full_receipt={full_receipt} ten_examples={ten_examples} graphic_style={graphic_style} "
            f"ui={screenshot} "
            f"receipt={getattr(job, 'preview_artifact_path', None)}"
        )
        app.exit(
            0
            if has_preview and full_receipt and ten_examples and graphic_style and border_x == 48 and border_y == 48
            else 1
        )

    QTimer.singleShot(1200, open_recipe_preset)
    QTimer.singleShot(5000, verify)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

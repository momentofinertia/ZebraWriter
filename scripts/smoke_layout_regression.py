from __future__ import annotations

import argparse
import os

_parser = argparse.ArgumentParser()
_parser.add_argument("--theme", choices=("light", "dark"), default=os.environ.get("ZEBRAWRITER_SMOKE_THEME", "dark"))
_parser.add_argument("--scale", default=os.environ.get("ZEBRAWRITER_SMOKE_SCALE", "1.5"))
_parser.add_argument("--width", type=int, default=int(os.environ.get("ZEBRAWRITER_SMOKE_WIDTH", "900")))
_parser.add_argument("--height", type=int, default=int(os.environ.get("ZEBRAWRITER_SMOKE_HEIGHT", "650")))
_parser.add_argument("--language", choices=("tr", "en"), default=os.environ.get("ZEBRAWRITER_SMOKE_LANGUAGE", "tr"))
_args = _parser.parse_args()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", _args.scale)

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QScrollArea

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow
from thermal_app.ui.theme import configure_application_font


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "output"
    theme = _args.theme
    scale = _args.scale
    width = _args.width
    height = _args.height
    scale_tag = scale.replace(".", "")
    run_tag = f"{theme}-{width}x{height}-{scale_tag}"
    app = QApplication([])
    configure_application_font(app)
    context = build_context(AppPaths.under(output / f"layout-regression-data-{run_tag}"))
    context.settings_service.set_theme(theme)
    context.settings_service.set_language(_args.language)
    context.settings_service.set_preview_visible(True)
    context.settings_service.set_editor_splitter_sizes(580, 420)
    window = MainWindow(context)
    window.resize(width, height)
    todo_index = next(
        index
        for index in range(window._template_combo.count())
        if getattr(window._template_combo.itemData(index), "id", None) == "todo.basic"
    )
    window._template_combo.setCurrentIndex(todo_index)
    window._tabs.setCurrentIndex(window._editor_tab_index)
    window.show()

    def verify() -> None:
        nested_scroll_removed = not window._controls_scroll.findChildren(QScrollArea)
        action_bottom = window._action_bar.mapTo(window, window._action_bar.rect().bottomLeft()).y()
        editor_bottom = window._editor_panel.mapTo(window, window._editor_panel.rect().bottomLeft()).y()
        actions_fixed = window._action_bar.isVisible() and action_bottom <= editor_bottom
        scroll_max = window._controls_scroll.verticalScrollBar().maximum()
        splitter_sizes = window._splitter.sizes()
        offset_range = (
            window._calibration_offset.minimum(),
            window._calibration_offset.maximum(),
        )
        window._device_card.set_expanded(False)
        app.processEvents()
        collapsible = not window._device_card.is_expanded()
        window.toggle_preview_panel()
        preview_hidden = window._preview_card.isHidden()
        window.toggle_preview_panel()
        preview_restored = not window._preview_card.isHidden()
        screenshot = output / f"layout-regression-{run_tag}.png"
        window.grab().save(str(screenshot))
        calibration_index = next(
            index
            for index in range(window._template_combo.count())
            if getattr(window._template_combo.itemData(index), "id", None) == "system.calibration"
        )
        window._template_combo.setCurrentIndex(calibration_index)
        window._controls_scroll.verticalScrollBar().setValue(0)

        def capture_calibration() -> None:
            calibration_screenshot = output / f"layout-regression-calibration-{run_tag}.png"
            window.grab().save(str(calibration_screenshot))
            print(
                f"theme={theme} scale={scale} size={width}x{height} language={_args.language} "
                f"nested_scroll_removed={nested_scroll_removed} actions_fixed={actions_fixed} "
                f"outer_scroll_max={scroll_max} splitter_sizes={splitter_sizes} "
                f"collapsible={collapsible} preview_hidden={preview_hidden} "
                f"preview_restored={preview_restored} offset_range={offset_range} "
                f"layout_screenshot={screenshot} calibration_screenshot={calibration_screenshot}"
            )
            passed = (
                nested_scroll_removed
                and actions_fixed
                and scroll_max > 0
                and len(splitter_sizes) == 2
                and splitter_sizes[0] > splitter_sizes[1]
                and collapsible
                and preview_hidden
                and preview_restored
                and offset_range == (-200, 200)
            )
            app.exit(0 if passed else 1)

        QTimer.singleShot(450, capture_calibration)

    QTimer.singleShot(2200, verify)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1.0")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QCheckBox

from thermal_app.bootstrap import build_context
from thermal_app.config import AppPaths
from thermal_app.ui.main_window import MainWindow
from thermal_app.ui.theme import configure_application_font


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / "output" / "document-designer-smoke"
    output.mkdir(parents=True, exist_ok=True)
    epub = output / "smoke.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="O/content.opf"/></rootfiles></container>')
        archive.writestr(
            "O/content.opf",
            '<package><metadata><title>Smoke Belgesi</title></metadata><manifest>'
            '<item id="x" href="x.xhtml" media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="x"/></spine></package>',
        )
        archive.writestr("O/x.xhtml", "<html><body><h1>Başlık</h1><p>Türkçe metin</p><ul><li>Madde</li></ul></body></html>")
    app = QApplication([])
    configure_application_font(app)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    context = build_context(AppPaths.under(output / f"app-data-{stamp}"))
    window = MainWindow(context)
    window.resize(1100, 760)
    window.show()
    app.processEvents()
    imported = context.document_import_service.import_document(epub)
    designer = window._designer_panel
    designer.set_design("todo.basic", {"title": "Tasarımcı testi"}, {})
    builtin_editing = not designer._schema_form.isHidden() and designer._block_section.isHidden()
    title_widget = designer._schema_form._widgets["title"][1]
    title_widget.setText("Tasarımcıdan gelen başlık")
    app.processEvents()
    builtin_data_flow = bool(
        designer.current_design()
        and designer.current_design()[1].get("title") == "Tasarımcıdan gelen başlık"
    )
    designer.new_template()
    designer._name.setText(imported.title)
    designer._blocks = [dict(block) for block in imported.blocks]
    designer._rebuild_block_list()
    window._tabs.setCurrentIndex(window._designer_tab_index)
    designer.save_template()
    app.processEvents()
    custom_present = any(
        getattr(window._template_combo.itemData(index), "id", "").startswith("custom-")
        for index in range(window._template_combo.count())
    )
    designer.open_in_editor()
    app.processEvents()
    open_button_flow = window._tabs.currentIndex() == window._editor_tab_index
    tab_names = [window._tabs.tabText(index) for index in range(window._tabs.count())]
    developer_removed = not any(
        isinstance(widget, QCheckBox) and "Developer" in widget.text()
        for widget in window.findChildren(QCheckBox)
    )
    screenshot = output / "designer-ui.png"
    window.grab().save(str(screenshot))
    passed = (
        imported.title == "Smoke Belgesi"
        and len(imported.blocks) == 3
        and custom_present
        and "Tasarımcı" in tab_names
        and developer_removed
        and builtin_editing
        and builtin_data_flow
        and open_button_flow
    )
    print(
        f"imported_blocks={len(imported.blocks)} custom_present={custom_present} "
        f"designer_tab={'Tasarımcı' in tab_names} developer_removed={developer_removed} "
        f"builtin_editing={builtin_editing} "
        f"builtin_data_flow={builtin_data_flow} "
        f"open_button_flow={open_button_flow} "
        f"screenshot={screenshot}"
    )
    QTimer.singleShot(250, lambda: app.exit(0 if passed else 1))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

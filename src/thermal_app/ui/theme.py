from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from thermal_app.config import project_root
from thermal_app.domain.errors import RenderingError


def configure_application_font(app: QApplication) -> None:
    font_path = project_root() / "assets" / "fonts" / "Vera.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id < 0:
        raise RenderingError("Qt uygulama fontu yüklenemedi.")
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        raise RenderingError("Qt uygulama font ailesi belirlenemedi.")
    app.setFont(QFont(families[0], 10))

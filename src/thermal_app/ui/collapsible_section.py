from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self._toggle = QToolButton()
        self._toggle.setObjectName("sectionToggle")
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setArrowType(Qt.DownArrow)
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._content = QWidget()
        self.content_layout = QVBoxLayout(self._content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 14)
        layout.setSpacing(8)
        layout.addWidget(self._toggle)
        layout.addWidget(self._content)
        self._toggle.toggled.connect(self.set_expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._toggle.blockSignals(True)
        self._toggle.setChecked(expanded)
        self._toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self._toggle.blockSignals(False)
        self._content.setVisible(expanded)
        if expanded:
            self.setMaximumHeight(16777215)
        else:
            margins = self.layout().contentsMargins()
            header_height = self._toggle.sizeHint().height() + margins.top() + margins.bottom()
            self.setMaximumHeight(header_height)
        self.updateGeometry()

    def is_expanded(self) -> bool:
        return self._toggle.isChecked()

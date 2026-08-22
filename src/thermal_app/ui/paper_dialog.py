from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from thermal_app.domain.enums import LengthMode
from thermal_app.domain.models import CALIBRATION_OFFSET_LIMIT_DOTS, GC420T_DPI, PaperProfile
from thermal_app.domain.measurements import mm_to_dots
from thermal_app.ui.localization import localize_widget_tree, tr


class CustomPaperDialog(QDialog):
    def __init__(self, parent: object | None = None, profile: PaperProfile | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Özel kağıt profili")
        self._profile: PaperProfile | None = None
        self._editing_id = profile.id if profile else None

        self._name = QLineEdit(tr("Özel kağıt"))
        self._width = QDoubleSpinBox()
        self._width.setRange(20.0, 104.0)
        self._width.setDecimals(1)
        self._width.setSuffix(" mm")
        self._width.setValue(56.0)
        self._printable = QSpinBox()
        self._printable.setRange(1, 832)
        self._left = QSpinBox()
        self._right = QSpinBox()
        for margin in (self._left, self._right):
            margin.setRange(0, 200)
            margin.setSuffix(" dot")
            margin.setValue(12)
        self._top = QSpinBox()
        self._bottom = QSpinBox()
        for margin in (self._top, self._bottom):
            margin.setRange(0, 400)
            margin.setSuffix(" dot")
        self._top.setValue(12)
        self._bottom.setValue(16)
        self._horizontal_offset = QSpinBox()
        self._horizontal_offset.setRange(
            -CALIBRATION_OFFSET_LIMIT_DOTS,
            CALIBRATION_OFFSET_LIMIT_DOTS,
        )
        self._horizontal_offset.setSuffix(" dot")
        self._length_mode = QComboBox()
        self._length_mode.addItem("Continuous", LengthMode.CONTINUOUS)
        self._length_mode.addItem("Fixed", LengthMode.FIXED)
        self._fixed_length = QDoubleSpinBox()
        self._fixed_length.setRange(10.0, 500.0)
        self._fixed_length.setDecimals(1)
        self._fixed_length.setSuffix(" mm")
        self._fixed_length.setValue(50.0)
        if profile:
            self._name.setText(profile.name)
            self._width.setValue(float(profile.width_mm))
            self._printable.setMaximum(profile.physical_width_dots)
            self._printable.setValue(profile.printable_width_dots)
            self._left.setValue(profile.margin_left_dots)
            self._right.setValue(profile.margin_right_dots)
            self._top.setValue(profile.margin_top_dots)
            self._bottom.setValue(profile.margin_bottom_dots)
            self._horizontal_offset.setValue(profile.horizontal_content_offset_dots)
            self._length_mode.setCurrentIndex(1 if profile.length_mode is LengthMode.FIXED else 0)
            if profile.fixed_length_mm is not None:
                self._fixed_length.setValue(float(profile.fixed_length_mm))
        else:
            self._update_printable_default()
        self._width.valueChanged.connect(self._update_printable_default)
        self._length_mode.currentIndexChanged.connect(self._update_length_mode)
        self._update_length_mode()

        form = QFormLayout()
        form.addRow("Ad", self._name)
        form.addRow("Fiziksel genişlik", self._width)
        dpi_display = QLineEdit("203 (sabit)")
        dpi_display.setReadOnly(True)
        form.addRow("DPI", dpi_display)
        form.addRow("Printable width", self._printable)
        form.addRow("Sol marj", self._left)
        form.addRow("Sağ marj", self._right)
        form.addRow("Üst marj", self._top)
        form.addRow("Alt marj", self._bottom)
        self._horizontal_offset.setToolTip("Negatif değer içeriği sola, pozitif değer sağa taşır.")
        form.addRow("Yatay ofset (- sola / + sağa)", self._horizontal_offset)
        form.addRow("Uzunluk modu", self._length_mode)
        form.addRow("Sabit uzunluk", self._fixed_length)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_profile)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        localize_widget_tree(self)

    def _update_printable_default(self) -> None:
        physical = mm_to_dots(str(self._width.value()), GC420T_DPI)
        self._printable.setMaximum(physical)
        self._printable.setValue(max(1, physical - self._left.value() - self._right.value()))

    def _update_length_mode(self) -> None:
        self._fixed_length.setEnabled(self._length_mode.currentData() is LengthMode.FIXED)

    def _accept_profile(self) -> None:
        try:
            self._profile = PaperProfile(
                id=self._editing_id or f"paper-custom-{uuid4()}",
                name=self._name.text().strip(),
                width_mm=Decimal(str(self._width.value())),
                dpi=GC420T_DPI,
                printable_width_dots=self._printable.value(),
                margin_left_dots=self._left.value(),
                margin_right_dots=self._right.value(),
                margin_top_dots=self._top.value(),
                margin_bottom_dots=self._bottom.value(),
                horizontal_content_offset_dots=self._horizontal_offset.value(),
                length_mode=self._length_mode.currentData(),
                fixed_length_mm=(
                    Decimal(str(self._fixed_length.value()))
                    if self._length_mode.currentData() is LengthMode.FIXED
                    else None
                ),
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Geçersiz kağıt profili"), str(exc))
            return
        self.accept()

    @property
    def profile(self) -> PaperProfile | None:
        return self._profile

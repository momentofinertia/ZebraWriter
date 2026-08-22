from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def as_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def mm_to_dots(mm: Decimal | int | float | str, dpi: int) -> int:
    millimeters = as_decimal(mm)
    if millimeters < 0:
        raise ValueError("Milimetre değeri negatif olamaz.")
    if dpi <= 0:
        raise ValueError("DPI pozitif olmalıdır.")
    dots = millimeters / Decimal("25.4") * Decimal(dpi)
    return int(dots.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

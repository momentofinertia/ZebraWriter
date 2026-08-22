from decimal import Decimal

import pytest

from thermal_app.domain.measurements import mm_to_dots


@pytest.mark.parametrize(
    ("millimeters", "expected"),
    [(56, 448), (57, 456), (58, 464), (80, 639), (100, 799)],
)
def test_mm_to_dots_uses_half_up_rounding(millimeters: int, expected: int) -> None:
    assert mm_to_dots(millimeters, 203) == expected


def test_mm_to_dots_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="negatif"):
        mm_to_dots(Decimal("-0.1"), 203)

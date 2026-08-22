from dataclasses import replace
from decimal import Decimal

import pytest

from thermal_app.domain.enums import LengthMode
from thermal_app.domain.errors import InvalidPaperProfileError
from thermal_app.domain.models import PaperProfile, validate_paper_for_printer
from thermal_app.domain.profiles import default_paper_profiles


def test_reference_56mm_profile_matches_calibration_default(paper_56: PaperProfile) -> None:
    assert paper_56.physical_width_dots == 448
    assert paper_56.printable_width_dots == 424
    assert paper_56.margin_left_dots == paper_56.margin_right_dots == 12
    assert paper_56.horizontal_content_offset_dots == -7


def test_margins_cannot_exceed_physical_width(paper_56: PaperProfile) -> None:
    with pytest.raises(InvalidPaperProfileError, match="fiziksel"):
        replace(paper_56, printable_width_dots=440)


def test_horizontal_content_offset_allows_calibration_trials(paper_56: PaperProfile) -> None:
    assert replace(paper_56, horizontal_content_offset_dots=-200).horizontal_content_offset_dots == -200
    assert replace(paper_56, horizontal_content_offset_dots=200).horizontal_content_offset_dots == 200
    with pytest.raises(InvalidPaperProfileError, match="kalibrasyon"):
        replace(paper_56, horizontal_content_offset_dots=201)


def test_fixed_length_requires_positive_value(paper_56: PaperProfile) -> None:
    with pytest.raises(InvalidPaperProfileError, match="Sabit uzunluk"):
        replace(paper_56, length_mode=LengthMode.FIXED)


def test_paper_cannot_exceed_gc420t_width(printer: object) -> None:
    paper = PaperProfile(
        id="too-wide",
        name="105 mm",
        width_mm=Decimal("105"),
        dpi=203,
        printable_width_dots=815,
        margin_left_dots=12,
        margin_right_dots=12,
        margin_top_dots=0,
        margin_bottom_dots=0,
    )
    with pytest.raises(InvalidPaperProfileError, match="maksimum"):
        validate_paper_for_printer(paper, printer)


def test_default_profiles_are_unique_and_valid(printer: object) -> None:
    profiles = default_paper_profiles()
    assert len({profile.id for profile in profiles}) == 5
    for profile in profiles:
        validate_paper_for_printer(profile, printer)

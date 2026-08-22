from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256

from thermal_app.application.dto import RenderOptions
from thermal_app.application.services.print_service import TEST_PAGE_TEMPLATE
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.domain.measurements import mm_to_dots
from thermal_app.domain.models import PaperProfile
from PIL import ImageOps

from thermal_app.infrastructure.artifacts.local_artifact_store import document_to_image
from thermal_app.rendering.test_page_renderer import TestPageRenderer


FIXED_TIME = datetime(2026, 8, 22, 9, 30, tzinfo=timezone.utc)


def test_renderer_reflows_between_56_and_80mm(font_paths: tuple) -> None:
    renderer = TestPageRenderer(*font_paths, clock=lambda: FIXED_TIME)
    paper_56, paper_80 = default_paper_profiles()[0], default_paper_profiles()[3]
    rendered_56 = renderer.render(TEST_PAGE_TEMPLATE, {}, paper_56, RenderOptions())
    rendered_80 = renderer.render(TEST_PAGE_TEMPLATE, {}, paper_80, RenderOptions())
    assert rendered_56.width_dots == 448
    assert rendered_80.width_dots == 639
    assert rendered_56.bitmap_1bpp != rendered_80.bitmap_1bpp


def test_turkish_test_page_matches_golden_bitmap(font_paths: tuple, paper_56: object) -> None:
    renderer = TestPageRenderer(*font_paths, clock=lambda: FIXED_TIME)
    document = renderer.render(
        TEST_PAGE_TEMPLATE,
        {"spooler_name": "ZDesigner GC420t", "timestamp": FIXED_TIME},
        paper_56,
        RenderOptions(),
    )
    digest = sha256(document.bitmap_1bpp).hexdigest()
    assert digest == "384b8ab1d8a749857f578815dfe185e6b7be94cf1e64dc5d1130bab904661cee"


def test_calibrated_content_stays_inside_physical_canvas(font_paths: tuple, paper_56: object) -> None:
    document = TestPageRenderer(*font_paths, clock=lambda: FIXED_TIME).render(
        TEST_PAGE_TEMPLATE, {}, paper_56, RenderOptions()
    )
    ink_bounds = ImageOps.invert(document_to_image(document).convert("L")).getbbox()
    assert ink_bounds is not None
    assert ink_bounds[0] == 5
    assert ink_bounds[2] == 429
    assert document.width_dots == 448


def test_preview_image_is_reconstructed_from_canonical_black_bits(font_paths: tuple, paper_56: object) -> None:
    document = TestPageRenderer(*font_paths, clock=lambda: FIXED_TIME).render(
        TEST_PAGE_TEMPLATE, {}, paper_56, RenderOptions()
    )
    preview = document_to_image(document)
    assert preview.size == (document.width_dots, document.height_dots)
    assert 0 in preview.get_flattened_data()


def test_custom_width_creates_matching_canvas(font_paths: tuple) -> None:
    physical = mm_to_dots(70, 203)
    paper = PaperProfile(
        id="paper-custom-70",
        name="Özel 70 mm",
        width_mm=Decimal("70"),
        dpi=203,
        printable_width_dots=physical - 24,
        margin_left_dots=12,
        margin_right_dots=12,
        margin_top_dots=12,
        margin_bottom_dots=16,
    )
    document = TestPageRenderer(*font_paths, clock=lambda: FIXED_TIME).render(
        TEST_PAGE_TEMPLATE, {}, paper, RenderOptions()
    )
    assert document.width_dots == physical

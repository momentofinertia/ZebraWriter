from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont, ImageOps

from thermal_app.application.dto import RenderOptions
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions
from thermal_app.config import project_root
from thermal_app.domain.measurements import mm_to_dots
from thermal_app.domain.models import PaperProfile
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.rendering.pillow_document_renderer import PillowDocumentRenderer
from thermal_app.rendering.primitives import (
    BadgeRow,
    Callout,
    ChecklistValue,
    CutLine,
    FramedImage,
    GraphicHeader,
    NumberedStep,
    QrBlock,
    SectionBand,
)
from thermal_app.rendering.template_builders import (
    PhotoBuilder,
    QrBuilder,
    RecipeBuilder,
    ShoppingBuilder,
    TodoBuilder,
)


GRAPHIC_SAMPLES: dict[str, dict[str, object]] = {
    "todo.basic": {
        "title": "Bugünün İşleri",
        "date": "22.08.2026",
        "priority_tasks": ["Raporu bitir", "Kargoyu teslim al", "Telefon et"],
        "tasks": [{"title": "Market", "due_time": "18:00", "category": "Ev"}],
        "note": "Önce en önemli işleri tamamla.",
        "show_checkboxes": True,
    },
    "shopping.basic": {
        "title": "Alışveriş",
        "date": "22.08.2026",
        "items": [
            {"product": "Domates", "quantity": "1 kg", "category": "Sebze & Meyve"},
            {"product": "Süt", "quantity": "2", "category": "Süt & Kahvaltı"},
        ],
        "show_checkboxes": True,
    },
    "recipe.basic": {
        "name": "Mercimek Çorbası",
        "prep_time": "10 dk",
        "cook_time": "30 dk",
        "servings": "4",
        "ingredients": ["1 bardak mercimek", "1 soğan", "1 havuç"],
        "steps": ["Sebzeleri doğra.", "Tüm malzemeleri kaynat.", "Blenderdan geçir."],
        "notes": "Serviste limon ekleyin.",
    },
    "note.quick": {
        "title": "Hatırlatma",
        "text": "Çiçekleri sula ve güneş alan pencereye taşı.",
        "date_time": "22.08.2026 10:30",
        "include_qr": False,
    },
    "photo.basic": {
        "image_path": str(project_root() / "assets" / "samples" / "thermal-photo.png"),
        "caption": "Termal fotoğraf ton testi",
        "fit": "fit_width",
        "rotation": "0",
    },
    "qr.basic": {
        "title": "Web Sitesi",
        "kind": "URL",
        "payload": "https://example.com",
        "ssid": "",
        "password": "",
        "caption": "Telefonunuzla tarayın",
    },
}


@pytest.fixture
def graphic_renderer(font_paths: tuple[Path, Path]) -> PillowDocumentRenderer:
    return PillowDocumentRenderer(*font_paths)


def test_graphic_template_golden_hashes(graphic_renderer: PillowDocumentRenderer) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    paper = default_paper_profiles()[0]
    hashes = {
        template_id: sha256(
            graphic_renderer.render(
                catalog.get(template_id),
                data,
                paper,
                RenderOptions(visual_style="graphic"),
            ).bitmap_1bpp
        ).hexdigest()
        for template_id, data in GRAPHIC_SAMPLES.items()
    }
    assert hashes == {
        "todo.basic": "5ac483765323b767019baad2446fd0d38603d0069814927fd46650f815a6b40f",
        "shopping.basic": "baf2ea4f8bc26809e678425b985f28542ce9481b7aad4ab37196c44c8a63ecfb",
        "recipe.basic": "e7bd0c957e8aaacf582cf89d5e997b6c4e5deac2bd83665d0ca384a288a5e13d",
        "note.quick": "586cfbedee59fac779d929b7ccbd52e83a5007e1de9e6a118598d85b7bb8b3bb",
        "photo.basic": "b7f9f75572f06d356dc6e4ca64763359a63e4a696b7e8131bdb2dc5e764d4923",
        "qr.basic": "1706fb64cf2272d4b8ea3f852a776906ff1890f05704f706ff90f2be604f61d6",
    }


def test_graphic_templates_reflow_on_supported_and_custom_widths(
    graphic_renderer: PillowDocumentRenderer,
) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    defaults = default_paper_profiles()
    physical = mm_to_dots(65, 203)
    custom = PaperProfile(
        id="paper-custom-65mm",
        name="65 mm",
        width_mm=Decimal("65"),
        dpi=203,
        printable_width_dots=physical - 24,
        margin_left_dots=12,
        margin_right_dots=12,
        margin_top_dots=12,
        margin_bottom_dots=16,
    )
    papers = (defaults[0], defaults[2], defaults[3], defaults[4], custom)

    for paper in papers:
        for template_id, data in GRAPHIC_SAMPLES.items():
            document = graphic_renderer.render(
                catalog.get(template_id),
                data,
                paper,
                RenderOptions(visual_style="graphic"),
            )
            assert document.width_dots == paper.physical_width_dots
            assert document.height_dots > paper.margin_top_dots + paper.margin_bottom_dots
            assert any(document.bitmap_1bpp)


def test_graphic_builders_use_thermal_safe_primitives() -> None:
    todo = TodoBuilder().build(GRAPHIC_SAMPLES["todo.basic"], "graphic")
    shopping = ShoppingBuilder().build(GRAPHIC_SAMPLES["shopping.basic"], "graphic")
    recipe = RecipeBuilder().build(GRAPHIC_SAMPLES["recipe.basic"], "graphic")
    photo = PhotoBuilder().build(GRAPHIC_SAMPLES["photo.basic"], "graphic")
    qr = QrBuilder().build(GRAPHIC_SAMPLES["qr.basic"], "graphic")

    assert any(isinstance(item, GraphicHeader) for item in todo)
    assert any(isinstance(item, SectionBand) for item in shopping)
    assert any(isinstance(item, ChecklistValue) for item in shopping)
    assert any(isinstance(item, BadgeRow) for item in recipe)
    assert any(isinstance(item, NumberedStep) for item in recipe)
    assert any(isinstance(item, Callout) for item in recipe)
    assert any(isinstance(item, FramedImage) for item in photo)
    assert any(isinstance(item, CutLine) for item in qr)


def test_qr_keeps_a_white_quiet_zone(font_paths: tuple[Path, Path]) -> None:
    canvas = Image.new("L", (448, 500), 255)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(font_paths[0]), 16)
    end_y = PillowDocumentRenderer._draw_qr(
        canvas,
        draw,
        QrBlock("https://example.com"),
        font,
        12,
        435,
        20,
    )
    black_bounds = ImageOps.invert(canvas.crop((0, 0, 448, end_y))).getbbox()

    assert black_bounds is not None
    assert black_bounds[0] > 12
    assert black_bounds[1] > 20
    assert black_bounds[2] < 436


def test_visual_style_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Görsel stil"):
        RenderOptions(visual_style="ornate")

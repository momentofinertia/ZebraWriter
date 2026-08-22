from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from thermal_app.application.dto import RenderOptions
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions
from thermal_app.domain.enums import LengthMode
from thermal_app.domain.errors import RenderingError
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.rendering.pillow_document_renderer import PillowDocumentRenderer


SAMPLES: dict[str, dict[str, object]] = {
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
    "qr.basic": {
        "title": "Web Sitesi",
        "kind": "URL",
        "payload": "https://example.com",
        "ssid": "",
        "password": "",
        "caption": "Telefonunuzla tarayın",
    },
    "system.calibration": {"left_offset_dots": "0", "top_offset_dots": "0"},
}


@pytest.fixture
def document_renderer(font_paths: tuple[Path, Path]) -> PillowDocumentRenderer:
    return PillowDocumentRenderer(*font_paths)


@pytest.mark.parametrize("template_id", list(SAMPLES))
def test_templates_reflow_at_56_and_80mm(
    document_renderer: PillowDocumentRenderer,
    template_id: str,
) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    paper_56, paper_80 = default_paper_profiles()[0], default_paper_profiles()[3]
    narrow = document_renderer.render(catalog.get(template_id), SAMPLES[template_id], paper_56, RenderOptions())
    wide = document_renderer.render(catalog.get(template_id), SAMPLES[template_id], paper_80, RenderOptions())
    assert narrow.width_dots == 448
    assert wide.width_dots == 639
    assert narrow.bitmap_1bpp != wide.bitmap_1bpp


def test_builtin_template_golden_hashes(document_renderer: PillowDocumentRenderer) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    paper = default_paper_profiles()[0]
    hashes = {
        template_id: sha256(
            document_renderer.render(catalog.get(template_id), data, paper, RenderOptions()).bitmap_1bpp
        ).hexdigest()
        for template_id, data in SAMPLES.items()
    }
    assert hashes == {
        "todo.basic": "f39413107410ed2cf2cdbfba4ad6aa000fa8f40ead814bcad4d73a36524621d5",
        "shopping.basic": "f54f1ee95fb2cb72bcd146340fe97a7d2a51c6dc7b1526827f6b06b0b64fb241",
        "recipe.basic": "b86573d0f8b1b047990776595e327ac4d83969d8408ccc6385c2df7e7ed1eb89",
        "note.quick": "c5d088a70826dadefc13834d71c026a7abe620743b4c9432871b5002ad2a135a",
        "qr.basic": "85c83e3f24d1664339732ba748eeb29e0238635d3ffbc4aecd2ab962b79c8fbc",
        "system.calibration": "7669bddcbda9bed3cebf75cf489df2a925049a2be95d75c1a8b7b31c143c054c",
    }


def test_long_recipe_grows_continuous_media(document_renderer: PillowDocumentRenderer) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    paper = default_paper_profiles()[0]
    short = document_renderer.render(catalog.get("recipe.basic"), SAMPLES["recipe.basic"], paper, RenderOptions())
    long_data = dict(SAMPLES["recipe.basic"])
    long_data["steps"] = [f"Uzun tarif adımı {index}: malzemeleri dikkatlice karıştır." for index in range(30)]
    long = document_renderer.render(catalog.get("recipe.basic"), long_data, paper, RenderOptions())
    assert long.height_dots > short.height_dots * 2


def test_fixed_media_overflow_is_not_cropped(document_renderer: PillowDocumentRenderer) -> None:
    catalog = TemplateCatalog(built_in_definitions())
    paper = replace(
        default_paper_profiles()[0],
        length_mode=LengthMode.FIXED,
        fixed_length_mm=Decimal("20"),
    )
    with pytest.raises(RenderingError, match="kırpılmadı"):
        document_renderer.render(catalog.get("recipe.basic"), SAMPLES["recipe.basic"], paper, RenderOptions())


def test_photo_options_change_live_bitmap(
    document_renderer: PillowDocumentRenderer,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "gradient.png"
    image = Image.new("L", (160, 100))
    image.putdata([round(x / 159 * 255) for _y in range(100) for x in range(160)])
    image.save(image_path)
    data = {"image_path": str(image_path), "caption": "Ton testi", "fit": "fit_width", "rotation": "0"}
    template = TemplateCatalog(built_in_definitions()).get("photo.basic")
    paper = default_paper_profiles()[0]
    threshold = document_renderer.render(template, data, paper, RenderOptions(dithering="threshold"))
    atkinson = document_renderer.render(template, data, paper, RenderOptions(dithering="atkinson"))
    assert threshold.bitmap_1bpp != atkinson.bitmap_1bpp


def test_qr_capacity_error_is_user_friendly(document_renderer: PillowDocumentRenderer) -> None:
    data = dict(SAMPLES["qr.basic"])
    data["payload"] = "x" * 5000
    template = TemplateCatalog(built_in_definitions()).get("qr.basic")
    with pytest.raises(RenderingError, match="kapasitesini"):
        document_renderer.render(template, data, default_paper_profiles()[0], RenderOptions())

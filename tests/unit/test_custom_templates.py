from __future__ import annotations

from datetime import datetime
from pathlib import Path

from thermal_app.application.services.custom_template_service import CustomTemplateService
from thermal_app.application.template_catalog import custom_definition
from thermal_app.application.dto import RenderOptions
from thermal_app.domain.models import CustomTemplate
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import SqliteCustomTemplateRepository
from thermal_app.rendering.pillow_document_renderer import PillowDocumentRenderer


def test_custom_template_round_trip_and_render(tmp_path: Path, font_paths: tuple[Path, Path]) -> None:
    database = Database(tmp_path / "app.db")
    database.initialize()
    service = CustomTemplateService(SqliteCustomTemplateRepository(database))
    saved = service.save(
        "Özel Fiş",
        "Deneme",
        (
            {"type": "heading", "value": "Başlık"},
            {"type": "divider", "thickness": 2},
            {"type": "checklist", "value": "Türkçe görev", "checked": False},
            {"type": "qr", "value": "https://example.com", "secondary": "Tara"},
        ),
    )
    loaded = service.get(saved.id)
    assert loaded is not None
    assert loaded.blocks[0]["value"] == "Başlık"
    definition = custom_definition(loaded.id, loaded.name, loaded.category, list(loaded.blocks))
    renderer = PillowDocumentRenderer(*font_paths)
    document = renderer.render(
        definition,
        {"blocks": list(loaded.blocks)},
        default_paper_profiles()[0],
        RenderOptions(visual_style="graphic"),
    )
    assert document.width_dots == 448
    assert document.height_dots > 100
    assert service.delete(saved.id) is True
    assert service.get(saved.id) is None

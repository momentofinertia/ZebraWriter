from datetime import datetime, timezone
from pathlib import Path

import pytest

from thermal_app.application.preset_catalog import (
    BUILT_IN_PRESET_PREFIX,
    built_in_example_presets,
)
from thermal_app.application.services.preset_service import PresetService
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions
from thermal_app.domain.models import Preset
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import SqlitePresetRepository


def test_ten_examples_are_installed_as_presets_and_user_presets_are_preserved(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "app.db")
    database.initialize()
    repository = SqlitePresetRepository(database)
    service = PresetService(repository)
    now = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    catalog = TemplateCatalog(built_in_definitions())
    examples = built_in_example_presets(catalog, now=now)
    user_preset = Preset(
        id="user-preset",
        name="Benim Presetim",
        template_id="note.quick",
        paper_profile_id="paper-56mm",
        printer_profile_id=None,
        integration_profile_id=None,
        filter_spec={},
        sort_spec={},
        input_data={"text": "Kullanıcı içeriği"},
        render_options={},
        pinned=False,
        created_at=now,
        updated_at=now,
    )
    repository.save(user_preset)
    repository.save(examples[0])
    service.set_pinned(examples[0].id, True)

    service.install_built_ins(examples)

    stored = service.list_all()
    built_ins = [item for item in stored if item.id.startswith(BUILT_IN_PRESET_PREFIX)]
    assert len(built_ins) == 10
    assert repository.get(user_preset.id) == user_preset
    assert repository.get(examples[0].id).pinned is True
    assert {item.template_id for item in built_ins} == {
        "todo.basic",
        "shopping.basic",
        "recipe.basic",
        "note.quick",
        "photo.basic",
        "qr.basic",
    }
    assert {item.name for item in built_ins if "Toplantı" in item.name} == {"Örnek — Toplantı Gündemi"}


def test_built_in_example_preset_cannot_be_deleted(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    database.initialize()
    service = PresetService(SqlitePresetRepository(database))

    with pytest.raises(ValueError, match="Hazır örnek preset"):
        service.delete(f"{BUILT_IN_PRESET_PREFIX}recipe")


def test_user_preset_round_trips_graphic_style(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    database.initialize()
    service = PresetService(SqlitePresetRepository(database))

    saved = service.save_new(
        "Grafikli tarif",
        "recipe.basic",
        "paper-56mm",
        {"name": "Çorba"},
        {"visual_style": "graphic", "threshold": 160},
    )

    loaded = next(item for item in service.list_all() if item.id == saved.id)
    assert loaded.render_options["visual_style"] == "graphic"

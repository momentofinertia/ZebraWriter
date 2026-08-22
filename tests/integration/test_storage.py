from pathlib import Path
from datetime import datetime

from thermal_app.domain.profiles import default_paper_profiles, gc420t_profile
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import (
    SqlitePaperProfileRepository,
    SqlitePresetRepository,
    SqlitePrinterProfileRepository,
    SqliteSettingsRepository,
)
from thermal_app.domain.models import Preset


def test_migration_is_idempotent_and_profiles_round_trip(tmp_path: Path) -> None:
    database = Database(tmp_path / "app.db")
    database.initialize()
    database.initialize()
    assert database.schema_version() == 6

    printer_repo = SqlitePrinterProfileRepository(database)
    paper_repo = SqlitePaperProfileRepository(database)
    printer = gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")
    paper = default_paper_profiles()[0]
    printer_repo.save(printer)
    paper_repo.save(paper)
    assert printer_repo.get(printer.id) == printer
    assert paper_repo.get(paper.id) == paper
    assert paper_repo.get(paper.id).horizontal_content_offset_dots == -7
    assert paper_repo.delete(paper.id) is True
    assert paper_repo.get(paper.id) is None

    settings = SqliteSettingsRepository(database)
    settings.set("theme", "dark")
    assert settings.get("theme") == "dark"

    now = datetime.now().astimezone()
    preset = Preset(
        id="preset-1",
        name="Bugün",
        template_id="todo.basic",
        paper_profile_id="paper-56mm",
        printer_profile_id="printer-1",
        integration_profile_id="todoist-personal",
        filter_spec={"mode": "today"},
        sort_spec={"by": "priority"},
        input_data={"title": "Bugün"},
        render_options={},
        pinned=True,
        created_at=now,
        updated_at=now,
    )
    presets = SqlitePresetRepository(database)
    presets.save(preset)
    assert presets.get(preset.id) == preset
    assert presets.list_all() == [preset]

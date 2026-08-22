from __future__ import annotations

import sqlite3
from pathlib import Path

from thermal_app.infrastructure.storage.database import MIGRATIONS, Database


def test_database_upgrades_existing_phase3_schema_to_phase4(tmp_path: Path) -> None:
    path = tmp_path / "legacy-v4.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (0)")
        for version, migration in enumerate(MIGRATIONS[:4], start=1):
            for statement in migration:
                connection.execute(statement)
            connection.execute("UPDATE schema_version SET version = ?", (version,))
        connection.commit()
    finally:
        connection.close()

    database = Database(path)
    database.initialize()

    assert database.schema_version() == 6
    with database.connect() as upgraded:
        columns = {
            row["name"] for row in upgraded.execute("PRAGMA table_info(presets)").fetchall()
        }
    assert {
        "printer_profile_id",
        "integration_profile_id",
        "filter_spec_json",
        "sort_spec_json",
    } <= columns

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from thermal_app.domain.errors import StorageMigrationError


MIGRATIONS: tuple[tuple[str, ...], ...] = (
    (
        """
        CREATE TABLE printer_profiles (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            spooler_name TEXT NOT NULL,
            driver_name TEXT NOT NULL,
            port_name TEXT NOT NULL,
            dpi INTEGER NOT NULL,
            max_print_width_mm TEXT NOT NULL,
            max_print_width_dots INTEGER NOT NULL,
            default_paper_profile_id TEXT
        )
        """,
        """
        CREATE TABLE paper_profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            width_mm TEXT NOT NULL,
            dpi INTEGER NOT NULL,
            printable_width_dots INTEGER NOT NULL,
            margin_left_dots INTEGER NOT NULL,
            margin_right_dots INTEGER NOT NULL,
            margin_top_dots INTEGER NOT NULL,
            margin_bottom_dots INTEGER NOT NULL,
            media_tracking TEXT NOT NULL,
            length_mode TEXT NOT NULL,
            fixed_length_mm TEXT,
            orientation TEXT NOT NULL,
            feed_after_print_mm TEXT NOT NULL,
            tear_offset_mm TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE print_jobs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            printer_profile_id TEXT NOT NULL,
            paper_profile_id TEXT NOT NULL,
            template_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_reference TEXT,
            status TEXT NOT NULL,
            canvas_width INTEGER,
            canvas_height INTEGER,
            bitmap_artifact_path TEXT,
            preview_artifact_path TEXT,
            encoded_artifact_path TEXT,
            transport_job_id TEXT,
            error_code TEXT,
            error_summary TEXT
        )
        """,
    ),
    (
        """
        ALTER TABLE paper_profiles
        ADD COLUMN horizontal_content_offset_dots INTEGER NOT NULL DEFAULT 0
        """,
    ),
    (
        """
        UPDATE paper_profiles
        SET horizontal_content_offset_dots = -7
        WHERE id = 'paper-56mm'
        """,
    ),
    (
        """
        ALTER TABLE print_jobs
        ADD COLUMN input_data_json TEXT NOT NULL DEFAULT '{}'
        """,
        """
        ALTER TABLE print_jobs
        ADD COLUMN render_options_json TEXT NOT NULL DEFAULT '{}'
        """,
        """
        CREATE TABLE integration_profiles (
            id TEXT PRIMARY KEY,
            provider_type TEXT NOT NULL,
            display_name TEXT NOT NULL,
            enabled INTEGER NOT NULL,
            credential_reference TEXT,
            last_synced_at TEXT,
            last_sync_status TEXT,
            settings_json TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE todoist_cache (
            cache_key TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            synced_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            template_id TEXT NOT NULL,
            paper_profile_id TEXT NOT NULL,
            input_data_json TEXT NOT NULL,
            render_options_json TEXT NOT NULL,
            pinned INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """,
        """
        CREATE INDEX idx_print_jobs_created_at ON print_jobs(created_at DESC)
        """,
    ),
    (
        """
        ALTER TABLE presets
        ADD COLUMN printer_profile_id TEXT
        """,
        """
        ALTER TABLE presets
        ADD COLUMN integration_profile_id TEXT
        """,
        """
        ALTER TABLE presets
        ADD COLUMN filter_spec_json TEXT NOT NULL DEFAULT '{}'
        """,
        """
        ALTER TABLE presets
        ADD COLUMN sort_spec_json TEXT NOT NULL DEFAULT '{}'
        """,
    ),
    (
        """
        CREATE TABLE custom_templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            version INTEGER NOT NULL,
            blocks_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE INDEX idx_custom_templates_updated_at ON custom_templates(updated_at DESC)
        """,
    ),
)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connect() as connection:
                with connection:
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
                    )
                    row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
                    if row is None:
                        connection.execute("INSERT INTO schema_version(version) VALUES (0)")
                        current_version = 0
                    else:
                        current_version = int(row["version"])

                    if current_version > len(MIGRATIONS):
                        raise StorageMigrationError(
                            f"Veritabanı sürümü desteklenenden yeni: {current_version}"
                        )

                    for index in range(current_version, len(MIGRATIONS)):
                        for statement in MIGRATIONS[index]:
                            connection.execute(statement)
                        connection.execute("UPDATE schema_version SET version = ?", (index + 1,))
        except StorageMigrationError:
            raise
        except sqlite3.Error as exc:
            raise StorageMigrationError("SQLite şeması hazırlanamadı.") from exc

    def schema_version(self) -> int:
        with self.connect() as connection:
            row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            return int(row["version"]) if row else 0

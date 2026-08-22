from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from thermal_app.domain.enums import LengthMode, MediaTracking, Orientation, PrintJobStatus
from thermal_app.domain.models import (
    CustomTemplate,
    IntegrationProfile,
    PaperProfile,
    Preset,
    PrinterProfile,
    PrintJob,
    TodoistCacheEntry,
)
from thermal_app.infrastructure.storage.database import Database


def _path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _mapping(value: str | None) -> dict[str, object]:
    decoded = json.loads(value or "{}")
    return decoded if isinstance(decoded, dict) else {}


class SqlitePrinterProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, profile: PrinterProfile) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO printer_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name=excluded.display_name,
                    spooler_name=excluded.spooler_name,
                    driver_name=excluded.driver_name,
                    port_name=excluded.port_name,
                    dpi=excluded.dpi,
                    max_print_width_mm=excluded.max_print_width_mm,
                    max_print_width_dots=excluded.max_print_width_dots,
                    default_paper_profile_id=excluded.default_paper_profile_id
                """,
                (
                    profile.id,
                    profile.display_name,
                    profile.spooler_name,
                    profile.driver_name,
                    profile.port_name,
                    profile.dpi,
                    str(profile.max_print_width_mm),
                    profile.max_print_width_dots,
                    profile.default_paper_profile_id,
                ),
            )

    def get(self, profile_id: str) -> PrinterProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM printer_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[PrinterProfile]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM printer_profiles ORDER BY display_name"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: object) -> PrinterProfile:
        return PrinterProfile(
            id=row["id"],
            display_name=row["display_name"],
            spooler_name=row["spooler_name"],
            driver_name=row["driver_name"],
            port_name=row["port_name"],
            dpi=int(row["dpi"]),
            max_print_width_mm=Decimal(row["max_print_width_mm"]),
            max_print_width_dots=int(row["max_print_width_dots"]),
            default_paper_profile_id=row["default_paper_profile_id"],
        )


class SqlitePaperProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, profile: PaperProfile) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO paper_profiles (
                    id, name, width_mm, dpi, printable_width_dots,
                    margin_left_dots, margin_right_dots, margin_top_dots, margin_bottom_dots,
                    media_tracking, length_mode, fixed_length_mm, orientation,
                    feed_after_print_mm, tear_offset_mm, horizontal_content_offset_dots
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    width_mm=excluded.width_mm,
                    dpi=excluded.dpi,
                    printable_width_dots=excluded.printable_width_dots,
                    margin_left_dots=excluded.margin_left_dots,
                    margin_right_dots=excluded.margin_right_dots,
                    margin_top_dots=excluded.margin_top_dots,
                    margin_bottom_dots=excluded.margin_bottom_dots,
                    media_tracking=excluded.media_tracking,
                    length_mode=excluded.length_mode,
                    fixed_length_mm=excluded.fixed_length_mm,
                    orientation=excluded.orientation,
                    feed_after_print_mm=excluded.feed_after_print_mm,
                    tear_offset_mm=excluded.tear_offset_mm,
                    horizontal_content_offset_dots=excluded.horizontal_content_offset_dots
                """,
                (
                    profile.id,
                    profile.name,
                    str(profile.width_mm),
                    profile.dpi,
                    profile.printable_width_dots,
                    profile.margin_left_dots,
                    profile.margin_right_dots,
                    profile.margin_top_dots,
                    profile.margin_bottom_dots,
                    profile.media_tracking.value,
                    profile.length_mode.value,
                    str(profile.fixed_length_mm) if profile.fixed_length_mm is not None else None,
                    profile.orientation.value,
                    str(profile.feed_after_print_mm),
                    str(profile.tear_offset_mm),
                    profile.horizontal_content_offset_dots,
                ),
            )

    def get(self, profile_id: str) -> PaperProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM paper_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[PaperProfile]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM paper_profiles ORDER BY CAST(width_mm AS REAL), name"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, profile_id: str) -> bool:
        with self._database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM paper_profiles WHERE id = ?", (profile_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _from_row(row: object) -> PaperProfile:
        return PaperProfile(
            id=row["id"],
            name=row["name"],
            width_mm=Decimal(row["width_mm"]),
            dpi=int(row["dpi"]),
            printable_width_dots=int(row["printable_width_dots"]),
            margin_left_dots=int(row["margin_left_dots"]),
            margin_right_dots=int(row["margin_right_dots"]),
            margin_top_dots=int(row["margin_top_dots"]),
            margin_bottom_dots=int(row["margin_bottom_dots"]),
            horizontal_content_offset_dots=int(row["horizontal_content_offset_dots"]),
            media_tracking=MediaTracking(row["media_tracking"]),
            length_mode=LengthMode(row["length_mode"]),
            fixed_length_mm=Decimal(row["fixed_length_mm"]) if row["fixed_length_mm"] else None,
            orientation=Orientation(row["orientation"]),
            feed_after_print_mm=Decimal(row["feed_after_print_mm"]),
            tear_offset_mm=Decimal(row["tear_offset_mm"]),
        )


class SqlitePrintJobRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, job: PrintJob) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO print_jobs (
                    id, created_at, updated_at, printer_profile_id, paper_profile_id,
                    template_id, source, source_reference, status, canvas_width, canvas_height,
                    bitmap_artifact_path, preview_artifact_path, encoded_artifact_path,
                    transport_job_id, error_code, error_summary, input_data_json, render_options_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    status=excluded.status,
                    canvas_width=excluded.canvas_width,
                    canvas_height=excluded.canvas_height,
                    bitmap_artifact_path=excluded.bitmap_artifact_path,
                    preview_artifact_path=excluded.preview_artifact_path,
                    encoded_artifact_path=excluded.encoded_artifact_path,
                    transport_job_id=excluded.transport_job_id,
                    error_code=excluded.error_code,
                    error_summary=excluded.error_summary,
                    input_data_json=excluded.input_data_json,
                    render_options_json=excluded.render_options_json
                """,
                (
                    job.id,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.printer_profile_id,
                    job.paper_profile_id,
                    job.template_id,
                    job.source,
                    job.source_reference,
                    job.status.value,
                    job.canvas_width,
                    job.canvas_height,
                    str(job.bitmap_artifact_path) if job.bitmap_artifact_path else None,
                    str(job.preview_artifact_path) if job.preview_artifact_path else None,
                    str(job.encoded_artifact_path) if job.encoded_artifact_path else None,
                    job.transport_job_id,
                    job.error_code,
                    job.error_summary,
                    _json(dict(job.input_data)),
                    _json(dict(job.render_options)),
                ),
            )

    def get(self, job_id: str) -> PrintJob | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM print_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return PrintJob(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            printer_profile_id=row["printer_profile_id"],
            paper_profile_id=row["paper_profile_id"],
            template_id=row["template_id"],
            source=row["source"],
            source_reference=row["source_reference"],
            status=PrintJobStatus(row["status"]),
            canvas_width=row["canvas_width"],
            canvas_height=row["canvas_height"],
            bitmap_artifact_path=_path(row["bitmap_artifact_path"]),
            preview_artifact_path=_path(row["preview_artifact_path"]),
            encoded_artifact_path=_path(row["encoded_artifact_path"]),
            transport_job_id=row["transport_job_id"],
            error_code=row["error_code"],
            error_summary=row["error_summary"],
            input_data=_mapping(row["input_data_json"]),
            render_options=_mapping(row["render_options_json"]),
        )

    def list_recent(self, limit: int = 100) -> list[PrintJob]:
        return self.list_filtered(limit=limit)

    def list_filtered(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        limit: int = 100,
    ) -> list[PrintJob]:
        clauses: list[str] = []
        parameters: list[object] = []
        if start_at is not None:
            clauses.append("created_at >= ?")
            parameters.append(start_at.isoformat())
        if end_at is not None:
            clauses.append("created_at <= ?")
            parameters.append(end_at.isoformat())
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            parameters.extend(statuses)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._database.connect() as connection:
            rows = connection.execute(
                f"SELECT id FROM print_jobs {where} ORDER BY created_at DESC LIMIT ?",
                (*parameters, max(1, limit)),
            ).fetchall()
        return [job for row in rows if (job := self.get(row["id"])) is not None]

    def delete(self, job_id: str) -> bool:
        with self._database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM print_jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def delete_many(self, job_ids: list[str]) -> int:
        if not job_ids:
            return 0
        placeholders = ",".join("?" for _ in job_ids)
        with self._database.connect() as connection, connection:
            cursor = connection.execute(
                f"DELETE FROM print_jobs WHERE id IN ({placeholders})", job_ids
            )
            return cursor.rowcount


class SqliteIntegrationProfileRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, profile: IntegrationProfile) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO integration_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider_type=excluded.provider_type,
                    display_name=excluded.display_name,
                    enabled=excluded.enabled,
                    credential_reference=excluded.credential_reference,
                    last_synced_at=excluded.last_synced_at,
                    last_sync_status=excluded.last_sync_status,
                    settings_json=excluded.settings_json
                """,
                (
                    profile.id,
                    profile.provider_type,
                    profile.display_name,
                    int(profile.enabled),
                    profile.credential_reference,
                    profile.last_synced_at.isoformat() if profile.last_synced_at else None,
                    profile.last_sync_status,
                    _json(dict(profile.settings_without_secrets)),
                ),
            )

    def get(self, profile_id: str) -> IntegrationProfile | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM integration_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        if row is None:
            return None
        return IntegrationProfile(
            id=row["id"],
            provider_type=row["provider_type"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            credential_reference=row["credential_reference"],
            last_synced_at=datetime.fromisoformat(row["last_synced_at"]) if row["last_synced_at"] else None,
            last_sync_status=row["last_sync_status"],
            settings_without_secrets=_mapping(row["settings_json"]),
        )


class SqliteTodoistCacheRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, entry: TodoistCacheEntry) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO todoist_cache VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    synced_at=excluded.synced_at
                """,
                (entry.cache_key, _json(dict(entry.payload)), entry.synced_at.isoformat()),
            )

    def get(self, cache_key: str) -> TodoistCacheEntry | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM todoist_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
        if row is None:
            return None
        return TodoistCacheEntry(
            cache_key=row["cache_key"],
            payload=_mapping(row["payload_json"]),
            synced_at=datetime.fromisoformat(row["synced_at"]),
        )


class SqlitePresetRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, preset: Preset) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO presets (
                    id, name, template_id, paper_profile_id,
                    input_data_json, render_options_json, pinned, created_at, updated_at,
                    printer_profile_id, integration_profile_id, filter_spec_json, sort_spec_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    template_id=excluded.template_id,
                    paper_profile_id=excluded.paper_profile_id,
                    input_data_json=excluded.input_data_json,
                    render_options_json=excluded.render_options_json,
                    pinned=excluded.pinned,
                    updated_at=excluded.updated_at,
                    printer_profile_id=excluded.printer_profile_id,
                    integration_profile_id=excluded.integration_profile_id,
                    filter_spec_json=excluded.filter_spec_json,
                    sort_spec_json=excluded.sort_spec_json
                """,
                (
                    preset.id,
                    preset.name,
                    preset.template_id,
                    preset.paper_profile_id,
                    _json(dict(preset.input_data)),
                    _json(dict(preset.render_options)),
                    int(preset.pinned),
                    preset.created_at.isoformat(),
                    preset.updated_at.isoformat(),
                    preset.printer_profile_id,
                    preset.integration_profile_id,
                    _json(preset.filter_spec),
                    _json(preset.sort_spec),
                ),
            )

    def get(self, preset_id: str) -> Preset | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT * FROM presets WHERE id = ?", (preset_id,)).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Preset]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM presets ORDER BY pinned DESC, updated_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, preset_id: str) -> bool:
        with self._database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _from_row(row: object) -> Preset:
        return Preset(
            id=row["id"],
            name=row["name"],
            template_id=row["template_id"],
            paper_profile_id=row["paper_profile_id"],
            printer_profile_id=row["printer_profile_id"],
            integration_profile_id=row["integration_profile_id"],
            filter_spec=_mapping(row["filter_spec_json"]),
            sort_spec=_mapping(row["sort_spec_json"]),
            input_data=_mapping(row["input_data_json"]),
            render_options=_mapping(row["render_options_json"]),
            pinned=bool(row["pinned"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SqliteCustomTemplateRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, template: CustomTemplate) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO custom_templates (
                    id, name, category, version, blocks_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    category=excluded.category,
                    version=excluded.version,
                    blocks_json=excluded.blocks_json,
                    updated_at=excluded.updated_at
                """,
                (
                    template.id,
                    template.name,
                    template.category,
                    template.version,
                    _json(list(template.blocks)),
                    template.created_at.isoformat(),
                    template.updated_at.isoformat(),
                ),
            )

    def get(self, template_id: str) -> CustomTemplate | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM custom_templates WHERE id = ?", (template_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[CustomTemplate]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM custom_templates ORDER BY updated_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, template_id: str) -> bool:
        with self._database.connect() as connection, connection:
            cursor = connection.execute("DELETE FROM custom_templates WHERE id = ?", (template_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _from_row(row: object) -> CustomTemplate:
        decoded = json.loads(row["blocks_json"] or "[]")
        blocks = tuple(item for item in decoded if isinstance(item, dict)) if isinstance(decoded, list) else ()
        return CustomTemplate(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            version=int(row["version"]),
            blocks=blocks,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SqliteSettingsRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def set(self, key: str, value: str) -> None:
        with self._database.connect() as connection, connection:
            connection.execute(
                """
                INSERT INTO app_settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value),
            )

    def get(self, key: str, default: str | None = None) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

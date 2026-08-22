from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from thermal_app.application.dto import RenderOptions, TransportReceipt
from thermal_app.application.services.print_service import PrintService
from thermal_app.config import AppPaths
from thermal_app.domain.enums import PrintJobStatus
from thermal_app.domain.profiles import default_paper_profiles, gc420t_profile
from thermal_app.infrastructure.artifacts.local_artifact_store import LocalArtifactStore
from thermal_app.infrastructure.encoders.zpl_gfa import ZplGfaEncoder
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import (
    SqlitePaperProfileRepository,
    SqlitePrinterProfileRepository,
    SqlitePrintJobRepository,
)
from thermal_app.rendering.test_page_renderer import TestPageRenderer


class FakeTransport:
    payload: bytes | None = None

    def is_available(self, printer: object) -> bool:
        return True

    def submit(self, printer: object, payload: bytes, document_name: str) -> TransportReceipt:
        self.payload = payload
        return TransportReceipt("77", datetime.now().astimezone(), True)

    def cancel(self, printer: object, transport_job_id: str) -> bool:
        return True


def test_prepare_and_submit_use_stored_zpl(
    tmp_path: Path,
    font_paths: tuple[Path, Path],
) -> None:
    paths = AppPaths.under(tmp_path / "data")
    paths.ensure()
    database = Database(paths.database)
    database.initialize()
    printers = SqlitePrinterProfileRepository(database)
    papers = SqlitePaperProfileRepository(database)
    jobs = SqlitePrintJobRepository(database)
    transport = FakeTransport()
    service = PrintService(
        TestPageRenderer(*font_paths, clock=lambda: datetime(2026, 8, 22, tzinfo=timezone.utc)),
        ZplGfaEncoder(),
        transport,
        LocalArtifactStore(paths),
        printers,
        papers,
        jobs,
    )
    printer = gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")
    paper = default_paper_profiles()[0]
    prepared = service.prepare_test_page(
        printer,
        paper,
        options=RenderOptions(visual_style="graphic"),
    )
    assert prepared.status is PrintJobStatus.READY
    assert prepared.preview_artifact_path and prepared.preview_artifact_path.is_file()
    assert prepared.encoded_artifact_path and prepared.encoded_artifact_path.is_file()
    assert prepared.render_options["visual_style"] == "graphic"

    submitted = service.submit(prepared.id)
    assert submitted.status is PrintJobStatus.SUBMITTED
    assert submitted.transport_job_id == "77"
    assert transport.payload == prepared.encoded_artifact_path.read_bytes()
    assert service.list_history()[0].id == submitted.id

    reprinted = service.reprint(submitted.id)
    assert reprinted.source == "reprint"
    assert reprinted.source_reference == submitted.id
    assert reprinted.input_data == submitted.input_data
    assert reprinted.render_options["visual_style"] == "graphic"
    assert service.cancel(reprinted.id) is True
    assert service.get_job(reprinted.id).status is PrintJobStatus.CANCELLED
    assert service.delete_history(reprinted.id) is True


def test_calibration_preview_does_not_persist_trial_offset(
    tmp_path: Path,
    font_paths: tuple[Path, Path],
) -> None:
    paths = AppPaths.under(tmp_path / "data")
    paths.ensure()
    database = Database(paths.database)
    database.initialize()
    printers = SqlitePrinterProfileRepository(database)
    papers = SqlitePaperProfileRepository(database)
    jobs = SqlitePrintJobRepository(database)
    paper = default_paper_profiles()[0]
    papers.save(paper)
    service = PrintService(
        TestPageRenderer(*font_paths),
        ZplGfaEncoder(),
        FakeTransport(),
        LocalArtifactStore(paths),
        printers,
        papers,
        jobs,
    )
    printer = gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")
    trial = replace(paper, horizontal_content_offset_dots=-8)
    service.prepare(
        printer,
        trial,
        "test.page",
        persist_paper_profile=False,
    )
    assert papers.get(paper.id) == paper


def test_filtered_history_delete_removes_artifacts_and_preserves_active_job(
    tmp_path: Path,
    font_paths: tuple[Path, Path],
) -> None:
    paths = AppPaths.under(tmp_path / "data")
    paths.ensure()
    database = Database(paths.database)
    database.initialize()
    printers = SqlitePrinterProfileRepository(database)
    papers = SqlitePaperProfileRepository(database)
    jobs = SqlitePrintJobRepository(database)
    service = PrintService(
        TestPageRenderer(*font_paths),
        ZplGfaEncoder(),
        FakeTransport(),
        LocalArtifactStore(paths),
        printers,
        papers,
        jobs,
    )
    printer = gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")
    paper = default_paper_profiles()[0]
    prepared = service.prepare_test_page(printer, paper)
    assert prepared.preview_artifact_path and prepared.preview_artifact_path.exists()
    result = service.delete_history_filtered(statuses=(PrintJobStatus.READY,))
    assert result.deleted_jobs == 1
    assert result.deleted_artifacts == 3
    assert not prepared.preview_artifact_path.exists()
    assert service.get_job(prepared.id) is None

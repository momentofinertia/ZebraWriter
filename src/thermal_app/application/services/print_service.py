from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from thermal_app.application.dto import RenderOptions
from thermal_app.application.ports.printing import PrintEncoder, PrintTransport
from thermal_app.application.ports.rendering import Renderer
from thermal_app.application.ports.storage import (
    ArtifactStore,
    PaperProfileRepository,
    PrinterProfileRepository,
    PrintJobRepository,
)
from thermal_app.domain.enums import PrintJobStatus
from thermal_app.domain.errors import PrinterUnavailableError
from thermal_app.domain.models import PaperProfile, PrinterProfile, PrintJob, TemplateDefinition, validate_paper_for_printer
from thermal_app.application.template_catalog import TemplateCatalog, built_in_definitions


TEST_PAGE_TEMPLATE = TemplateDefinition(
    id="test.page",
    version=1,
    name="GC420t Test Sayfası",
    category="System",
    input_schema={},
    default_settings={},
    renderer_key="test-page",
)


@dataclass(frozen=True, slots=True)
class HistoryDeletionResult:
    deleted_jobs: int
    deleted_artifacts: int
    skipped_active_jobs: int


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


class PrintService:
    def __init__(
        self,
        renderer: Renderer,
        encoder: PrintEncoder,
        transport: PrintTransport,
        artifacts: ArtifactStore,
        printer_profiles: PrinterProfileRepository,
        paper_profiles: PaperProfileRepository,
        jobs: PrintJobRepository,
        template_catalog: TemplateCatalog | None = None,
    ) -> None:
        self._renderer = renderer
        self._encoder = encoder
        self._transport = transport
        self._artifacts = artifacts
        self._printer_profiles = printer_profiles
        self._paper_profiles = paper_profiles
        self._jobs = jobs
        self._templates = template_catalog or TemplateCatalog(built_in_definitions())

    def prepare_test_page(
        self,
        printer: PrinterProfile,
        paper: PaperProfile,
        *,
        data: Mapping[str, object] | None = None,
        options: RenderOptions | None = None,
    ) -> PrintJob:
        return self.prepare(
            printer,
            paper,
            TEST_PAGE_TEMPLATE.id,
            data=data,
            options=options,
            source="manual-test-page",
        )

    def prepare(
        self,
        printer: PrinterProfile,
        paper: PaperProfile,
        template_id: str,
        *,
        data: Mapping[str, object] | None = None,
        options: RenderOptions | None = None,
        source: str = "manual-template",
        source_reference: str | None = None,
        persist_paper_profile: bool = True,
    ) -> PrintJob:
        validate_paper_for_printer(paper, printer)
        template = TEST_PAGE_TEMPLATE if template_id == TEST_PAGE_TEMPLATE.id else self._templates.get(template_id)
        self._printer_profiles.save(printer)
        if persist_paper_profile:
            self._paper_profiles.save(paper)
        now = datetime.now().astimezone()
        render_options = options or RenderOptions()
        stored_input = _json_safe(dict(data or {}))
        assert isinstance(stored_input, dict)
        job = PrintJob(
            id=str(uuid4()),
            created_at=now,
            updated_at=now,
            printer_profile_id=printer.id,
            paper_profile_id=paper.id,
            template_id=template.id,
            source=source,
            source_reference=source_reference,
            input_data=stored_input,
            render_options=asdict(render_options),
        )
        self._jobs.save(job)
        try:
            job.transition_to(PrintJobStatus.RENDERING)
            self._jobs.save(job)
            render_data = dict(data or {})
            if template.id == TEST_PAGE_TEMPLATE.id:
                render_data = {"spooler_name": printer.spooler_name, **render_data}
            document = self._renderer.render(
                template,
                render_data,
                paper,
                render_options,
            )
            payload = self._encoder.encode(document, printer, paper)
            job.canvas_width = document.width_dots
            job.canvas_height = document.height_dots
            job.bitmap_artifact_path = self._artifacts.save_bitmap(job.id, document)
            job.preview_artifact_path = self._artifacts.save_preview(job.id, document)
            job.encoded_artifact_path = self._artifacts.save_encoded(job.id, payload)
            job.transition_to(PrintJobStatus.READY)
            self._jobs.save(job)
            return job
        except Exception as exc:
            if job.status is PrintJobStatus.RENDERING:
                job.error_code = type(exc).__name__
                job.error_summary = str(exc)
                job.transition_to(PrintJobStatus.FAILED)
                self._jobs.save(job)
            raise

    def get_job(self, job_id: str) -> PrintJob | None:
        return self._jobs.get(job_id)

    def list_history(
        self,
        limit: int = 100,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        statuses: tuple[PrintJobStatus, ...] | None = None,
    ) -> list[PrintJob]:
        status_values = tuple(status.value for status in statuses) if statuses else None
        return self._jobs.list_filtered(start_at, end_at, status_values, limit)

    def delete_history(self, job_id: str) -> bool:
        result = self.delete_history_filtered(job_ids=[job_id])
        return result.deleted_jobs == 1

    def delete_history_filtered(
        self,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        statuses: tuple[PrintJobStatus, ...] | None = None,
        job_ids: list[str] | None = None,
    ) -> HistoryDeletionResult:
        jobs = (
            [job for job_id in (job_ids or []) if (job := self._jobs.get(job_id)) is not None]
            if job_ids is not None
            else self.list_history(limit=100000, start_at=start_at, end_at=end_at, statuses=statuses)
        )
        active = {PrintJobStatus.CREATED, PrintJobStatus.RENDERING, PrintJobStatus.SUBMITTING}
        deletable = [job for job in jobs if job.status not in active]
        skipped = len(jobs) - len(deletable)
        artifact_paths = [
            path
            for job in deletable
            for path in (job.bitmap_artifact_path, job.preview_artifact_path, job.encoded_artifact_path)
            if path is not None
        ]
        deleted_artifacts = self._artifacts.delete_paths(artifact_paths)
        deleted_jobs = self._jobs.delete_many([job.id for job in deletable])
        return HistoryDeletionResult(deleted_jobs, deleted_artifacts, skipped)

    def reprint(self, job_id: str) -> PrintJob:
        original = self._jobs.get(job_id)
        if original is None:
            raise KeyError(f"Baskı işi bulunamadı: {job_id}")
        printer = self._printer_profiles.get(original.printer_profile_id)
        paper = self._paper_profiles.get(original.paper_profile_id)
        if printer is None or paper is None:
            raise KeyError("Tekrar baskı için yazıcı veya kağıt profili bulunamadı.")
        option_names = RenderOptions.__dataclass_fields__.keys()
        options = RenderOptions(
            **{key: value for key, value in original.render_options.items() if key in option_names}
        )
        prepared = self.prepare(
            printer,
            paper,
            original.template_id,
            data=original.input_data,
            options=options,
            source="reprint",
            source_reference=original.id,
        )
        return self.submit(prepared.id)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or not job.transport_job_id:
            return False
        printer = self._printer_profiles.get(job.printer_profile_id)
        if printer is None or not self._transport.cancel(printer, job.transport_job_id):
            return False
        if job.status is PrintJobStatus.SUBMITTED:
            job.transition_to(PrintJobStatus.CANCELLED)
            self._jobs.save(job)
        return True

    def submit(self, job_id: str) -> PrintJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Baskı işi bulunamadı: {job_id}")
        if job.encoded_artifact_path is None:
            raise ValueError("Baskı işinin hazır encoded artefaktı yok.")
        printer = self._printer_profiles.get(job.printer_profile_id)
        if printer is None:
            raise KeyError("Baskı işinin GC420t profili bulunamadı.")
        if not self._transport.is_available(printer):
            raise PrinterUnavailableError("Zebra GC420t yazıcı kuyruğuna erişilemiyor.")

        job.transition_to(PrintJobStatus.SUBMITTING)
        self._jobs.save(job)
        try:
            payload = self._artifacts.read_encoded(job.encoded_artifact_path)
            receipt = self._transport.submit(printer, payload, f"ZebraWriter — {job.template_id}")
            job.transport_job_id = receipt.transport_job_id
            job.transition_to(PrintJobStatus.SUBMITTED)
            self._jobs.save(job)
            return job
        except Exception as exc:
            job.error_code = type(exc).__name__
            job.error_summary = str(exc)
            job.transition_to(PrintJobStatus.FAILED)
            self._jobs.save(job)
            raise

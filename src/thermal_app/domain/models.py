from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from thermal_app.domain.enums import LengthMode, MediaTracking, Orientation, PrintJobStatus
from thermal_app.domain.errors import InvalidJobTransitionError, InvalidPaperProfileError
from thermal_app.domain.measurements import mm_to_dots


GC420T_DPI = 203
GC420T_MAX_WIDTH_MM = Decimal("104")
GC420T_MAX_WIDTH_DOTS = 832
CALIBRATION_OFFSET_LIMIT_DOTS = 200


@dataclass(frozen=True, slots=True)
class PrinterProfile:
    id: str
    display_name: str
    spooler_name: str
    driver_name: str
    port_name: str
    dpi: int = GC420T_DPI
    max_print_width_mm: Decimal = GC420T_MAX_WIDTH_MM
    max_print_width_dots: int = GC420T_MAX_WIDTH_DOTS
    default_paper_profile_id: str | None = "paper-56mm"

    def __post_init__(self) -> None:
        if not self.spooler_name.strip():
            raise ValueError("Windows yazıcı kuyruğu adı boş olamaz.")
        if self.dpi != GC420T_DPI:
            raise ValueError("GC420t profili 203 DPI olmalıdır.")
        if self.max_print_width_dots <= 0 or self.max_print_width_mm <= 0:
            raise ValueError("Yazıcı maksimum genişliği pozitif olmalıdır.")


@dataclass(frozen=True, slots=True)
class PaperProfile:
    id: str
    name: str
    width_mm: Decimal
    dpi: int
    printable_width_dots: int
    margin_left_dots: int
    margin_right_dots: int
    margin_top_dots: int
    margin_bottom_dots: int
    horizontal_content_offset_dots: int = 0
    media_tracking: MediaTracking = MediaTracking.CONTINUOUS
    length_mode: LengthMode = LengthMode.CONTINUOUS
    fixed_length_mm: Decimal | None = None
    orientation: Orientation = Orientation.PORTRAIT
    feed_after_print_mm: Decimal = Decimal("0")
    tear_offset_mm: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidPaperProfileError("Kağıt profili adı boş olamaz.")
        if self.width_mm <= 0 or self.dpi <= 0 or self.printable_width_dots <= 0:
            raise InvalidPaperProfileError("Kağıt ölçüleri pozitif olmalıdır.")
        margins = (
            self.margin_left_dots,
            self.margin_right_dots,
            self.margin_top_dots,
            self.margin_bottom_dots,
        )
        if any(value < 0 for value in margins):
            raise InvalidPaperProfileError("Kağıt marjları negatif olamaz.")
        if self.printable_width_dots + self.margin_left_dots + self.margin_right_dots > self.physical_width_dots:
            raise InvalidPaperProfileError("Printable width ve yatay marjlar fiziksel genişliği aşıyor.")
        if abs(self.horizontal_content_offset_dots) > CALIBRATION_OFFSET_LIMIT_DOTS:
            raise InvalidPaperProfileError(
                f"Yatay kalibrasyon ofseti -{CALIBRATION_OFFSET_LIMIT_DOTS} ile "
                f"+{CALIBRATION_OFFSET_LIMIT_DOTS} dot arasında olmalıdır."
            )
        if self.length_mode is LengthMode.FIXED and (self.fixed_length_mm is None or self.fixed_length_mm <= 0):
            raise InvalidPaperProfileError("Sabit uzunluk modunda pozitif uzunluk zorunludur.")
        if self.length_mode is LengthMode.CONTINUOUS and self.fixed_length_mm is not None:
            raise InvalidPaperProfileError("Continuous profilde sabit uzunluk bulunamaz.")
        if self.feed_after_print_mm < 0:
            raise InvalidPaperProfileError("Baskı sonrası ilerletme negatif olamaz.")

    @property
    def physical_width_dots(self) -> int:
        return mm_to_dots(self.width_mm, self.dpi)


@dataclass(slots=True)
class PrintJob:
    id: str
    created_at: datetime
    updated_at: datetime
    printer_profile_id: str
    paper_profile_id: str
    template_id: str
    source: str
    source_reference: str | None = None
    status: PrintJobStatus = PrintJobStatus.CREATED
    canvas_width: int | None = None
    canvas_height: int | None = None
    bitmap_artifact_path: Path | None = None
    preview_artifact_path: Path | None = None
    encoded_artifact_path: Path | None = None
    transport_job_id: str | None = None
    error_code: str | None = None
    error_summary: str | None = None
    input_data: Mapping[str, object] = field(default_factory=dict)
    render_options: Mapping[str, object] = field(default_factory=dict)

    def transition_to(self, target: PrintJobStatus, *, now: datetime | None = None) -> None:
        allowed = {
            PrintJobStatus.CREATED: {PrintJobStatus.RENDERING, PrintJobStatus.CANCELLED},
            PrintJobStatus.RENDERING: {PrintJobStatus.READY, PrintJobStatus.FAILED, PrintJobStatus.CANCELLED},
            PrintJobStatus.READY: {PrintJobStatus.SUBMITTING, PrintJobStatus.CANCELLED},
            PrintJobStatus.SUBMITTING: {PrintJobStatus.SUBMITTED, PrintJobStatus.FAILED},
            PrintJobStatus.SUBMITTED: {PrintJobStatus.CANCELLED},
            PrintJobStatus.FAILED: set(),
            PrintJobStatus.CANCELLED: set(),
        }
        if target not in allowed[self.status]:
            raise InvalidJobTransitionError(f"Geçersiz baskı işi geçişi: {self.status} → {target}")
        self.status = target
        self.updated_at = now or datetime.now().astimezone()


@dataclass(frozen=True, slots=True)
class TemplateDefinition:
    id: str
    version: int
    name: str
    category: str
    input_schema: Mapping[str, object]
    default_settings: Mapping[str, object]
    renderer_key: str


@dataclass(frozen=True, slots=True)
class CustomTemplate:
    id: str
    name: str
    category: str
    blocks: tuple[Mapping[str, object], ...]
    created_at: datetime
    updated_at: datetime
    version: int = 1


@dataclass(frozen=True, slots=True)
class TaskItem:
    id: str
    title: str
    description: str | None
    completed: bool
    priority: int
    due_date: str | None
    due_time: str | None
    project: str | None
    labels: tuple[str, ...]
    source: str
    source_id: str


@dataclass(frozen=True, slots=True)
class IntegrationProfile:
    id: str
    provider_type: str
    display_name: str
    enabled: bool
    credential_reference: str | None
    last_synced_at: datetime | None
    last_sync_status: str | None
    settings_without_secrets: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class TodoistCacheEntry:
    cache_key: str
    payload: Mapping[str, object]
    synced_at: datetime


@dataclass(frozen=True, slots=True)
class Preset:
    id: str
    name: str
    template_id: str
    paper_profile_id: str
    printer_profile_id: str | None
    integration_profile_id: str | None
    filter_spec: Mapping[str, object]
    sort_spec: Mapping[str, object]
    input_data: Mapping[str, object]
    render_options: Mapping[str, object]
    pinned: bool
    created_at: datetime
    updated_at: datetime


def validate_paper_for_printer(paper: PaperProfile, printer: PrinterProfile) -> None:
    if paper.dpi != printer.dpi:
        raise InvalidPaperProfileError("Kağıt profili DPI değeri GC420t ile eşleşmiyor.")
    if paper.physical_width_dots > printer.max_print_width_dots:
        raise InvalidPaperProfileError("Kağıt genişliği GC420t maksimum baskı genişliğini aşıyor.")
    if paper.orientation is not Orientation.PORTRAIT:
        raise InvalidPaperProfileError("Faz 2 yalnızca portrait yönünü destekler.")

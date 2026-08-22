from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from thermal_app.domain.models import TaskItem


@dataclass(frozen=True, slots=True)
class RenderOptions:
    brightness: float = 1.0
    contrast: float = 1.0
    threshold: int = 160
    dithering: str = "threshold"
    sharpen: bool = False
    invert: bool = False
    visual_style: str = "plain"

    def __post_init__(self) -> None:
        if self.visual_style not in {"plain", "graphic"}:
            raise ValueError("Görsel stil plain veya graphic olmalıdır.")


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    width_dots: int
    height_dots: int
    bytes_per_row: int
    bitmap_1bpp: bytes

    def __post_init__(self) -> None:
        expected = self.bytes_per_row * self.height_dots
        if self.width_dots <= 0 or self.height_dots <= 0 or self.bytes_per_row != (self.width_dots + 7) // 8:
            raise ValueError("Geçersiz raster belge ölçüsü.")
        if len(self.bitmap_1bpp) != expected:
            raise ValueError("Raster bitmap uzunluğu belge ölçüsüyle eşleşmiyor.")


@dataclass(frozen=True, slots=True)
class EncodedPayload:
    content: bytes
    media_type: str
    suggested_extension: str
    metadata: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class TransportReceipt:
    transport_job_id: str
    accepted_at: datetime
    accepted_by_queue: bool


@dataclass(frozen=True, slots=True)
class TodoistSyncResult:
    tasks: tuple[TaskItem, ...]
    projects: Mapping[str, str]
    synced_at: datetime
    stale: bool
    source: str
    warning: str | None = None

from __future__ import annotations

from typing import Protocol

from thermal_app.application.dto import EncodedPayload, RenderedDocument, TransportReceipt
from thermal_app.domain.models import PaperProfile, PrinterProfile


class PrinterDiscovery(Protocol):
    def discover(self) -> list[PrinterProfile]: ...


class PrintTransport(Protocol):
    def is_available(self, printer: PrinterProfile) -> bool: ...

    def submit(self, printer: PrinterProfile, payload: bytes, document_name: str) -> TransportReceipt: ...

    def cancel(self, printer: PrinterProfile, transport_job_id: str) -> bool: ...


class PrintEncoder(Protocol):
    def encode(
        self,
        document: RenderedDocument,
        printer: PrinterProfile,
        paper: PaperProfile,
    ) -> EncodedPayload: ...

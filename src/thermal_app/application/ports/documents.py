from __future__ import annotations

from pathlib import Path
from typing import Protocol

from thermal_app.application.services.document_import_service import ImportedDocument


class DocumentImporter(Protocol):
    def import_document(self, path: Path) -> ImportedDocument: ...

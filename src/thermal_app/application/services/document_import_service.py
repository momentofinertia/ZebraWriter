from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol

from thermal_app.domain.errors import DocumentImportError


@dataclass(frozen=True, slots=True)
class ImportedDocument:
    title: str
    source_format: str
    blocks: tuple[Mapping[str, object], ...]
    warnings: tuple[str, ...] = ()


class DocumentFormatImporter(Protocol):
    def import_document(self, path: Path) -> ImportedDocument: ...


class DocumentImportService:
    def __init__(self, importers: Mapping[str, DocumentFormatImporter]) -> None:
        self._importers = {key.lower().lstrip("."): value for key, value in importers.items()}

    def import_document(self, path: Path) -> ImportedDocument:
        if not path.exists() or not path.is_file():
            raise DocumentImportError("Belge dosyası bulunamadı.")
        extension = path.suffix.lower().lstrip(".")
        importer = self._importers.get(extension)
        if importer is None:
            raise DocumentImportError("Yalnızca PDF, EPUB ve DOCX dosyaları destekleniyor.")
        try:
            return importer.import_document(path)
        except DocumentImportError:
            raise
        except Exception as exc:
            raise DocumentImportError(f"{path.name} okunamadı: {exc}") from exc

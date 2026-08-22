from __future__ import annotations

from pathlib import Path, PurePosixPath
import posixpath
import re
from typing import Iterable
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from thermal_app.application.services.document_import_service import ImportedDocument
from thermal_app.domain.errors import DocumentImportError


_WS = re.compile(r"\s+")
_BULLET = re.compile(r"^(?:[-*•‣▪◦]|\d+[.)])\s+(.*)$")


def _clean(value: str) -> str:
    return _WS.sub(" ", value.replace("\u00a0", " ")).strip()


def _looks_like_heading(value: str) -> bool:
    if len(value) > 90 or value.endswith((".", ":", ";", ",")):
        return False
    words = value.split()
    return bool(value.isupper() or (len(words) <= 8 and value[:1].isupper()))


def _line_blocks(lines: Iterable[str]) -> tuple[dict[str, object], ...]:
    blocks: list[dict[str, object]] = []
    for raw in lines:
        value = _clean(raw)
        if not value:
            continue
        bullet = _BULLET.match(value)
        if bullet:
            blocks.append({"type": "checklist", "label": _clean(bullet.group(1)), "checked": False})
        elif _looks_like_heading(value):
            blocks.append({"type": "heading", "value": value})
        else:
            blocks.append({"type": "text", "value": value})
    return tuple(blocks)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class PdfDocumentImporter:
    def import_document(self, path: Path) -> ImportedDocument:
        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise DocumentImportError(f"PDF okunamadı: {path.name}") from exc
        lines = [line for page in pages for line in page.splitlines()]
        blocks = _line_blocks(lines)
        if not blocks:
            raise DocumentImportError(
                "PDF içinde seçilebilir metin bulunamadı. Taranmış PDF için OCR desteği henüz yok."
            )
        return ImportedDocument(path.stem, "pdf", blocks)


class EpubDocumentImporter:
    def import_document(self, path: Path) -> ImportedDocument:
        try:
            with ZipFile(path) as archive:
                container = ET.fromstring(archive.read("META-INF/container.xml"))
                rootfile = next(
                    element for element in container.iter() if _local(element.tag) == "rootfile"
                ).attrib["full-path"]
                opf = ET.fromstring(archive.read(rootfile))
                root_dir = str(PurePosixPath(rootfile).parent)
                manifest = {
                    item.attrib["id"]: item.attrib["href"]
                    for item in opf.iter()
                    if _local(item.tag) == "item" and item.attrib.get("media-type", "").startswith("application/xhtml")
                }
                spine = [item.attrib["idref"] for item in opf.iter() if _local(item.tag) == "itemref"]
                title = next(
                    (_clean(element.text or "") for element in opf.iter() if _local(element.tag) == "title"),
                    path.stem,
                ) or path.stem
                blocks: list[dict[str, object]] = []
                warnings: list[str] = []
                for item_id in spine:
                    href = manifest.get(item_id)
                    if not href:
                        continue
                    member = posixpath.normpath(posixpath.join(root_dir, href.split("#", 1)[0]))
                    content = archive.read(member)
                    blocks.extend(_xhtml_blocks(content))
                    if b"<img" in content.lower() or b":img" in content.lower():
                        warnings.append("EPUB görselleri aktarılmadı.")
        except (BadZipFile, KeyError, ET.ParseError, StopIteration) as exc:
            raise DocumentImportError(f"EPUB yapısı okunamadı: {path.name}") from exc
        if not blocks:
            raise DocumentImportError("EPUB içinde aktarılabilir metin bulunamadı.")
        return ImportedDocument(title, "epub", tuple(blocks), tuple(dict.fromkeys(warnings)))


def _xhtml_blocks(content: bytes) -> list[dict[str, object]]:
    root = ET.fromstring(content)
    blocks: list[dict[str, object]] = []
    for element in root.iter():
        tag = _local(element.tag)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            value = _clean(" ".join(element.itertext()))
            if value:
                blocks.append({"type": "heading", "value": value})
        elif tag == "li":
            value = _clean(" ".join(element.itertext()))
            if value:
                blocks.append({"type": "checklist", "label": value, "checked": False})
        elif tag in {"p", "blockquote", "pre"}:
            value = _clean(" ".join(element.itertext()))
            if value:
                blocks.append({"type": "text", "value": value})
    return blocks


class DocxDocumentImporter:
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def import_document(self, path: Path) -> ImportedDocument:
        try:
            with ZipFile(path) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
        except (BadZipFile, KeyError, ET.ParseError) as exc:
            raise DocumentImportError(f"DOCX yapısı okunamadı: {path.name}") from exc
        blocks: list[dict[str, object]] = []
        warnings: list[str] = []
        body = next((element for element in document.iter() if _local(element.tag) == "body"), None)
        if body is None:
            raise DocumentImportError("DOCX gövdesi bulunamadı.")
        for child in body:
            tag = _local(child.tag)
            if any(_local(element.tag) in {"drawing", "pict"} for element in child.iter()):
                warnings.append("DOCX görselleri aktarılmadı.")
            if tag == "p":
                value = _clean("".join(element.text or "" for element in child.iter() if _local(element.tag) == "t"))
                if not value:
                    continue
                style = next(
                    (element.attrib.get(self.W + "val", "") for element in child.iter() if _local(element.tag) == "pStyle"),
                    "",
                )
                is_list = any(_local(element.tag) == "numPr" for element in child.iter())
                if is_list:
                    blocks.append({"type": "checklist", "label": value, "checked": False})
                elif "heading" in style.lower():
                    blocks.append({"type": "heading", "value": value})
                else:
                    blocks.append({"type": "text", "value": value})
            elif tag == "tbl":
                for row in (element for element in child.iter() if _local(element.tag) == "tr"):
                    cells = []
                    for cell in (element for element in row.iter() if _local(element.tag) == "tc"):
                        cells.append(_clean(" ".join(element.text or "" for element in cell.iter() if _local(element.tag) == "t")))
                    value = " | ".join(cell for cell in cells if cell)
                    if value:
                        blocks.append({"type": "text", "value": value})
        if not blocks:
            raise DocumentImportError("DOCX içinde aktarılabilir metin bulunamadı.")
        return ImportedDocument(path.stem, "docx", tuple(blocks), tuple(dict.fromkeys(warnings)))

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from thermal_app.domain.errors import DocumentImportError
from thermal_app.infrastructure.document_importers import (
    DocxDocumentImporter,
    EpubDocumentImporter,
    PdfDocumentImporter,
)


def test_epub_import_preserves_spine_and_blocks(tmp_path: Path) -> None:
    path = tmp_path / "kitap.epub"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
        )
        archive.writestr(
            "OEBPS/content.opf",
            '<package><metadata><title>Türkçe Kitap</title></metadata>'
            '<manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/>'
            '<item id="two" href="two.xhtml" media-type="application/xhtml+xml"/></manifest>'
            '<spine><itemref idref="one"/><itemref idref="two"/></spine></package>',
        )
        archive.writestr("OEBPS/one.xhtml", "<html><body><h1>Birinci</h1><p>İlk bölüm.</p></body></html>")
        archive.writestr("OEBPS/two.xhtml", "<html><body><h2>İkinci</h2><ul><li>Madde</li></ul></body></html>")
    result = EpubDocumentImporter().import_document(path)
    assert result.title == "Türkçe Kitap"
    assert [block["value"] for block in result.blocks if block["type"] == "heading"] == ["Birinci", "İkinci"]
    assert any(block["type"] == "checklist" for block in result.blocks)


def test_docx_import_reads_headings_paragraphs_and_tables(tmp_path: Path) -> None:
    path = tmp_path / "notlar.docx"
    document = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Başlık</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Türkçe metin</w:t></w:r></w:p>'
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Ürün</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>Miktar</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
        '</w:body></w:document>'
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)
    result = DocxDocumentImporter().import_document(path)
    assert result.blocks[0] == {"type": "heading", "value": "Başlık"}
    assert result.blocks[1] == {"type": "text", "value": "Türkçe metin"}
    assert result.blocks[2]["value"] == "Ürün | Miktar"


def test_empty_pdf_reports_ocr_boundary(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    path = tmp_path / "tarama.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with path.open("wb") as handle:
        writer.write(handle)
    with pytest.raises(DocumentImportError, match="OCR"):
        PdfDocumentImporter().import_document(path)

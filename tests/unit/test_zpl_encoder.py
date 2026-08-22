import pytest

from thermal_app.application.dto import RenderedDocument
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.infrastructure.encoders.zpl_gfa import ZplGfaEncoder


def test_zpl_uses_dynamic_width_height_and_gfa(printer: object, paper_56: object) -> None:
    document = RenderedDocument(
        width_dots=448,
        height_dots=2,
        bytes_per_row=56,
        bitmap_1bpp=bytes([0xAA] * 112),
    )
    payload = ZplGfaEncoder().encode(document, printer, paper_56)
    text = payload.content.decode("ascii")
    assert text.startswith("^XA\n")
    assert "^PW448\n" in text
    assert "^LL2\n" in text
    assert "^GFA,112,112,56," in text
    assert text.endswith("^XZ\n")


def test_rendered_document_requires_padded_row_width() -> None:
    document = RenderedDocument(9, 1, 2, bytes([0x80, 0x00]))
    assert document.bytes_per_row == 2


@pytest.mark.parametrize("profile_index", [0, 2, 3])
def test_zpl_width_follows_56_58_and_80mm_profiles(printer: object, profile_index: int) -> None:
    paper = default_paper_profiles()[profile_index]
    row_bytes = (paper.physical_width_dots + 7) // 8
    document = RenderedDocument(
        paper.physical_width_dots,
        1,
        row_bytes,
        bytes(row_bytes),
    )
    text = ZplGfaEncoder().encode(document, printer, paper).content.decode("ascii")
    assert f"^PW{paper.physical_width_dots}\n" in text

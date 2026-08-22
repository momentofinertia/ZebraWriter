from __future__ import annotations

from thermal_app.application.dto import EncodedPayload, RenderedDocument
from thermal_app.domain.models import PaperProfile, PrinterProfile, validate_paper_for_printer


class ZplGfaEncoder:
    def encode(
        self,
        document: RenderedDocument,
        printer: PrinterProfile,
        paper: PaperProfile,
    ) -> EncodedPayload:
        validate_paper_for_printer(paper, printer)
        if document.width_dots != paper.physical_width_dots:
            raise ValueError("Raster genişliği seçili fiziksel kağıt genişliği ile eşleşmiyor.")
        total_bytes = len(document.bitmap_1bpp)
        hexadecimal = document.bitmap_1bpp.hex().upper()
        zpl = (
            f"^XA\n"
            f"^PW{document.width_dots}\n"
            f"^LL{document.height_dots}\n"
            "^LH0,0\n"
            "^FO0,0\n"
            f"^GFA,{total_bytes},{total_bytes},{document.bytes_per_row},{hexadecimal}\n"
            "^XZ\n"
        ).encode("ascii")
        return EncodedPayload(
            content=zpl,
            media_type="application/zpl",
            suggested_extension="zpl",
            metadata={
                "width_dots": str(document.width_dots),
                "height_dots": str(document.height_dots),
                "bytes_per_row": str(document.bytes_per_row),
            },
        )

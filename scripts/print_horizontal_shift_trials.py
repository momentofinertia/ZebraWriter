from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from thermal_app.application.dto import RenderedDocument
from thermal_app.config import project_root
from thermal_app.domain.profiles import default_paper_profiles
from thermal_app.infrastructure.encoders.zpl_gfa import ZplGfaEncoder
from thermal_app.infrastructure.printers.windows_discovery import WindowsPrinterDiscovery
from thermal_app.infrastructure.printers.windows_raw_transport import WindowsRawTransport
from thermal_app.rendering.test_page_renderer import pack_black_bits


TRIALS = (("A", 0), ("B", -8), ("C", -16))


def parse_trials(value: str) -> tuple[tuple[str, int], ...]:
    trials: list[tuple[str, int]] = []
    for item in value.split(","):
        name, shift = item.split(":", 1)
        trials.append((name.strip(), int(shift.strip())))
    return tuple(trials)


def render_trial(
    name: str,
    shift_dots: int,
    width: int,
    home_x: int = 0,
    raster_left: bool = False,
) -> RenderedDocument:
    image = Image.new("1", (width, 180), 1)
    draw = ImageDraw.Draw(image)
    font_root = project_root() / "assets" / "fonts"
    title = ImageFont.truetype(str(font_root / "VeraBd.ttf"), 28)
    body = ImageFont.truetype(str(font_root / "Vera.ttf"), 18)
    label = (
        f"{name}: RASTER LEFT {shift_dots}"
        if raster_left
        else f"{name}: ^LH {home_x} / ^LS {shift_dots}"
    )
    box = draw.textbbox((0, 0), label, font=title)
    draw.text(((width - (box[2] - box[0])) // 2, 12), label, font=title, fill=0)
    draw.rectangle((0, 58, width - 1, 150), outline=0, width=2)
    draw.line((0, 58, width - 1, 150), fill=0, width=1)
    draw.line((width - 1, 58, 0, 150), fill=0, width=1)
    draw.text((5, 155), "LEFT", font=body, fill=0)
    center = "CENTER"
    center_box = draw.textbbox((0, 0), center, font=body)
    draw.text(((width - (center_box[2] - center_box[0])) // 2, 155), center, font=body, fill=0)
    right = "RIGHT"
    right_box = draw.textbbox((0, 0), right, font=body)
    draw.text((width - (right_box[2] - right_box[0]) - 5, 155), right, font=body, fill=0)
    if raster_left and shift_dots:
        shifted_image = Image.new("1", image.size, 1)
        shifted_image.paste(image, (-shift_dots, 0))
        image = shifted_image
    row_bytes, bitmap = pack_black_bits(image)
    return RenderedDocument(width, image.height, row_bytes, bitmap)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trials",
        type=parse_trials,
        default=TRIALS,
        help="Virgulle ayrilmis ETIKET:DOT degerleri (ornegin M:40,N:44,O:48)",
    )
    parser.add_argument("--home-x", type=int, default=0)
    parser.add_argument("--raster-left", action="store_true")
    args = parser.parse_args()
    printers = WindowsPrinterDiscovery().discover()
    if len(printers) != 1:
        raise RuntimeError(f"Bir GC420t bekleniyordu; bulunan: {len(printers)}")
    printer = printers[0]
    paper = default_paper_profiles()[0]
    encoder = ZplGfaEncoder()
    transport = WindowsRawTransport()
    results: list[tuple[str, int, str]] = []
    for name, shift in args.trials:
        document = render_trial(
            name,
            shift,
            paper.printable_width_dots,
            args.home_x,
            args.raster_left,
        )
        payload = encoder.encode(document, printer, paper).content
        label_shift = 0 if args.raster_left else shift
        shifted = payload.replace(
            b"^LH0,0\n",
            f"^LH{args.home_x},0\n^LS{label_shift}\n".encode("ascii"),
            1,
        )
        receipt = transport.submit(printer, shifted, f"ZebraWriter Horizontal Shift {name}")
        results.append((name, shift, receipt.transport_job_id))
    print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

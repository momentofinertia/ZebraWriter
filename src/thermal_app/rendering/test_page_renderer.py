from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from thermal_app.application.dto import RenderedDocument, RenderOptions
from thermal_app.domain.enums import LengthMode
from thermal_app.domain.errors import RenderingError
from thermal_app.domain.measurements import mm_to_dots
from thermal_app.domain.models import PaperProfile, TemplateDefinition


def pack_black_bits(image: Image.Image) -> tuple[int, bytes]:
    if image.mode != "1":
        raise ValueError("Packed bitmap için Pillow mode '1' gereklidir.")
    width, height = image.size
    bytes_per_row = (width + 7) // 8
    output = bytearray(bytes_per_row * height)
    pixels = image.load()
    for y in range(height):
        row_start = y * bytes_per_row
        for x in range(width):
            if pixels[x, y] == 0:
                output[row_start + (x // 8)] |= 1 << (7 - (x % 8))
    return bytes_per_row, bytes(output)


class TestPageRenderer:
    __test__ = False

    def __init__(
        self,
        regular_font: Path,
        bold_font: Path,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._regular_font = regular_font
        self._bold_font = bold_font
        self._clock = clock or (lambda: datetime.now().astimezone())
        if not regular_font.is_file() or not bold_font.is_file():
            raise RenderingError("Paketlenmiş Bitstream Vera fontları bulunamadı.")

    def render(
        self,
        template: TemplateDefinition,
        data: Mapping[str, object],
        paper: PaperProfile,
        options: RenderOptions,
    ) -> RenderedDocument:
        if template.id != "test.page":
            raise RenderingError(f"Desteklenmeyen Faz 2 template’i: {template.id}")

        width = paper.physical_width_dots
        max_height = 1600
        image = Image.new("L", (width, max_height), 255)
        draw = ImageDraw.Draw(image)
        title_font = ImageFont.truetype(str(self._bold_font), 30)
        body_font = ImageFont.truetype(str(self._regular_font), 20)
        small_font = ImageFont.truetype(str(self._regular_font), 16)
        x = paper.margin_left_dots + paper.horizontal_content_offset_dots
        right = x + paper.printable_width_dots - 1
        y = paper.margin_top_dots

        def centered(text: str, font: ImageFont.FreeTypeFont, spacing: int = 8) -> None:
            nonlocal y
            box = draw.textbbox((0, 0), text, font=font)
            text_width = box[2] - box[0]
            text_height = box[3] - box[1]
            draw.text((x + (paper.printable_width_dots - text_width) // 2, y), text, font=font, fill=0)
            y += text_height + spacing

        def line(text: str, font: ImageFont.FreeTypeFont = body_font, spacing: int = 6) -> None:
            nonlocal y
            draw.text((x, y), text, font=font, fill=0)
            box = draw.textbbox((x, y), text, font=font)
            y = box[3] + spacing

        centered("GC420t TEST SAYFASI", title_font, 12)
        draw.line((x, y, right, y), fill=0, width=2)
        y += 12
        timestamp = data.get("timestamp")
        now = timestamp if isinstance(timestamp, datetime) else self._clock()
        line(f"Tarih: {now:%d.%m.%Y %H:%M}")
        line(f"Kağıt: {paper.name} / {paper.printable_width_dots} dot")
        line("DPI: 203 / Dil: ZPL")
        queue_name = str(data.get("spooler_name", "ZDesigner GC420t"))
        line(f"Kuyruk: {queue_name}", small_font, 10)
        line("Türkçe: ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü", small_font, 12)

        draw.line((x, y, right, y), fill=0, width=2)
        y += 18
        scale_start = x
        scale_end = min(right, scale_start + mm_to_dots(30, paper.dpi))
        draw.line((scale_start, y, scale_end, y), fill=0, width=2)
        for millimeter in (0, 10, 20, 30):
            tick_x = scale_start + mm_to_dots(millimeter, paper.dpi)
            if tick_x <= right:
                draw.line((tick_x, y - 8, tick_x, y + 8), fill=0, width=2)
                if millimeter:
                    draw.text((tick_x - 10, y + 10), str(millimeter), font=small_font, fill=0)
        y += 42

        edge_padding = 6
        draw.text((x + edge_padding, y), "LEFT EDGE", font=small_font, fill=0)
        center_text = "CENTER"
        center_box = draw.textbbox((0, 0), center_text, font=small_font)
        draw.text((x + (paper.printable_width_dots - (center_box[2] - center_box[0])) // 2, y), center_text, font=small_font, fill=0)
        right_text = "RIGHT EDGE"
        right_box = draw.textbbox((0, 0), right_text, font=small_font)
        draw.text((right - edge_padding - (right_box[2] - right_box[0]) + 1, y), right_text, font=small_font, fill=0)
        y += 32
        draw.rectangle((x, 0, right, y), outline=0, width=1)

        content_height = y + paper.margin_bottom_dots
        if paper.length_mode is LengthMode.FIXED:
            assert paper.fixed_length_mm is not None
            fixed_height = mm_to_dots(paper.fixed_length_mm, paper.dpi)
            if content_height > fixed_height:
                raise RenderingError("Test sayfası sabit kağıt uzunluğuna sığmıyor.")
            final_height = fixed_height
        else:
            final_height = content_height

        image = image.crop((0, 0, width, final_height))
        if options.brightness != 1.0:
            image = ImageEnhance.Brightness(image).enhance(options.brightness)
        if options.contrast != 1.0:
            image = ImageEnhance.Contrast(image).enhance(options.contrast)
        mono = image.point(lambda value: 255 if value >= options.threshold else 0, mode="1")
        bytes_per_row, bitmap = pack_black_bits(mono)
        return RenderedDocument(width, final_height, bytes_per_row, bitmap)

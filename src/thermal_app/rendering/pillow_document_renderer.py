from __future__ import annotations

from pathlib import Path
from typing import Mapping

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps

from thermal_app.application.dto import RenderedDocument, RenderOptions
from thermal_app.domain.enums import LengthMode
from thermal_app.domain.errors import RenderingError
from thermal_app.domain.measurements import mm_to_dots
from thermal_app.domain.models import PaperProfile, TemplateDefinition
from thermal_app.domain.template_schema import normalize_template_input
from thermal_app.rendering.primitives import (
    BadgeRow,
    CalibrationScale,
    Callout,
    Checkbox,
    ChecklistValue,
    CutLine,
    Divider,
    FramedImage,
    GraphicHeader,
    ImageBlock,
    KeyValue,
    NumberedStep,
    QrBlock,
    SectionBand,
    Spacer,
    Text,
)
from thermal_app.rendering.template_builders import TemplateBuilder, built_in_builders
from thermal_app.rendering.test_page_renderer import TestPageRenderer, pack_black_bits
from thermal_app.rendering.thermal import thermalize


class PillowDocumentRenderer:
    def __init__(
        self,
        regular_font: Path,
        bold_font: Path,
        *,
        test_page_renderer: TestPageRenderer | None = None,
        builders: Mapping[str, TemplateBuilder] | None = None,
    ) -> None:
        self._regular_font = regular_font
        self._bold_font = bold_font
        self._test_page = test_page_renderer or TestPageRenderer(regular_font, bold_font)
        self._builders = dict(builders or built_in_builders())

    def render(
        self,
        template: TemplateDefinition,
        data: Mapping[str, object],
        paper: PaperProfile,
        options: RenderOptions,
    ) -> RenderedDocument:
        if template.id == "test.page":
            return self._test_page.render(template, data, paper, options)
        try:
            builder = self._builders[template.renderer_key]
        except KeyError as exc:
            raise RenderingError(f"Template renderer bulunamadı: {template.renderer_key}") from exc
        normalized = normalize_template_input(template, data)
        elements = builder.build(normalized, options.visual_style)
        return self._draw(elements, paper, options)

    def _draw(self, elements: list[object], paper: PaperProfile, options: RenderOptions) -> RenderedDocument:
        width = paper.physical_width_dots
        image = Image.new("L", (width, 12000), 255)
        draw = ImageDraw.Draw(image)
        regular = {
            "title": ImageFont.truetype(str(self._bold_font), 30),
            "heading": ImageFont.truetype(str(self._bold_font), 21),
            "body": ImageFont.truetype(str(self._regular_font), 20),
            "small": ImageFont.truetype(str(self._regular_font), 16),
            "label": ImageFont.truetype(str(self._bold_font), 16),
        }
        left = paper.margin_left_dots + paper.horizontal_content_offset_dots
        right = left + paper.printable_width_dots - 1
        available = right - left + 1
        y = paper.margin_top_dots

        for element in elements:
            top = y
            if isinstance(element, Spacer):
                y += element.height
            elif isinstance(element, Divider):
                draw.line((left, y, right, y), fill=0, width=element.thickness)
                y += element.thickness + 8
            elif isinstance(element, Text):
                font = regular[element.style]
                y = self._draw_wrapped(draw, element.value, font, left, right, y, element.align)
                y += 7
            elif isinstance(element, Checkbox):
                box_size = 18
                draw.rectangle((left, y + 2, left + box_size, y + 2 + box_size), outline=0, width=2)
                if element.checked:
                    draw.line((left + 3, y + 11, left + 8, y + 16), fill=0, width=2)
                    draw.line((left + 8, y + 16, left + 16, y + 5), fill=0, width=2)
                text_left = left + box_size + 8
                y = self._draw_wrapped(draw, element.label, regular["body"], text_left, right, y, "left")
                if element.secondary:
                    y = self._draw_wrapped(draw, element.secondary, regular["small"], text_left, right, y, "left")
                y += 7
            elif isinstance(element, KeyValue):
                draw.text((left, y), element.key, font=regular["body"], fill=0)
                value_box = draw.textbbox((0, 0), element.value, font=regular["body"])
                draw.text((right - (value_box[2] - value_box[0]), y), element.value, font=regular["body"], fill=0)
                y += max(24, value_box[3] - value_box[1]) + 7
            elif isinstance(element, ImageBlock):
                y = self._draw_image(image, element, left, right, y)
            elif isinstance(element, QrBlock):
                y = self._draw_qr(image, draw, element, regular["small"], left, right, y)
            elif isinstance(element, CalibrationScale):
                y = self._draw_calibration(draw, regular, paper, element, left, right, y)
            elif isinstance(element, GraphicHeader):
                y = self._draw_graphic_header(draw, regular, element, left, right, y)
            elif isinstance(element, SectionBand):
                y = self._draw_section_band(draw, regular, element, left, right, y)
            elif isinstance(element, BadgeRow):
                y = self._draw_badge_row(draw, regular, element, left, right, y)
            elif isinstance(element, NumberedStep):
                y = self._draw_numbered_step(draw, regular, element, left, right, y)
            elif isinstance(element, Callout):
                y = self._draw_callout(draw, regular, element, left, right, y)
            elif isinstance(element, FramedImage):
                y = self._draw_framed_image(image, draw, element, left, right, y)
            elif isinstance(element, CutLine):
                y = self._draw_cut_line(draw, left, right, y)
            elif isinstance(element, ChecklistValue):
                y = self._draw_checklist_value(draw, regular, element, left, right, y)
            else:
                raise RenderingError(f"Bilinmeyen layout elementi: {type(element).__name__}")

        content_height = y + paper.margin_bottom_dots
        if paper.length_mode is LengthMode.FIXED:
            assert paper.fixed_length_mm is not None
            final_height = mm_to_dots(paper.fixed_length_mm, paper.dpi)
            if content_height > final_height:
                raise RenderingError("İçerik sabit kağıt uzunluğuna sığmıyor; çıktı kırpılmadı.")
        else:
            final_height = content_height
        image = image.crop((0, 0, width, final_height))
        mono = thermalize(image, options)
        row_bytes, bitmap = pack_black_bits(mono)
        return RenderedDocument(width, final_height, row_bytes, bitmap)

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
        paragraphs = text.splitlines() or [""]
        lines: list[str] = []
        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                box = draw.textbbox((0, 0), candidate, font=font)
                if box[2] - box[0] <= width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    @classmethod
    def _draw_wrapped(
        cls,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        left: int,
        right: int,
        y: int,
        align: str,
    ) -> int:
        for line in cls._wrap(draw, text, font, right - left + 1):
            box = draw.textbbox((0, 0), line or "Ag", font=font)
            line_width = box[2] - box[0]
            line_height = box[3] - box[1]
            x = left if align == "left" else (right - line_width if align == "right" else left + (right - left + 1 - line_width) // 2)
            if line:
                draw.text((x, y), line, font=font, fill=0)
            y += line_height + 5
        return y

    @staticmethod
    def _draw_image(canvas: Image.Image, element: ImageBlock, left: int, right: int, y: int) -> int:
        try:
            source = Image.open(element.path)
            source = ImageOps.exif_transpose(source).convert("L")
        except Exception as exc:
            raise RenderingError("Fotoğraf açılamadı veya desteklenmiyor.") from exc
        if element.rotation:
            source = source.rotate(-element.rotation, expand=True, fillcolor=255)
        available = right - left + 1
        if element.fit == "fit_width" or source.width > available:
            height = max(1, round(source.height * available / source.width))
            source = source.resize((available, height), Image.Resampling.LANCZOS)
        x = left + (available - source.width) // 2
        canvas.paste(source, (x, y))
        return y + source.height

    @staticmethod
    def _draw_qr(
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        element: QrBlock,
        font: ImageFont.FreeTypeFont,
        left: int,
        right: int,
        y: int,
    ) -> int:
        try:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=1)
            qr.add_data(element.payload)
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white").convert("L")
        except Exception as exc:
            raise RenderingError("QR içeriği kod kapasitesini aşıyor veya geçersiz.") from exc
        available = right - left + 1
        target = min(available, 360)
        integer_scale = max(1, target // qr_image.width)
        qr_image = qr_image.resize(
            (qr_image.width * integer_scale, qr_image.height * integer_scale),
            Image.Resampling.NEAREST,
        )
        x = left + (available - qr_image.width) // 2
        canvas.paste(qr_image, (x, y))
        y += qr_image.height + 8
        if element.caption:
            y = PillowDocumentRenderer._draw_wrapped(draw, element.caption, font, left, right, y, "center")
        return y

    @classmethod
    def _draw_graphic_header(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: GraphicHeader,
        left: int,
        right: int,
        y: int,
    ) -> int:
        icon_size = 34
        text_left = left + icon_size + 12
        top = y
        cls._draw_icon(draw, element.icon, left, top + 1, icon_size, fill=0, width=3)
        title_bottom = cls._draw_wrapped(draw, element.title, fonts["title"], text_left, right, y, "left")
        y = max(top + icon_size, title_bottom)
        if element.subtitle:
            y = cls._draw_wrapped(draw, element.subtitle, fonts["small"], text_left, right, y, "left")
        y += 5
        draw.line((left, y, right, y), fill=0, width=3)
        return y + 10

    @classmethod
    def _draw_section_band(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: SectionBand,
        left: int,
        right: int,
        y: int,
    ) -> int:
        height = 34
        draw.rounded_rectangle((left, y, right, y + height), radius=6, fill=0)
        cls._draw_icon(draw, element.icon, left + 7, y + 7, 20, fill=255, width=2)
        draw.text((left + 35, y + 6), element.label, font=fonts["label"], fill=255)
        return y + height + 9

    @classmethod
    def _draw_badge_row(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: BadgeRow,
        left: int,
        right: int,
        y: int,
    ) -> int:
        if not element.items:
            return y
        gap = 6
        available = right - left + 1
        badge_width = (available - gap * (len(element.items) - 1)) // len(element.items)
        height = 36
        for index, (icon, value) in enumerate(element.items):
            x = left + index * (badge_width + gap)
            badge_right = right if index == len(element.items) - 1 else x + badge_width - 1
            draw.rounded_rectangle((x, y, badge_right, y + height), radius=6, outline=0, width=2)
            cls._draw_icon(draw, icon, x + 6, y + 8, 20, fill=0, width=2)
            draw.text((x + 31, y + 9), value, font=fonts["small"], fill=0)
        return y + height + 10

    @classmethod
    def _draw_numbered_step(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: NumberedStep,
        left: int,
        right: int,
        y: int,
    ) -> int:
        diameter = 24
        draw.ellipse((left, y + 1, left + diameter, y + 1 + diameter), fill=0)
        number = str(element.number)
        box = draw.textbbox((0, 0), number, font=fonts["label"])
        number_width = box[2] - box[0]
        number_height = box[3] - box[1]
        draw.text(
            (left + (diameter - number_width) // 2, y + 1 + (diameter - number_height) // 2 - box[1]),
            number,
            font=fonts["label"],
            fill=255,
        )
        text_bottom = cls._draw_wrapped(
            draw,
            element.text,
            fonts["body"],
            left + diameter + 10,
            right,
            y,
            "left",
        )
        return max(y + diameter + 1, text_bottom) + 7

    @classmethod
    def _draw_callout(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: Callout,
        left: int,
        right: int,
        y: int,
    ) -> int:
        top = y
        inner_left = left + 12
        title_left = inner_left + 27
        title_y = top + 9
        cls._draw_icon(draw, element.icon, inner_left, title_y, 19, fill=0, width=2)
        draw.text((title_left, title_y + 1), element.title, font=fonts["label"], fill=0)
        text_y = title_y + 25
        text_bottom = cls._draw_wrapped(
            draw,
            element.text,
            fonts["body"],
            inner_left,
            right - 10,
            text_y,
            "left",
        )
        bottom = max(text_bottom + 4, top + 50)
        draw.rounded_rectangle((left, top, right, bottom), radius=7, outline=0, width=2)
        draw.rounded_rectangle((left, top, left + 6, bottom), radius=3, fill=0)
        return bottom + 10

    @staticmethod
    def _draw_framed_image(
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        element: FramedImage,
        left: int,
        right: int,
        y: int,
    ) -> int:
        try:
            source = Image.open(element.path)
            source = ImageOps.exif_transpose(source).convert("L")
        except Exception as exc:
            raise RenderingError("Fotoğraf açılamadı veya desteklenmiyor.") from exc
        if element.rotation:
            source = source.rotate(-element.rotation, expand=True, fillcolor=255)
        padding = 7
        inner_left = left + padding
        inner_right = right - padding
        available = inner_right - inner_left + 1
        if element.fit == "fit_width" or source.width > available:
            height = max(1, round(source.height * available / source.width))
            source = source.resize((available, height), Image.Resampling.LANCZOS)
        x = inner_left + (available - source.width) // 2
        image_y = y + padding
        canvas.paste(source, (x, image_y))
        bottom = image_y + source.height + padding
        draw.rectangle((left, y, right, bottom), outline=0, width=3)
        return bottom + 9

    @staticmethod
    def _draw_cut_line(draw: ImageDraw.ImageDraw, left: int, right: int, y: int) -> int:
        y += 5
        x = left
        while x <= right:
            draw.line((x, y, min(x + 11, right), y), fill=0, width=2)
            x += 20
        return y + 13

    @classmethod
    def _draw_checklist_value(
        cls,
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        element: ChecklistValue,
        left: int,
        right: int,
        y: int,
    ) -> int:
        box_size = 18
        draw.rectangle((left, y + 2, left + box_size, y + 2 + box_size), outline=0, width=2)
        if element.checked:
            draw.line((left + 3, y + 11, left + 8, y + 16), fill=0, width=2)
            draw.line((left + 8, y + 16, left + 16, y + 5), fill=0, width=2)
        value_width = 0
        if element.value:
            value_box = draw.textbbox((0, 0), element.value, font=fonts["label"])
            value_width = value_box[2] - value_box[0]
            draw.text((right - value_width, y + 2), element.value, font=fonts["label"], fill=0)
        text_left = left + box_size + 8
        text_right = right - value_width - (10 if value_width else 0)
        text_bottom = cls._draw_wrapped(
            draw,
            element.label,
            fonts["body"],
            text_left,
            max(text_left, text_right),
            y,
            "left",
        )
        return max(y + box_size + 2, text_bottom) + 7

    @staticmethod
    def _draw_icon(
        draw: ImageDraw.ImageDraw,
        icon: str,
        x: int,
        y: int,
        size: int,
        *,
        fill: int,
        width: int,
    ) -> None:
        right = x + size - 1
        bottom = y + size - 1
        q = max(4, size // 4)
        if icon == "check":
            draw.ellipse((x + 1, y + 1, right - 1, bottom - 1), outline=fill, width=width)
            draw.line((x + q, y + size // 2, x + size // 2 - 1, y + size - q), fill=fill, width=width)
            draw.line((x + size // 2 - 1, y + size - q, right - q + 1, y + q), fill=fill, width=width)
        elif icon == "basket":
            draw.line((x + q, y + q, x + size // 2, y + 1, right - q, y + q), fill=fill, width=width)
            draw.rectangle((x + 3, y + q, right - 3, bottom - 4), outline=fill, width=width)
            draw.line((x + size // 3, y + q + 3, x + size // 3, bottom - 6), fill=fill, width=width)
            draw.line((x + size * 2 // 3, y + q + 3, x + size * 2 // 3, bottom - 6), fill=fill, width=width)
        elif icon == "pot":
            draw.rectangle((x + 4, y + q, right - 4, bottom - 4), outline=fill, width=width)
            draw.line((x + 2, y + q, right - 2, y + q), fill=fill, width=width)
            draw.line((x + q, y + 3, right - q, y + 3), fill=fill, width=width)
            draw.line((x + 1, y + size // 2, x + 5, y + size // 2), fill=fill, width=width)
            draw.line((right - 5, y + size // 2, right - 1, y + size // 2), fill=fill, width=width)
        elif icon == "note":
            draw.rectangle((x + 3, y + 2, right - 3, bottom - 2), outline=fill, width=width)
            draw.line((right - q, y + 2, right - q, y + q, right - 3, y + q), fill=fill, width=width)
            draw.line((x + q, y + size // 2, right - q, y + size // 2), fill=fill, width=width)
            draw.line((x + q, y + size * 2 // 3, right - q, y + size * 2 // 3), fill=fill, width=width)
        elif icon == "photo":
            draw.rectangle((x + 2, y + 3, right - 2, bottom - 3), outline=fill, width=width)
            dot = max(4, size // 6)
            draw.ellipse((x + q, y + q, x + q + dot, y + q + dot), outline=fill, width=width)
            draw.line((x + 4, bottom - 6, x + size // 2, y + size // 2, right - 4, bottom - 6), fill=fill, width=width)
        elif icon == "link":
            draw.rounded_rectangle((x + 1, y + q, x + size // 2 + 3, bottom - q), radius=q, outline=fill, width=width)
            draw.rounded_rectangle((x + size // 2 - 3, y + q, right - 1, bottom - q), radius=q, outline=fill, width=width)
            draw.line((x + q, y + size // 2, right - q, y + size // 2), fill=fill, width=width)
        elif icon == "star":
            points = [
                (x + size // 2, y + 1),
                (x + size * 3 // 5, y + size * 2 // 5),
                (right - 1, y + size * 2 // 5),
                (x + size * 7 // 10, y + size * 3 // 5),
                (x + size * 4 // 5, bottom - 1),
                (x + size // 2, y + size * 7 // 10),
                (x + size // 5, bottom - 1),
                (x + size * 3 // 10, y + size * 3 // 5),
                (x + 1, y + size * 2 // 5),
                (x + size * 2 // 5, y + size * 2 // 5),
            ]
            draw.line(points + [points[0]], fill=fill, width=width, joint="curve")
        elif icon == "tag":
            points = [(x + 2, y + q), (x + size // 2, y + 2), (right - 2, y + size // 2), (x + size // 2, bottom - 2), (x + 2, bottom - q)]
            draw.line(points + [points[0]], fill=fill, width=width)
            draw.ellipse((x + q, y + size // 2 - 2, x + q + 4, y + size // 2 + 2), fill=fill)
        elif icon == "clock":
            draw.ellipse((x + 1, y + 1, right - 1, bottom - 1), outline=fill, width=width)
            draw.line((x + size // 2, y + q, x + size // 2, y + size // 2, right - q, y + size // 2), fill=fill, width=width)
        elif icon == "flame":
            points = [(x + size // 2, y + 1), (right - 3, y + size // 2), (x + size * 3 // 5, bottom - 2), (x + q, bottom - q), (x + 2, y + size // 2)]
            draw.line(points + [points[0]], fill=fill, width=width, joint="curve")
        elif icon == "people":
            dot = max(5, size // 4)
            draw.ellipse((x + size // 2 - dot // 2, y + 2, x + size // 2 + dot // 2, y + 2 + dot), outline=fill, width=width)
            draw.arc((x + q, y + q, right - q, bottom - 1), 190, 350, fill=fill, width=width)
        elif icon == "ingredients":
            draw.arc((x + 2, y + 2, right - 2, bottom - 4), 0, 180, fill=fill, width=width)
            draw.line((x + 3, y + size // 2, right - 3, y + size // 2), fill=fill, width=width)
            draw.line((x + q, bottom - 3, right - q, bottom - 3), fill=fill, width=width)
        elif icon == "steps":
            for offset in (3, size // 2):
                draw.rectangle((x + 2, y + offset, x + 6, y + offset + 4), outline=fill, width=width)
                draw.line((x + 10, y + offset + 2, right - 2, y + offset + 2), fill=fill, width=width)
        else:
            for offset in (3, size // 2):
                draw.rectangle((x + 2, y + offset, x + 6, y + offset + 4), outline=fill, width=width)
                draw.line((x + 10, y + offset + 2, right - 2, y + offset + 2), fill=fill, width=width)

    @staticmethod
    def _draw_calibration(
        draw: ImageDraw.ImageDraw,
        fonts: Mapping[str, ImageFont.FreeTypeFont],
        paper: PaperProfile,
        element: CalibrationScale,
        left: int,
        right: int,
        y: int,
    ) -> int:
        y += max(0, element.top_offset_dots)
        origin = max(left, min(right, left + element.left_offset_dots))
        scale_end = min(right, origin + mm_to_dots(30, paper.dpi))
        draw.line((origin, y, scale_end, y), fill=0, width=2)
        for millimeter in (0, 10, 20, 30):
            x = origin + mm_to_dots(millimeter, paper.dpi)
            if x <= right:
                draw.line((x, y - 10, x, y + 10), fill=0, width=2)
                if millimeter:
                    draw.text((x - 10, y + 12), str(millimeter), font=fonts["small"], fill=0)
        y += 48
        edge_padding = 6
        labels = ("LEFT EDGE", "CENTER", "RIGHT EDGE")
        widths = {
            label: draw.textbbox((0, 0), label, font=fonts["small"])[2]
            for label in labels
        }
        positions = (
            (left + edge_padding, "LEFT EDGE"),
            (left + (right - left + 1 - widths["CENTER"]) // 2, "CENTER"),
            (right - edge_padding - widths["RIGHT EDGE"] + 1, "RIGHT EDGE"),
        )
        for x, label in positions:
            draw.text((x, y), label, font=fonts["small"], fill=0)
        y += 32
        draw.rectangle((left, y, right, y + 80), outline=0, width=2)
        draw.line((left, y, right, y + 80), fill=0, width=1)
        draw.line((right, y, left, y + 80), fill=0, width=1)
        draw.text((left + 8, y + 28), f"{paper.width_mm} mm / {paper.printable_width_dots} dot / 203 DPI", font=fonts["small"], fill=0)
        return y + 92

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol
import unicodedata

from thermal_app.domain.errors import RenderingError
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
    LayoutElement,
    NumberedStep,
    QrBlock,
    SectionBand,
    Spacer,
    Text,
)


class TemplateBuilder(Protocol):
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]: ...


class CustomBlockBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        elements: list[LayoutElement] = []
        for raw in list(data.get("blocks") or []):
            if not isinstance(raw, Mapping):
                continue
            kind = str(raw.get("type", "text"))
            value = str(raw.get("value", ""))
            if kind == "text":
                elements.append(Text(value, str(raw.get("style", "body")), str(raw.get("align", "left"))))
            elif kind == "heading":
                elements.append(Text(value, "heading", str(raw.get("align", "left"))))
            elif kind == "divider":
                elements.append(Divider(max(2, min(4, int(raw.get("thickness", 2))))) )
            elif kind == "spacer":
                elements.append(Spacer(max(4, min(240, int(raw.get("height", 12))))))
            elif kind == "section_band":
                elements.append(SectionBand(value or "BÖLÜM", str(raw.get("icon", "list"))))
            elif kind == "key_value":
                elements.append(KeyValue(value, str(raw.get("secondary", ""))))
            elif kind == "checklist":
                elements.append(Checkbox(value, bool(raw.get("checked", False)), str(raw.get("secondary", ""))))
            elif kind == "image":
                elements.append(ImageBlock(Path(value), str(raw.get("fit", "fit_width")), int(raw.get("rotation", 0))))
            elif kind == "qr":
                elements.append(QrBlock(value, str(raw.get("secondary", ""))))
        return elements


class TodoBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        if visual_style == "graphic":
            return self._build_graphic(data)
        elements: list[LayoutElement] = [Text(str(data["title"]), "title", "center")]
        if data.get("date"):
            elements.append(Text(str(data["date"]), "small", "center"))
        elements.extend((Divider(), Spacer(8)))
        show_boxes = bool(data.get("show_checkboxes", True))
        priorities = list(data.get("priority_tasks") or [])
        if priorities:
            elements.append(Text("ÖNCELİKLİ", "heading"))
            for task in priorities[:3]:
                elements.append(Checkbox(str(task)) if show_boxes else Text(f"• {task}"))
            elements.append(Spacer())
        for row in list(data.get("tasks") or []):
            title = str(row.get("title", ""))
            if not title:
                continue
            secondary = " · ".join(value for value in (row.get("due_time", ""), row.get("category", "")) if value)
            elements.append(Checkbox(title, secondary=secondary) if show_boxes else Text(f"• {title}"))
        if data.get("note"):
            elements.extend((Spacer(), Divider(1), Text("NOT", "small"), Text(str(data["note"]))))
        return elements

    @staticmethod
    def _build_graphic(data: Mapping[str, object]) -> list[LayoutElement]:
        elements: list[LayoutElement] = [
            GraphicHeader(str(data["title"]), str(data.get("date") or ""), "check")
        ]
        show_boxes = bool(data.get("show_checkboxes", True))
        priorities = list(data.get("priority_tasks") or [])
        if priorities:
            elements.append(SectionBand("ÖNCELİKLİ", "star"))
            for task in priorities[:3]:
                elements.append(Checkbox(str(task)) if show_boxes else Text(f"• {task}"))
        tasks = [row for row in list(data.get("tasks") or []) if str(row.get("title", ""))]
        if tasks:
            elements.append(SectionBand("GÖREVLER", "list"))
            for row in tasks:
                secondary = " · ".join(
                    value for value in (row.get("due_time", ""), row.get("category", "")) if value
                )
                title = str(row.get("title", ""))
                elements.append(Checkbox(title, secondary=secondary) if show_boxes else Text(f"• {title}"))
        if data.get("note"):
            elements.append(Callout("NOT", str(data["note"]), "note"))
        elements.append(CutLine())
        return elements


class ShoppingBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        elements: list[LayoutElement]
        if visual_style == "graphic":
            elements = [GraphicHeader(str(data["title"]), str(data.get("date") or ""), "basket")]
        else:
            elements = [Text(str(data["title"]), "title", "center")]
            if data.get("date"):
                elements.append(Text(str(data["date"]), "small", "center"))
            elements.extend((Divider(), Spacer(8)))
        grouped: dict[str, tuple[str, list[Mapping[str, str]]]] = {}
        for row in list(data.get("items") or []):
            category = self._clean_category(row.get("category"))
            key = category.casefold()
            if key not in grouped:
                grouped[key] = (category, [])
            grouped[key][1].append(row)
        for category, rows in grouped.values():
            elements.append(
                SectionBand(category.upper(), "tag")
                if visual_style == "graphic"
                else Text(category.upper(), "heading")
            )
            for row in rows:
                product = str(row.get("product", ""))
                quantity = str(row.get("quantity", ""))
                if product:
                    if visual_style == "graphic" and data.get("show_checkboxes", True):
                        elements.append(ChecklistValue(product, quantity))
                    elif data.get("show_checkboxes", True):
                        elements.append(Checkbox(product, secondary=quantity))
                    else:
                        elements.append(KeyValue(product, quantity))
            elements.append(Spacer(8))
        if visual_style == "graphic":
            elements.append(CutLine())
        return elements

    @staticmethod
    def _clean_category(value: object) -> str:
        normalized = unicodedata.normalize("NFKC", str(value or ""))
        without_formatting = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Cf"
        )
        return " ".join(without_formatting.split()) or "Diğer"


class RecipeBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        metadata = " · ".join(
            value
            for value in (
                f"Hazırlık {data['prep_time']}" if data.get("prep_time") else "",
                f"Pişirme {data['cook_time']}" if data.get("cook_time") else "",
                f"{data['servings']} porsiyon" if data.get("servings") else "",
            )
            if value
        )
        if visual_style == "graphic":
            badges = tuple(
                (icon, value)
                for icon, value in (
                    ("clock", str(data.get("prep_time") or "")),
                    ("flame", str(data.get("cook_time") or "")),
                    ("people", f"{data['servings']} kişilik" if data.get("servings") else ""),
                )
                if value
            )
            elements: list[LayoutElement] = [GraphicHeader(str(data["name"]), icon="pot")]
            if badges:
                elements.append(BadgeRow(badges))
            elements.append(SectionBand("MALZEMELER", "ingredients"))
            elements.extend(Text(f"• {item}") for item in list(data.get("ingredients") or []))
            elements.append(SectionBand("ADIMLAR", "steps"))
            for index, step in enumerate(list(data.get("steps") or []), start=1):
                elements.append(NumberedStep(index, str(step)))
            if data.get("notes"):
                elements.append(Callout("NOTLAR", str(data["notes"]), "note"))
            elements.append(CutLine())
            return elements

        elements = [Text(str(data["name"]), "title", "center")]
        if metadata:
            elements.append(Text(metadata, "small", "center"))
        elements.extend((Divider(), Text("MALZEMELER", "heading")))
        elements.extend(Text(f"• {item}") for item in list(data.get("ingredients") or []))
        elements.extend((Spacer(), Divider(1), Text("ADIMLAR", "heading")))
        for index, step in enumerate(list(data.get("steps") or []), start=1):
            elements.append(Text(f"{index}. {step}"))
        if data.get("notes"):
            elements.extend((Spacer(), Divider(1), Text("NOTLAR", "heading"), Text(str(data["notes"]))))
        return elements


class QuickNoteBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        if visual_style == "graphic":
            elements: list[LayoutElement] = [
                GraphicHeader(str(data.get("title") or "Not"), str(data.get("date_time") or ""), "note"),
                Callout("NOT", str(data["text"]), "note"),
            ]
            if data.get("include_qr"):
                elements.extend((Spacer(), QrBlock(str(data["text"]), "Notun dijital kopyası")))
            elements.append(CutLine())
            return elements
        elements: list[LayoutElement] = []
        if data.get("title"):
            elements.extend((Text(str(data["title"]), "title", "center"), Divider()))
        if data.get("date_time"):
            elements.append(Text(str(data["date_time"]), "small", "right"))
        elements.append(Text(str(data["text"]), "body"))
        if data.get("include_qr"):
            elements.extend((Spacer(), QrBlock(str(data["text"]), "Notun dijital kopyası")))
        return elements


class PhotoBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        path = Path(str(data["image_path"]))
        if not str(data["image_path"]):
            return [Text("Fotoğraf seçin", "heading", "center"), Text("JPG veya PNG dosyası", "small", "center")]
        if not path.is_file():
            raise RenderingError("Seçilen fotoğraf dosyası bulunamadı.")
        fit = str(data.get("fit") or "fit_width")
        rotation = int(str(data.get("rotation") or "0"))
        elements: list[LayoutElement] = (
            [GraphicHeader("FOTOĞRAF", icon="photo"), FramedImage(path, fit, rotation)]
            if visual_style == "graphic"
            else [ImageBlock(path, fit, rotation)]
        )
        if data.get("caption"):
            elements.extend(
                (Spacer(8), Callout("AÇIKLAMA", str(data["caption"]), "photo"))
                if visual_style == "graphic"
                else (Spacer(8), Text(str(data["caption"]), "small", "center"))
            )
        if visual_style == "graphic":
            elements.append(CutLine())
        return elements


class QrBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        kind = str(data.get("kind") or "Text")
        payload = str(data.get("payload") or "")
        if kind == "Wi-Fi":
            ssid = str(data.get("ssid") or "")
            password = str(data.get("password") or "")
            if not ssid:
                raise RenderingError("Wi-Fi QR için ağ adı zorunludur.")
            payload = f"WIFI:T:WPA;S:{ssid};P:{password};;"
        elif kind == "Phone":
            payload = f"tel:{payload}"
        elif kind == "Email":
            payload = f"mailto:{payload}"
        if not payload:
            raise RenderingError("QR içeriği boş olamaz.")
        title = str(data.get("title") or "QR Kod")
        caption = str(data.get("caption") or "")
        if visual_style == "graphic":
            elements: list[LayoutElement] = [GraphicHeader(title, icon="link"), QrBlock(payload)]
            if caption:
                elements.append(Callout("TARA", caption, "link"))
            elements.append(CutLine())
            return elements
        return [Text(title, "title", "center"), Divider(), QrBlock(payload, caption)]


class CalibrationBuilder:
    def build(self, data: Mapping[str, object], visual_style: str = "plain") -> list[LayoutElement]:
        try:
            left = int(str(data.get("left_offset_dots") or "0"))
            top = int(str(data.get("top_offset_dots") or "0"))
        except ValueError as exc:
            raise RenderingError("Kalibrasyon ofsetleri tam sayı olmalıdır.") from exc
        return [
            Text("GC420t BASKI KALİBRASYONU", "title", "center"),
            Divider(),
            CalibrationScale(left, top),
        ]


def built_in_builders() -> dict[str, TemplateBuilder]:
    return {
        "custom.blocks": CustomBlockBuilder(),
        "todo": TodoBuilder(),
        "shopping": ShoppingBuilder(),
        "recipe": RecipeBuilder(),
        "quick-note": QuickNoteBuilder(),
        "photo": PhotoBuilder(),
        "qr": QrBuilder(),
        "calibration": CalibrationBuilder(),
    }

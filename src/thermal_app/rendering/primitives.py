from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Text:
    value: str
    style: str = "body"
    align: str = "left"


@dataclass(frozen=True, slots=True)
class Spacer:
    height: int = 12


@dataclass(frozen=True, slots=True)
class Divider:
    thickness: int = 2


@dataclass(frozen=True, slots=True)
class Checkbox:
    label: str
    checked: bool = False
    secondary: str = ""


@dataclass(frozen=True, slots=True)
class KeyValue:
    key: str
    value: str


@dataclass(frozen=True, slots=True)
class ImageBlock:
    path: Path
    fit: str = "fit_width"
    rotation: int = 0


@dataclass(frozen=True, slots=True)
class QrBlock:
    payload: str
    caption: str = ""


@dataclass(frozen=True, slots=True)
class CalibrationScale:
    left_offset_dots: int = 0
    top_offset_dots: int = 0


@dataclass(frozen=True, slots=True)
class GraphicHeader:
    title: str
    subtitle: str = ""
    icon: str = "check"


@dataclass(frozen=True, slots=True)
class SectionBand:
    label: str
    icon: str = "list"


@dataclass(frozen=True, slots=True)
class BadgeRow:
    items: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class NumberedStep:
    number: int
    text: str


@dataclass(frozen=True, slots=True)
class Callout:
    title: str
    text: str
    icon: str = "note"


@dataclass(frozen=True, slots=True)
class FramedImage:
    path: Path
    fit: str = "fit_width"
    rotation: int = 0


@dataclass(frozen=True, slots=True)
class CutLine:
    pass


@dataclass(frozen=True, slots=True)
class ChecklistValue:
    label: str
    value: str = ""
    checked: bool = False


LayoutElement = (
    Text
    | Spacer
    | Divider
    | Checkbox
    | KeyValue
    | ImageBlock
    | QrBlock
    | CalibrationScale
    | GraphicHeader
    | SectionBand
    | BadgeRow
    | NumberedStep
    | Callout
    | FramedImage
    | CutLine
    | ChecklistValue
)

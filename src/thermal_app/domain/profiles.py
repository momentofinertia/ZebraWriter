from __future__ import annotations

from decimal import Decimal

from thermal_app.domain.models import GC420T_DPI, PaperProfile, PrinterProfile
from thermal_app.domain.measurements import mm_to_dots


def default_paper_profiles() -> tuple[PaperProfile, ...]:
    profiles: list[PaperProfile] = []
    for width in (56, 57, 58, 80, 100):
        physical = mm_to_dots(width, GC420T_DPI)
        profiles.append(
            PaperProfile(
                id=f"paper-{width}mm",
                name=f"{width} mm",
                width_mm=Decimal(width),
                dpi=GC420T_DPI,
                printable_width_dots=physical - 24,
                margin_left_dots=12,
                margin_right_dots=12,
                margin_top_dots=12,
                margin_bottom_dots=16,
                horizontal_content_offset_dots=-7 if width == 56 else 0,
            )
        )
    return tuple(profiles)


def gc420t_profile(spooler_name: str, driver_name: str, port_name: str) -> PrinterProfile:
    return PrinterProfile(
        id="printer-gc420t",
        display_name="Zebra GC420t",
        spooler_name=spooler_name,
        driver_name=driver_name,
        port_name=port_name,
    )

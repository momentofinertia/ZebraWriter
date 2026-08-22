from __future__ import annotations

from pathlib import Path

import pytest

from thermal_app.config import project_root
from thermal_app.domain.models import PaperProfile, PrinterProfile
from thermal_app.domain.profiles import default_paper_profiles, gc420t_profile


@pytest.fixture
def printer() -> PrinterProfile:
    return gc420t_profile("ZDesigner GC420t", "ZDesigner GC420t", "USB003")


@pytest.fixture
def paper_56() -> PaperProfile:
    return default_paper_profiles()[0]


@pytest.fixture
def font_paths() -> tuple[Path, Path]:
    root = project_root() / "assets" / "fonts"
    return root / "Vera.ttf", root / "VeraBd.ttf"

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DISPLAY_NAME = "ZebraWriter"
APP_DATA_FOLDER = "ZebraWriter"


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    database: Path
    previews: Path
    bitmaps: Path
    encoded: Path
    logs: Path

    @classmethod
    def default(cls) -> "AppPaths":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA ortam değişkeni bulunamadı.")
        return cls.under(Path(local_app_data) / APP_DATA_FOLDER)

    @classmethod
    def under(cls, root: Path) -> "AppPaths":
        artifacts = root / "artifacts"
        return cls(
            root=root,
            database=root / "app.db",
            previews=artifacts / "previews",
            bitmaps=artifacts / "bitmaps",
            encoded=artifacts / "encoded",
            logs=root / "logs",
        )

    def ensure(self) -> None:
        for path in (self.root, self.previews, self.bitmaps, self.encoded, self.logs):
            path.mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[2]

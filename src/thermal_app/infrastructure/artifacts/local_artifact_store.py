from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

from thermal_app.application.dto import EncodedPayload, RenderedDocument
from thermal_app.config import AppPaths


def document_to_image(document: RenderedDocument) -> Image.Image:
    pillow_bits = bytes(value ^ 0xFF for value in document.bitmap_1bpp)
    return Image.frombytes(
        "1",
        (document.width_dots, document.height_dots),
        pillow_bits,
        "raw",
        "1",
    )


class LocalArtifactStore:
    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths

    @staticmethod
    def _atomic_bytes(path: Path, content: bytes) -> Path:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)
        return path

    def save_bitmap(self, job_id: str, document: RenderedDocument) -> Path:
        return self._atomic_bytes(self._paths.bitmaps / f"{job_id}.bin", document.bitmap_1bpp)

    def save_preview(self, job_id: str, document: RenderedDocument) -> Path:
        path = self._paths.previews / f"{job_id}.png"
        temporary = path.with_suffix(".png.tmp")
        document_to_image(document).save(temporary, format="PNG")
        os.replace(temporary, path)
        return path

    def save_encoded(self, job_id: str, payload: EncodedPayload) -> Path:
        suffix = payload.suggested_extension.lstrip(".")
        return self._atomic_bytes(self._paths.encoded / f"{job_id}.{suffix}", payload.content)

    def read_encoded(self, path: Path) -> bytes:
        return path.read_bytes()

    def delete_paths(self, paths: list[Path]) -> int:
        roots = tuple(path.resolve() for path in (self._paths.previews, self._paths.bitmaps, self._paths.encoded))
        deleted = 0
        for path in paths:
            try:
                resolved = path.resolve()
                if not any(resolved.parent == root for root in roots):
                    continue
                if resolved.is_file():
                    resolved.unlink()
                    deleted += 1
            except OSError:
                continue
        return deleted

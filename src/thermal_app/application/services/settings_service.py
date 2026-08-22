from __future__ import annotations

from thermal_app.application.ports.storage import SettingsRepository


class SettingsService:
    THEMES = ("system", "light", "dark")
    LANGUAGES = ("tr", "en")

    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    def theme(self) -> str:
        value = self._repository.get("theme", "system") or "system"
        return value if value in self.THEMES else "system"

    def set_theme(self, theme: str) -> None:
        if theme not in self.THEMES:
            raise ValueError("Bilinmeyen tema.")
        self._repository.set("theme", theme)

    def language(self) -> str:
        value = self._repository.get("language", "tr") or "tr"
        return value if value in self.LANGUAGES else "tr"

    def set_language(self, language: str) -> None:
        if language not in self.LANGUAGES:
            raise ValueError("Bilinmeyen dil.")
        self._repository.set("language", language)

    def editor_splitter_sizes(self) -> tuple[int, int]:
        raw = self._repository.get("editor_splitter_sizes", "580,420") or "580,420"
        try:
            left, right = (int(part) for part in raw.split(",", maxsplit=1))
        except (TypeError, ValueError):
            return 580, 420
        if left < 460 or right < 300:
            return 580, 420
        return left, right

    def set_editor_splitter_sizes(self, left: int, right: int) -> None:
        if left < 460 or right < 300:
            return
        self._repository.set("editor_splitter_sizes", f"{left},{right}")

    def preview_visible(self) -> bool:
        return self._repository.get("editor_preview_visible", "1") != "0"

    def set_preview_visible(self, visible: bool) -> None:
        self._repository.set("editor_preview_visible", "1" if visible else "0")

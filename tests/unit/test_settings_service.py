from thermal_app.application.services.settings_service import SettingsService


class MemorySettings:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.values.get(key, default)


def test_editor_layout_settings_round_trip_and_reject_too_small_sizes() -> None:
    repository = MemorySettings()
    service = SettingsService(repository)

    assert service.editor_splitter_sizes() == (580, 420)
    assert service.preview_visible() is True
    assert service.language() == "tr"

    service.set_editor_splitter_sizes(640, 460)
    service.set_preview_visible(False)
    service.set_language("en")
    assert service.editor_splitter_sizes() == (640, 460)
    assert service.preview_visible() is False
    assert service.language() == "en"

    service.set_editor_splitter_sizes(300, 200)
    assert service.editor_splitter_sizes() == (640, 460)


def test_invalid_stored_splitter_sizes_fall_back() -> None:
    repository = MemorySettings()
    repository.values["editor_splitter_sizes"] = "broken"
    service = SettingsService(repository)

    assert service.editor_splitter_sizes() == (580, 420)


def test_invalid_language_is_rejected_and_invalid_stored_value_falls_back() -> None:
    repository = MemorySettings()
    repository.values["language"] = "invalid"
    service = SettingsService(repository)

    assert service.language() == "tr"
    try:
        service.set_language("de")
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported language must be rejected")

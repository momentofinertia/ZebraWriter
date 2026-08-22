from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Mapping
from uuid import uuid4

from thermal_app.application.ports.storage import PresetRepository
from thermal_app.application.preset_catalog import is_built_in_preset_id
from thermal_app.domain.models import Preset


class PresetService:
    def __init__(self, repository: PresetRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[Preset]:
        return self._repository.list_all()

    def install_built_ins(self, presets: tuple[Preset, ...]) -> None:
        for preset in presets:
            existing = self._repository.get(preset.id)
            if existing is not None:
                preset = replace(
                    preset,
                    pinned=existing.pinned,
                    created_at=existing.created_at,
                )
            self._repository.save(preset)

    def save_new(
        self,
        name: str,
        template_id: str,
        paper_profile_id: str,
        input_data: Mapping[str, object],
        render_options: Mapping[str, object],
        *,
        printer_profile_id: str | None = None,
        integration_profile_id: str | None = None,
        filter_spec: Mapping[str, object] | None = None,
        sort_spec: Mapping[str, object] | None = None,
        pinned: bool = False,
    ) -> Preset:
        if not name.strip():
            raise ValueError("Preset adı boş olamaz.")
        now = datetime.now().astimezone()
        preset = Preset(
            id=str(uuid4()),
            name=name.strip(),
            template_id=template_id,
            paper_profile_id=paper_profile_id,
            printer_profile_id=printer_profile_id,
            integration_profile_id=integration_profile_id,
            filter_spec=dict(filter_spec or {}),
            sort_spec=dict(sort_spec or {}),
            input_data=dict(input_data),
            render_options=dict(render_options),
            pinned=pinned,
            created_at=now,
            updated_at=now,
        )
        self._repository.save(preset)
        return preset

    def set_pinned(self, preset_id: str, pinned: bool) -> Preset:
        preset = self._repository.get(preset_id)
        if preset is None:
            raise KeyError("Preset bulunamadı.")
        updated = replace(preset, pinned=pinned, updated_at=datetime.now().astimezone())
        self._repository.save(updated)
        return updated

    def delete(self, preset_id: str) -> bool:
        if is_built_in_preset_id(preset_id):
            raise ValueError("Hazır örnek preset silinemez; editörde açıp yeni preset olarak kaydedebilirsiniz.")
        return self._repository.delete(preset_id)

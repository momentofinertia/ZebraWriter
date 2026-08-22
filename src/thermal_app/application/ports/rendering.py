from __future__ import annotations

from typing import Mapping, Protocol

from thermal_app.application.dto import RenderedDocument, RenderOptions
from thermal_app.domain.models import PaperProfile, TemplateDefinition


class Renderer(Protocol):
    def render(
        self,
        template: TemplateDefinition,
        data: Mapping[str, object],
        paper: PaperProfile,
        options: RenderOptions,
    ) -> RenderedDocument: ...

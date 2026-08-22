from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from thermal_app.domain.models import CustomTemplate
from thermal_app.application.ports.storage import CustomTemplateRepository


class CustomTemplateService:
    def __init__(self, repository: CustomTemplateRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[CustomTemplate]:
        return self._repository.list_all()

    def get(self, template_id: str) -> CustomTemplate | None:
        return self._repository.get(template_id)

    def save(
        self,
        name: str,
        category: str,
        blocks: tuple[dict[str, object], ...],
        template_id: str | None = None,
    ) -> CustomTemplate:
        now = datetime.now().astimezone()
        existing = self._repository.get(template_id) if template_id else None
        template = CustomTemplate(
            id=template_id or f"custom-{uuid4()}",
            name=name.strip(),
            category=category.strip() or "Özel",
            blocks=tuple(dict(block) for block in blocks),
            created_at=existing.created_at if existing else now,
            updated_at=now,
            version=(existing.version + 1) if existing else 1,
        )
        self._repository.save(template)
        return template

    def delete(self, template_id: str) -> bool:
        return self._repository.delete(template_id)

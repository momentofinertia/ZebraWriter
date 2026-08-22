from __future__ import annotations

from typing import Mapping, Protocol


class TodoistGateway(Protocol):
    def validate_token(self, token: str) -> None: ...
    def get_projects(self, token: str) -> list[Mapping[str, object]]: ...
    def get_tasks(
        self,
        token: str,
        *,
        filter_query: str | None = None,
        project_id: str | None = None,
    ) -> list[Mapping[str, object]]: ...

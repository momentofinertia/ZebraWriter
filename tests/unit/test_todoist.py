from __future__ import annotations

from pathlib import Path

import pytest

from thermal_app.application.services.todoist_service import TodoistService
from thermal_app.domain.errors import TodoistAuthError, TodoistNetworkError, TodoistRateLimitError
from thermal_app.infrastructure.storage.database import Database
from thermal_app.infrastructure.storage.repositories import (
    SqliteIntegrationProfileRepository,
    SqliteTodoistCacheRepository,
)


class FakeCredentials:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def save(self, reference: str, secret: str) -> None:
        self.values[reference] = secret

    def get(self, reference: str) -> str | None:
        return self.values.get(reference)

    def delete(self, reference: str) -> None:
        self.values.pop(reference, None)


class FakeGateway:
    offline = False
    rate_limited = False
    unauthorized = False

    def validate_token(self, token: str) -> None:
        assert token == "top-secret-token"

    def get_projects(self, token: str) -> list[dict[str, object]]:
        if self.unauthorized:
            raise TodoistAuthError("yetkisiz")
        if self.rate_limited:
            raise TodoistRateLimitError("sınır aşıldı")
        if self.offline:
            raise TodoistNetworkError("çevrimdışı")
        return [{"id": "p1", "name": "Ev"}]

    def get_tasks(self, token: str, **kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "id": "t1",
                "content": "Süt al",
                "description": "Tam yağlı",
                "checked": False,
                "priority": 1,
                "project_id": "p1",
                "labels": ["market"],
                "due": {"date": "2026-08-22T18:30:00"},
            }
        ]


def build_service(tmp_path: Path) -> tuple[TodoistService, FakeGateway, FakeCredentials, Path]:
    database_path = tmp_path / "app.db"
    database = Database(database_path)
    database.initialize()
    gateway = FakeGateway()
    credentials = FakeCredentials()
    service = TodoistService(
        gateway,
        credentials,
        SqliteIntegrationProfileRepository(database),
        SqliteTodoistCacheRepository(database),
    )
    return service, gateway, credentials, database_path


def test_todoist_online_mapping_cache_and_secret_storage(tmp_path: Path) -> None:
    service, gateway, credentials, database_path = build_service(tmp_path)
    service.connect(" top-secret-token ")
    result = service.sync("today")
    assert result.stale is False
    assert result.tasks[0].title == "Süt al"
    assert result.tasks[0].due_time == "18:30"
    assert result.tasks[0].project == "Ev"
    assert b"top-secret-token" not in database_path.read_bytes()
    assert credentials.values

    gateway.offline = True
    cached = service.sync("today")
    assert cached.stale is True
    assert cached.source == "cache"
    assert cached.tasks == result.tasks


def test_todoist_template_mapping_marks_stale_cache(tmp_path: Path) -> None:
    service, gateway, _credentials, _database_path = build_service(tmp_path)
    service.connect("top-secret-token")
    service.sync("today")
    gateway.offline = True
    cached = service.sync("today")
    data = service.to_todo_input(cached, "Bugün")
    assert data["priority_tasks"] == ["Süt al"]
    assert "Offline cache" in str(data["note"])


def test_supported_todoist_filters_are_translated() -> None:
    assert TodoistService._filter_query("today", "") == "today"
    assert TodoistService._filter_query("overdue", "") == "overdue"
    assert TodoistService._filter_query("today_overdue", "") == "today | overdue"
    assert TodoistService._filter_query("upcoming", "") == "next 7 days"
    assert TodoistService._filter_query("label", "market") == "@market"
    assert TodoistService._filter_query("priority", "1") == "p1"
    assert TodoistService._filter_query("custom", "no date & @home") == "no date & @home"


def test_rate_limit_uses_explicit_stale_cache_but_auth_does_not(tmp_path: Path) -> None:
    service, gateway, _credentials, _database_path = build_service(tmp_path)
    service.connect("top-secret-token")
    service.sync("today")

    gateway.rate_limited = True
    cached = service.sync("today")
    assert cached.stale is True
    assert cached.warning == "sınır aşıldı"

    gateway.rate_limited = False
    gateway.unauthorized = True
    with pytest.raises(TodoistAuthError):
        service.sync("today")

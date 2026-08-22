from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
from typing import Mapping

from thermal_app.application.dto import TodoistSyncResult
from thermal_app.application.ports.integrations import TodoistGateway
from thermal_app.application.ports.storage import (
    CredentialStore,
    IntegrationProfileRepository,
    TodoistCacheRepository,
)
from thermal_app.domain.errors import (
    TodoistAuthError,
    TodoistNetworkError,
    TodoistRateLimitError,
)
from thermal_app.domain.models import IntegrationProfile, TaskItem, TodoistCacheEntry


TODOIST_PROFILE_ID = "todoist-personal"
TODOIST_CREDENTIAL_REFERENCE = "todoist.personal.api-token"


class TodoistService:
    def __init__(
        self,
        gateway: TodoistGateway,
        credentials: CredentialStore,
        profiles: IntegrationProfileRepository,
        cache: TodoistCacheRepository,
    ) -> None:
        self._gateway = gateway
        self._credentials = credentials
        self._profiles = profiles
        self._cache = cache

    def profile(self) -> IntegrationProfile | None:
        return self._profiles.get(TODOIST_PROFILE_ID)

    def connect(self, token: str) -> IntegrationProfile:
        clean_token = token.strip()
        self._gateway.validate_token(clean_token)
        self._credentials.save(TODOIST_CREDENTIAL_REFERENCE, clean_token)
        profile = IntegrationProfile(
            id=TODOIST_PROFILE_ID,
            provider_type="todoist",
            display_name="Todoist Kişisel Token",
            enabled=True,
            credential_reference=TODOIST_CREDENTIAL_REFERENCE,
            last_synced_at=None,
            last_sync_status="connected",
            settings_without_secrets={"api_version": "v1"},
        )
        self._profiles.save(profile)
        return profile

    def disconnect(self) -> None:
        profile = self.profile()
        self._credentials.delete(TODOIST_CREDENTIAL_REFERENCE)
        if profile:
            self._profiles.save(
                replace(
                    profile,
                    enabled=False,
                    credential_reference=None,
                    last_sync_status="disconnected",
                )
            )

    def list_projects(self) -> dict[str, str]:
        profile = self.profile()
        reference = profile.credential_reference if profile else TODOIST_CREDENTIAL_REFERENCE
        token = self._credentials.get(reference or TODOIST_CREDENTIAL_REFERENCE)
        if not token:
            raise TodoistAuthError("Todoist bağlantısı kurulmamış.")
        return {
            str(item.get("id", "")): str(item.get("name", ""))
            for item in self._gateway.get_projects(token)
            if item.get("id")
        }

    def sync(
        self,
        mode: str,
        *,
        project_id: str | None = None,
        filter_value: str | None = None,
    ) -> TodoistSyncResult:
        profile = self.profile()
        reference = profile.credential_reference if profile else TODOIST_CREDENTIAL_REFERENCE
        token = self._credentials.get(reference or TODOIST_CREDENTIAL_REFERENCE)
        if not token:
            raise TodoistAuthError("Todoist bağlantısı kurulmamış.")
        clean_filter_value = (filter_value or "").strip()
        cache_key = self._cache_key(mode, project_id, clean_filter_value)
        try:
            raw_projects = self._gateway.get_projects(token)
            projects = {
                str(item.get("id", "")): str(item.get("name", ""))
                for item in raw_projects
                if item.get("id")
            }
            filter_query = self._filter_query(mode, clean_filter_value)
            if mode == "project" and not project_id:
                raise ValueError("Todoist proje filtresi için bir proje seçilmelidir.")
            raw_tasks = self._gateway.get_tasks(
                token,
                filter_query=filter_query,
                project_id=project_id if mode == "project" else None,
            )
            tasks = tuple(self._map_task(item, projects) for item in raw_tasks)
            synced_at = datetime.now().astimezone()
            self._cache.save(
                TodoistCacheEntry(
                    cache_key=cache_key,
                    payload={
                        "tasks": [asdict(task) for task in tasks],
                        "projects": projects,
                    },
                    synced_at=synced_at,
                )
            )
            if profile:
                self._profiles.save(
                    replace(profile, last_synced_at=synced_at, last_sync_status="ok")
                )
            return TodoistSyncResult(tasks, projects, synced_at, False, "online")
        except (TodoistNetworkError, TodoistRateLimitError) as exc:
            cached = self._cache.get(cache_key)
            if cached is None:
                raise
            result = self._from_cache(cached, warning=str(exc))
            if profile:
                self._profiles.save(
                    replace(
                        profile,
                        last_sync_status="stale-cache",
                    )
                )
            return result

    @staticmethod
    def _cache_key(mode: str, project_id: str | None, filter_value: str = "") -> str:
        return f"todoist:{mode}:{project_id or '-'}:{filter_value or '-'}"

    @staticmethod
    def _filter_query(mode: str, filter_value: str) -> str | None:
        fixed = {
            "today": "today",
            "overdue": "overdue",
            "today_overdue": "today | overdue",
            "upcoming": "next 7 days",
        }
        if mode in fixed:
            return fixed[mode]
        if mode == "project":
            return None
        if mode == "label":
            if not filter_value:
                raise ValueError("Todoist etiket filtresi boş olamaz.")
            return filter_value if filter_value.startswith("@") else f"@{filter_value}"
        if mode == "priority":
            normalized = filter_value.lower().removeprefix("p")
            if normalized not in {"1", "2", "3", "4"}:
                raise ValueError("Todoist önceliği 1, 2, 3 veya 4 olmalıdır.")
            return f"p{normalized}"
        if mode == "custom":
            if not filter_value:
                raise ValueError("Todoist özel filtresi boş olamaz.")
            return filter_value
        raise ValueError(f"Desteklenmeyen Todoist filtresi: {mode}")

    @staticmethod
    def _map_task(payload: Mapping[str, object], projects: Mapping[str, str]) -> TaskItem:
        due = payload.get("due") if isinstance(payload.get("due"), Mapping) else {}
        due_value = str(due.get("date", "")) if isinstance(due, Mapping) else ""
        due_date = due_value[:10] or None
        due_time = None
        if "T" in due_value:
            due_time = due_value.split("T", 1)[1][:5]
        project_id = str(payload.get("project_id", ""))
        labels = payload.get("labels", [])
        return TaskItem(
            id=str(payload.get("id", "")),
            title=str(payload.get("content", "")),
            description=str(payload.get("description", "")) or None,
            completed=bool(payload.get("checked", False)),
            priority=int(payload.get("priority", 1)),
            due_date=due_date,
            due_time=due_time,
            project=projects.get(project_id),
            labels=tuple(str(label) for label in labels) if isinstance(labels, list) else (),
            source="todoist",
            source_id=str(payload.get("id", "")),
        )

    @staticmethod
    def _from_cache(entry: TodoistCacheEntry, *, warning: str) -> TodoistSyncResult:
        raw_tasks = entry.payload.get("tasks", [])
        tasks: list[TaskItem] = []
        if isinstance(raw_tasks, list):
            for raw in raw_tasks:
                if isinstance(raw, dict):
                    tasks.append(
                        TaskItem(
                            **{
                                **raw,
                                "labels": tuple(str(label) for label in raw.get("labels", [])),
                            }
                        )
                    )
        raw_projects = entry.payload.get("projects", {})
        projects = (
            {str(key): str(value) for key, value in raw_projects.items()}
            if isinstance(raw_projects, dict)
            else {}
        )
        return TodoistSyncResult(
            tuple(tasks),
            projects,
            entry.synced_at,
            True,
            "cache",
            warning,
        )

    @staticmethod
    def to_todo_input(result: TodoistSyncResult, title: str) -> dict[str, object]:
        active = [task for task in result.tasks if not task.completed]
        ordered = sorted(active, key=lambda task: (task.priority, task.due_time or "99:99", task.title))
        return {
            "title": title,
            "date": result.synced_at.strftime("%d.%m.%Y"),
            "priority_tasks": [task.title for task in ordered[:3]],
            "tasks": [
                {
                    "title": task.title,
                    "due_time": task.due_time or "",
                    "category": task.project or "",
                }
                for task in ordered[3:]
            ],
            "note": (
                f"Offline cache: {result.synced_at:%d.%m.%Y %H:%M}"
                if result.stale
                else "Todoist ile senkronize edildi."
            ),
            "show_checkboxes": True,
        }

    @staticmethod
    def to_shopping_input(result: TodoistSyncResult, project_name: str) -> dict[str, object]:
        return {
            "title": project_name,
            "date": result.synced_at.strftime("%d.%m.%Y"),
            "items": [
                {
                    "product": task.title,
                    "quantity": "",
                    "category": task.labels[0] if task.labels else "Todoist",
                }
                for task in result.tasks
                if not task.completed
            ],
            "show_checkboxes": True,
        }

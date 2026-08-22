from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from thermal_app.domain.errors import (
    TodoistAuthError,
    TodoistError,
    TodoistNetworkError,
    TodoistRateLimitError,
)


class TodoistApiV1Client:
    BASE_URL = "https://api.todoist.com/api/v1"

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urlopen,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._opener = opener
        self._timeout = timeout_seconds

    def validate_token(self, token: str) -> None:
        self._request("/projects", token, {"limit": "1"})

    def get_projects(self, token: str) -> list[Mapping[str, object]]:
        return self._paginate("/projects", token, result_key="results")

    def get_tasks(
        self,
        token: str,
        *,
        filter_query: str | None = None,
        project_id: str | None = None,
    ) -> list[Mapping[str, object]]:
        if filter_query:
            return self._paginate(
                "/tasks/filter",
                token,
                result_key="results",
                params={"query": filter_query},
            )
        params = {"project_id": project_id} if project_id else None
        return self._paginate("/tasks", token, result_key="results", params=params)

    def _paginate(
        self,
        path: str,
        token: str,
        *,
        result_key: str,
        params: Mapping[str, str | None] | None = None,
    ) -> list[Mapping[str, object]]:
        output: list[Mapping[str, object]] = []
        cursor: str | None = None
        for _page in range(100):
            query = {key: value for key, value in dict(params or {}).items() if value is not None}
            query["limit"] = "200"
            if cursor:
                query["cursor"] = cursor
            payload = self._request(path, token, query)
            values = payload.get(result_key, []) if isinstance(payload, dict) else []
            if not isinstance(values, list):
                raise TodoistError("Todoist yanıt biçimi beklenen görev listesini içermiyor.")
            output.extend(value for value in values if isinstance(value, dict))
            cursor_value = payload.get("next_cursor") if isinstance(payload, dict) else None
            cursor = str(cursor_value) if cursor_value else None
            if not cursor:
                return output
        raise TodoistError("Todoist sayfalaması güvenlik sınırını aştı.")

    def _request(
        self,
        path: str,
        token: str,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        if not token.strip():
            raise TodoistAuthError("Todoist tokenı bulunamadı.")
        url = f"{self.BASE_URL}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "ZebraWriter/0.1",
            },
            method="GET",
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise TodoistAuthError("Todoist tokenı geçersiz veya yetkisiz.") from exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After", "bilinmiyor")
                raise TodoistRateLimitError(
                    f"Todoist istek sınırı aşıldı; tekrar süresi: {retry_after}."
                ) from exc
            raise TodoistError(f"Todoist API isteği başarısız oldu (HTTP {exc.code}).") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise TodoistNetworkError("Todoist ağına ulaşılamadı.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TodoistError("Todoist geçersiz JSON yanıtı döndürdü.") from exc
        if not isinstance(decoded, dict):
            raise TodoistError("Todoist yanıt biçimi beklenmiyor.")
        return decoded

from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from thermal_app.domain.errors import TodoistAuthError, TodoistRateLimitError
from thermal_app.infrastructure.todoist_client import TodoistApiV1Client


class Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_api_v1_client_follows_cursor_pagination() -> None:
    urls: list[str] = []

    def opener(request: object, timeout: float) -> Response:
        url = request.full_url
        urls.append(url)
        if "cursor=" in url:
            return Response({"results": [{"id": "2"}], "next_cursor": None})
        return Response({"results": [{"id": "1"}], "next_cursor": "next"})

    tasks = TodoistApiV1Client(opener=opener).get_tasks("token", filter_query="today")
    assert [task["id"] for task in tasks] == ["1", "2"]
    assert all("/api/v1/tasks/filter" in url for url in urls)
    assert "query=today" in urls[0]


def test_api_v1_client_maps_unauthorized_without_exposing_token() -> None:
    def opener(request: object, timeout: float) -> Response:
        raise HTTPError(request.full_url, 401, "unauthorized", {}, io.BytesIO())

    with pytest.raises(TodoistAuthError, match="geçersiz") as captured:
        TodoistApiV1Client(opener=opener).validate_token("do-not-leak")
    assert "do-not-leak" not in str(captured.value)


def test_api_v1_client_maps_rate_limit() -> None:
    def opener(request: object, timeout: float) -> Response:
        raise HTTPError(
            request.full_url,
            429,
            "rate limited",
            {"Retry-After": "30"},
            io.BytesIO(),
        )

    with pytest.raises(TodoistRateLimitError, match="30"):
        TodoistApiV1Client(opener=opener).get_tasks("token")

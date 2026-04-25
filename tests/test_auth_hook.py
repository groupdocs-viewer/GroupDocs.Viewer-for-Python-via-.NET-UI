"""Tests for ``create_app(auth_check=...)`` — applied to /viewer-api/* only."""
from pathlib import Path

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.testclient import TestClient

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.storage.local import LocalFileStorage


async def _allow_only_with_token(request: Request) -> None:
    if request.query_params.get("token") != "let-me-in":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _make_app(tmp_path: Path, fake_viewer, *, auth_check=None):
    return create_app(
        Config(),
        storage=LocalFileStorage(tmp_path),
        viewer=fake_viewer,
        auth_check=auth_check,
    )


def test_auth_check_blocks_unauthorized_api_request(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer, auth_check=_allow_only_with_token)
    with TestClient(app) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 401


def test_auth_check_allows_authorized_api_request(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer, auth_check=_allow_only_with_token)
    with TestClient(app) as client:
        response = client.post(
            "/viewer-api/list-dir?token=let-me-in", json={"path": ""}
        )
        assert response.status_code == 200


def test_auth_check_does_not_guard_health(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer, auth_check=_allow_only_with_token)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_auth_check_does_not_guard_spa_index(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer, auth_check=_allow_only_with_token)
    with TestClient(app) as client:
        response = client.get("/viewer/")
        assert response.status_code == 200


def test_auth_check_does_not_guard_spa_static_assets(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer, auth_check=_allow_only_with_token)
    with TestClient(app) as client:
        response = client.get("/viewer/main.js")
        assert response.status_code == 200


def test_no_auth_check_means_open_api(tmp_path, fake_viewer):
    app = _make_app(tmp_path, fake_viewer)  # default auth_check=None
    with TestClient(app) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_check_can_inspect_headers(tmp_path, fake_viewer):
    seen_headers: list[str] = []

    async def capture_auth(request: Request) -> None:
        seen_headers.append(request.headers.get("x-trace-id", ""))

    app = _make_app(tmp_path, fake_viewer, auth_check=capture_auth)
    with TestClient(app) as client:
        client.post(
            "/viewer-api/list-dir",
            json={"path": ""},
            headers={"x-trace-id": "abc123"},
        )
    assert seen_headers == ["abc123"]

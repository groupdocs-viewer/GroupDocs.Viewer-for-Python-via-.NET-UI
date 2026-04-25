from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.storage.local import LocalFileStorage


def test_create_app_returns_starlette():
    assert isinstance(create_app(), Starlette)


def test_create_app_stores_config():
    cfg = Config(preload_pages=7)
    app = create_app(cfg)
    assert app.state.config.preload_pages == 7


def test_health_endpoint():
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body


def test_spa_index_renders_template_substitutions():
    cfg = Config(ui_title="My Viewer")
    with TestClient(create_app(cfg)) as client:
        response = client.get("/viewer/")
        assert response.status_code == 200
        body = response.text
        # Title substitution
        assert "<title>My Viewer</title>" in body
        # base href substitution
        assert 'href="/viewer/"' in body
        # window.groupdocs.viewer config object replaced — placeholders gone
        assert "#uiConfig#" not in body
        assert "#uiPath#" not in body
        assert "#uiTitle#" not in body
        assert "#customCSS#" not in body
        assert "#customJS#" not in body
        # SPA config carries the API endpoint and a sentinel field
        assert '"apiEndpoint": "/viewer-api"' in body
        assert '"renderingMode": "html"' in body
        assert '"initialZoom": "Fit Page"' in body


def test_spa_static_assets_served():
    with TestClient(create_app()) as client:
        response = client.get("/viewer/main.js")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/javascript")


def test_custom_logo_image_path_serves_supplied_bytes(tmp_path: Path):
    custom_logo = tmp_path / "logo.svg"
    custom_logo.write_bytes(b"<svg id='custom-logo'/>")
    cfg = Config(custom_logo_image_path=str(custom_logo))
    with TestClient(create_app(cfg)) as client:
        response = client.get("/viewer/assets/ui/logo-image.svg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.content == b"<svg id='custom-logo'/>"


def test_hide_logo_text_serves_empty_svg():
    cfg = Config(hide_logo_text=True)
    with TestClient(create_app(cfg)) as client:
        response = client.get("/viewer/assets/ui/logo-text.svg")
        assert response.status_code == 200
        assert response.content == b'<svg xmlns="http://www.w3.org/2000/svg"/>'


def test_no_logo_override_falls_through_to_vendored_static():
    with TestClient(create_app(Config())) as client:
        response = client.get("/viewer/assets/ui/logo-image.svg")
        assert response.status_code == 200
        # The vendored logo is non-empty real SVG, not the override placeholder.
        assert response.content != b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        assert len(response.content) > 50


def test_api_routes_are_present_when_storage_and_viewer_supplied(
    tmp_path: Path, fake_viewer
):
    storage = LocalFileStorage(tmp_path)
    app = create_app(Config(), storage=storage, viewer=fake_viewer)
    with TestClient(app) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 200
        assert response.json() == []


def test_api_routes_skipped_without_storage_and_viewer():
    app = create_app(Config())
    with TestClient(app) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 404


@pytest.fixture
def fake_viewer():
    # Fixture imported from conftest is preferred but kept here as a
    # safety net to avoid surprises if conftest isn't picked up.
    from tests.conftest import FakeViewer
    return FakeViewer()

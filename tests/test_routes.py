"""Integration tests for the 9 viewer API endpoints, driven by FakeViewer."""
from __future__ import annotations

import io
from pathlib import Path

from starlette.testclient import TestClient

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.storage.local import LocalFileStorage


def _client(tmp_path: Path, viewer, **config_overrides):
    cfg = Config(**config_overrides)
    storage = LocalFileStorage(tmp_path)
    return TestClient(create_app(cfg, storage=storage, viewer=viewer))


def test_list_dir_returns_files_camel_case(tmp_path: Path, fake_viewer):
    (tmp_path / "a.docx").write_bytes(b"x" * 4)
    (tmp_path / "sub").mkdir()
    with _client(tmp_path, fake_viewer) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 200
        items = response.json()
        assert items == [
            {"path": "sub", "name": "sub", "isDir": True, "size": 0},
            {"path": "a.docx", "name": "a.docx", "isDir": False, "size": 4},
        ]


def test_list_dir_returns_500_when_disabled(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer, enable_file_browser=False) as client:
        response = client.post("/viewer-api/list-dir", json={"path": ""})
        assert response.status_code == 500


def test_upload_file_saves_to_storage(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.post(
            "/viewer-api/upload-file",
            files={"file": ("upload.txt", io.BytesIO(b"hi"), "text/plain")},
        )
        assert response.status_code == 200
        assert response.json() == {"file": "upload.txt"}
        assert (tmp_path / "upload.txt").read_bytes() == b"hi"


def test_view_data_returns_pages_with_urls(tmp_path: Path, fake_viewer):
    (tmp_path / "a.docx").write_bytes(b"x")
    with _client(tmp_path, fake_viewer, preload_pages=2) as client:
        response = client.post(
            "/viewer-api/view-data", json={"file": "a.docx"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["file"] == "a.docx"
        assert body["fileType"] == "docx"
        assert body["fileName"] == "a.docx"
        assert body["canPrint"] is True
        # 3 pages total (FakeViewer default), preload=2 → first two have URLs
        assert len(body["pages"]) == 3
        assert body["pages"][0]["pageUrl"] == "/get-page?file=a.docx&page=1"
        assert body["pages"][0]["thumbUrl"] == "/get-thumb?file=a.docx&page=1"
        assert body["pages"][1]["pageUrl"] == "/get-page?file=a.docx&page=2"
        assert body["pages"][2]["pageUrl"] is None
        assert body["pages"][2]["thumbUrl"] is None


def test_view_data_returns_403_on_password_error(tmp_path: Path):
    from tests.conftest import FakeViewer

    viewer = FakeViewer(password_required=True)
    with _client(tmp_path, viewer) as client:
        response = client.post("/viewer-api/view-data", json={"file": "a.docx"})
        assert response.status_code == 403
        assert response.json() == {"error": "Password Required"}

        response2 = client.post(
            "/viewer-api/view-data",
            json={"file": "a.docx", "password": "wrong"},
        )
        assert response2.status_code == 403
        assert response2.json() == {"error": "Incorrect Password"}


def test_create_pages_returns_only_requested(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.post(
            "/viewer-api/create-pages",
            json={"file": "a.docx", "pages": [2]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["number"] == 2
        assert body[0]["pageUrl"] == "/get-page?file=a.docx&page=2"


def test_create_pdf_returns_pdf_url(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.post("/viewer-api/create-pdf", json={"file": "a.docx"})
        assert response.status_code == 200
        assert response.json() == {"pdfUrl": "/get-pdf?file=a.docx"}


def test_get_page_returns_html_bytes(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.get("/viewer-api/get-page?file=a.docx&page=2")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.content == b"<html>page 2</html>"


def test_get_thumb_returns_png_bytes(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.get("/viewer-api/get-thumb?file=a.docx&page=1")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert response.content == b"\x89PNG-fake"


def test_get_pdf_sets_attachment_disposition(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer) as client:
        response = client.get("/viewer-api/get-pdf?file=a.docx")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert "a.pdf" in response.headers["content-disposition"]


def test_get_resource_returns_bytes_with_inferred_content_type(
    tmp_path: Path, fake_viewer
):
    with _client(tmp_path, fake_viewer) as client:
        response = client.get(
            "/viewer-api/get-resource?file=a.docx&page=1&resource=styles.css"
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/css")
        assert response.content == b"/* styles.css */"


def test_get_resource_404_when_image_mode(tmp_path: Path, fake_viewer):
    with _client(tmp_path, fake_viewer, rendering_mode="image") as client:
        response = client.get(
            "/viewer-api/get-resource?file=a.docx&page=1&resource=img.png"
        )
        assert response.status_code == 500

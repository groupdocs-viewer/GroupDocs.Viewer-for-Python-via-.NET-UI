"""End-to-end tests: real ``SelfHostViewer`` + real ``groupdocs.viewer`` library
+ real DOCX fixture, exercised through the actual HTTP layer.

Skipped when ``groupdocs-viewer-net`` isn't installed (most dev environments
won't have it; CI installs it explicitly via the optional extra).

These tests are slower than the rest of the suite — each render spins up
the .NET runtime and does real document parsing — so we keep them lean:
one document, one HTML render path, one image render path, one PDF.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from starlette.testclient import TestClient

pytest.importorskip("groupdocs.viewer")

from groupdocs_viewer_ui import Config, create_app  # noqa: E402
from groupdocs_viewer_ui.cache.memory import InMemoryCache  # noqa: E402
from groupdocs_viewer_ui.storage.local import LocalFileStorage  # noqa: E402
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_DOCX = FIXTURES / "sample.docx"

if not SAMPLE_DOCX.is_file():
    pytest.skip(f"sample fixture missing at {SAMPLE_DOCX}", allow_module_level=True)


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    """Per-test copy of the fixtures so concurrent tests don't fight."""
    target = tmp_path / "docs"
    target.mkdir()
    shutil.copy(SAMPLE_DOCX, target / "sample.docx")
    return target


def _client(docs_dir: Path, *, rendering_mode: str = "html") -> TestClient:
    storage = LocalFileStorage(docs_dir)
    app = create_app(
        Config(rendering_mode=rendering_mode),  # type: ignore[arg-type]
        storage=storage,
        cache=InMemoryCache(),
        viewer=SelfHostViewer(rendering_mode=rendering_mode, storage=storage),
    )
    return TestClient(app)


def test_view_data_returns_real_document_metadata(docs_dir: Path):
    with _client(docs_dir) as client:
        response = client.post(
            "/viewer-api/view-data", json={"file": "sample.docx"}
        )
        assert response.status_code == 200, response.text
        body = response.json()

    assert body["fileName"] == "sample.docx"
    assert body["fileType"].lower() == "docx"
    assert body["canPrint"] is True
    assert isinstance(body["pages"], list)
    assert len(body["pages"]) >= 1
    # Preloaded pages must carry URLs the SPA can fetch.
    first = body["pages"][0]
    assert first["number"] == 1
    assert first["width"] > 0
    assert first["height"] > 0
    assert first["pageUrl"].startswith("/get-page?file=sample.docx&page=1")


def test_get_page_returns_real_html_in_html_mode(docs_dir: Path):
    with _client(docs_dir) as client:
        # Trigger render via view-data first so the cache is warm — also
        # the order the SPA actually uses.
        client.post("/viewer-api/view-data", json={"file": "sample.docx"})
        page = client.get("/viewer-api/get-page?file=sample.docx&page=1")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert len(page.content) > 100, "rendered HTML page is suspiciously small"
    # Embedded-resources mode bakes CSS into the HTML — at minimum the
    # output should look like an HTML document.
    body_text = page.content.decode("utf-8", errors="replace")
    assert "<html" in body_text.lower() or "<!doctype html" in body_text.lower()


def test_get_page_returns_real_png_in_image_mode(docs_dir: Path):
    with _client(docs_dir, rendering_mode="image") as client:
        client.post("/viewer-api/view-data", json={"file": "sample.docx"})
        page = client.get("/viewer-api/get-page?file=sample.docx&page=1")

    assert page.status_code == 200
    assert page.headers["content-type"] == "image/png"
    # Real PNG starts with the 8-byte magic signature.
    assert page.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_get_pdf_returns_real_pdf(docs_dir: Path):
    with _client(docs_dir) as client:
        # CreatePdf primes the cache and returns the URL...
        create = client.post("/viewer-api/create-pdf", json={"file": "sample.docx"})
        assert create.status_code == 200, create.text
        pdf_url = create.json()["pdfUrl"]
        assert pdf_url.startswith("/get-pdf?file=sample.docx")

        # ...then the actual download serves the bytes.
        download = client.get("/viewer-api" + pdf_url)

    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert "attachment" in download.headers["content-disposition"]
    # Real PDF starts with "%PDF-"
    assert download.content.startswith(b"%PDF-")


def test_get_thumb_returns_image_bytes(docs_dir: Path):
    with _client(docs_dir) as client:
        client.post("/viewer-api/view-data", json={"file": "sample.docx"})
        thumb = client.get("/viewer-api/get-thumb?file=sample.docx&page=1")

    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/png"
    assert thumb.content[:8] == b"\x89PNG\r\n\x1a\n"

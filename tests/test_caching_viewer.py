import pytest

from groupdocs_viewer_ui.cache.memory import InMemoryCache
from groupdocs_viewer_ui.viewer.caching import CachingViewer
from groupdocs_viewer_ui.viewer.entities import FileCredentials

CREDS = FileCredentials(file_path="/a.docx")


def _calls(viewer, name):
    return [c for c in viewer.calls if c[0] == name]


@pytest.mark.asyncio
async def test_get_document_info_caches_and_round_trips(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())

    first = await cv.get_document_info(CREDS)
    second = await cv.get_document_info(CREDS)

    assert first == second
    assert len(_calls(fake_viewer, "get_document_info")) == 1


@pytest.mark.asyncio
async def test_get_page_caches(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())

    page1 = await cv.get_page(CREDS, 1)
    page1_again = await cv.get_page(CREDS, 1)

    assert page1.data == page1_again.data
    assert len(_calls(fake_viewer, "get_page")) == 1


@pytest.mark.asyncio
async def test_get_pages_only_renders_misses(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())

    # Warm pages 1 and 2
    await cv.get_pages(CREDS, [1, 2])
    fake_viewer.calls.clear()

    # Ask for 1, 2, 3 — only 3 should be sent to the inner viewer
    pages = await cv.get_pages(CREDS, [1, 2, 3])
    assert [p.number for p in pages] == [1, 2, 3]
    batch_calls = _calls(fake_viewer, "get_pages")
    assert len(batch_calls) == 1
    assert batch_calls[0][1] == ("/a.docx", (3,))


@pytest.mark.asyncio
async def test_get_pages_skips_inner_call_when_fully_cached(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())
    await cv.get_pages(CREDS, [1, 2])
    fake_viewer.calls.clear()

    pages = await cv.get_pages(CREDS, [1, 2])
    assert [p.number for p in pages] == [1, 2]
    assert _calls(fake_viewer, "get_pages") == []


@pytest.mark.asyncio
async def test_get_pdf_caches(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())
    pdf1 = await cv.get_pdf(CREDS)
    pdf2 = await cv.get_pdf(CREDS)
    assert pdf1 == pdf2
    assert len(_calls(fake_viewer, "get_pdf")) == 1


@pytest.mark.asyncio
async def test_get_thumbs_only_renders_misses(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())
    await cv.get_thumbs(CREDS, [1])
    fake_viewer.calls.clear()
    thumbs = await cv.get_thumbs(CREDS, [1, 2])
    assert [t.number for t in thumbs] == [1, 2]
    batch = _calls(fake_viewer, "get_thumbs")
    assert len(batch) == 1
    assert batch[0][1] == ("/a.docx", (2,))


@pytest.mark.asyncio
async def test_extensions_pass_through(fake_viewer):
    cv = CachingViewer(fake_viewer, InMemoryCache())
    assert cv.page_extension == fake_viewer.page_extension
    assert cv.thumb_extension == fake_viewer.thumb_extension


@pytest.mark.asyncio
async def test_create_app_wraps_viewer_when_cache_supplied(tmp_path, fake_viewer):
    from starlette.testclient import TestClient

    from groupdocs_viewer_ui import Config, create_app
    from groupdocs_viewer_ui.storage.local import LocalFileStorage

    cache = InMemoryCache()
    app = create_app(
        Config(),
        storage=LocalFileStorage(tmp_path),
        cache=cache,
        viewer=fake_viewer,
    )
    # The state-stored viewer should be the wrapping CachingViewer, not the raw fake.
    assert isinstance(app.state.viewer, CachingViewer)

    with TestClient(app) as client:
        client.get("/viewer-api/get-page?file=a.docx&page=1")
        client.get("/viewer-api/get-page?file=a.docx&page=1")
    assert len(_calls(fake_viewer, "get_page")) == 1

import pytest

from groupdocs_viewer_ui.cache.memory import InMemoryCache


@pytest.mark.asyncio
async def test_returns_none_for_missing_key():
    cache = InMemoryCache()
    assert await cache.try_get("p1.html", "/a.docx") is None


@pytest.mark.asyncio
async def test_set_then_get_round_trips():
    cache = InMemoryCache()
    await cache.set("p1.html", "/a.docx", b"<html>hi</html>")
    assert await cache.try_get("p1.html", "/a.docx") == b"<html>hi</html>"


@pytest.mark.asyncio
async def test_keyed_by_both_path_and_cache_key():
    cache = InMemoryCache()
    await cache.set("p1.html", "/a.docx", b"A")
    await cache.set("p1.html", "/b.docx", b"B")
    await cache.set("p2.html", "/a.docx", b"C")
    assert await cache.try_get("p1.html", "/a.docx") == b"A"
    assert await cache.try_get("p1.html", "/b.docx") == b"B"
    assert await cache.try_get("p2.html", "/a.docx") == b"C"


@pytest.mark.asyncio
async def test_remove_clears_only_target_file():
    cache = InMemoryCache()
    await cache.set("p1.html", "/a.docx", b"A")
    await cache.set("p2.html", "/a.docx", b"A2")
    await cache.set("p1.html", "/b.docx", b"B")

    await cache.remove("/a.docx")

    assert await cache.try_get("p1.html", "/a.docx") is None
    assert await cache.try_get("p2.html", "/a.docx") is None
    assert await cache.try_get("p1.html", "/b.docx") == b"B"

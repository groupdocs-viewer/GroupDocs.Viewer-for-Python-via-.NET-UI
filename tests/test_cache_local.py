from pathlib import Path

import pytest

from groupdocs_viewer_ui.cache.local import LocalFileCache


@pytest.mark.asyncio
async def test_returns_none_for_missing_key(tmp_path: Path):
    cache = LocalFileCache(tmp_path)
    assert await cache.try_get("p1.html", "/a.docx") is None


@pytest.mark.asyncio
async def test_set_then_get_round_trips(tmp_path: Path):
    cache = LocalFileCache(tmp_path)
    await cache.set("p1.html", "/a.docx", b"<html>hi</html>")
    assert await cache.try_get("p1.html", "/a.docx") == b"<html>hi</html>"


@pytest.mark.asyncio
async def test_persists_across_instances(tmp_path: Path):
    await LocalFileCache(tmp_path).set("p1.html", "/a.docx", b"persisted")
    fresh = LocalFileCache(tmp_path)
    assert await fresh.try_get("p1.html", "/a.docx") == b"persisted"


@pytest.mark.asyncio
async def test_remove_drops_all_keys_for_a_file(tmp_path: Path):
    cache = LocalFileCache(tmp_path)
    await cache.set("info.json", "/a.docx", b'{"x":1}')
    await cache.set("p1.html", "/a.docx", b"page")
    await cache.set("p1.html", "/b.docx", b"other")

    await cache.remove("/a.docx")

    assert await cache.try_get("info.json", "/a.docx") is None
    assert await cache.try_get("p1.html", "/a.docx") is None
    assert await cache.try_get("p1.html", "/b.docx") == b"other"


@pytest.mark.asyncio
async def test_files_with_problematic_chars_are_safely_hashed(tmp_path: Path):
    cache = LocalFileCache(tmp_path)
    weird = "../../etc/passwd?x=1&y=2"
    await cache.set("p1.html", weird, b"hi")
    assert await cache.try_get("p1.html", weird) == b"hi"
    # The on-disk directory is the hash, not the raw path
    assert not (tmp_path / "etc").exists()

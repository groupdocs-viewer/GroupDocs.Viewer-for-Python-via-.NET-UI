"""Behavioral tests for RedisCache using fakeredis (skipped if not installed)."""
from __future__ import annotations

import pytest

fakeredis = pytest.importorskip("fakeredis")


@pytest.fixture
async def redis_cache():
    from groupdocs_viewer_ui.cache.redis import RedisCache

    client = fakeredis.aioredis.FakeRedis()
    cache = RedisCache(client=client)
    yield cache
    await client.aclose()


@pytest.mark.asyncio
async def test_returns_none_for_missing_key(redis_cache):
    assert await redis_cache.try_get("p1.html", "/a.docx") is None


@pytest.mark.asyncio
async def test_set_then_get_round_trips(redis_cache):
    await redis_cache.set("p1.html", "/a.docx", b"<html>hi</html>")
    assert await redis_cache.try_get("p1.html", "/a.docx") == b"<html>hi</html>"


@pytest.mark.asyncio
async def test_keyed_by_both_path_and_cache_key(redis_cache):
    await redis_cache.set("p1.html", "/a.docx", b"A")
    await redis_cache.set("p1.html", "/b.docx", b"B")
    await redis_cache.set("p2.html", "/a.docx", b"C")
    assert await redis_cache.try_get("p1.html", "/a.docx") == b"A"
    assert await redis_cache.try_get("p1.html", "/b.docx") == b"B"
    assert await redis_cache.try_get("p2.html", "/a.docx") == b"C"


@pytest.mark.asyncio
async def test_remove_drops_only_target_file(redis_cache):
    await redis_cache.set("p1.html", "/a.docx", b"A")
    await redis_cache.set("p2.html", "/a.docx", b"A2")
    await redis_cache.set("p1.html", "/b.docx", b"B")

    await redis_cache.remove("/a.docx")

    assert await redis_cache.try_get("p1.html", "/a.docx") is None
    assert await redis_cache.try_get("p2.html", "/a.docx") is None
    assert await redis_cache.try_get("p1.html", "/b.docx") == b"B"


def test_construction_requires_client_or_url():
    from groupdocs_viewer_ui.cache.redis import RedisCache

    with pytest.raises(ValueError, match="client.*url"):
        RedisCache()

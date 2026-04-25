"""Redis-backed file cache.

Behind the ``[redis]`` extra (``pip install groupdocs-viewer-net-ui[redis]``).
Compatible with ``redis.asyncio`` and ``fakeredis.aioredis`` for tests.
"""
from __future__ import annotations

import hashlib
from typing import Any


class RedisCache:
    """Stores cache entries in Redis, keyed by ``<prefix><sha-of-file>:<cache_key>``.

    Provide one of:
      * ``client`` — an async-compatible Redis client you've already configured
      * ``url``    — a redis:// URL; we'll create the client for you

    The client is reused across calls. We don't close it on shutdown — manage
    its lifecycle on the caller side if that matters.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        url: str | None = None,
        key_prefix: str = "gd-viewer:",
    ):
        if client is None:
            if not url:
                raise ValueError("Provide either `client` or `url`.")
            try:
                import redis.asyncio as redis
            except ImportError as exc:
                raise ImportError(
                    "RedisCache needs redis-py — install with "
                    "`pip install groupdocs-viewer-net-ui[redis]`."
                ) from exc
            # redis-py types vary by version — pair the suppression with
            # `unused-ignore` so this works whether or not the installed
            # release exposes a typed `from_url`.
            client = redis.from_url(url)  # type: ignore[no-untyped-call, unused-ignore]
        self._redis = client
        self._prefix = key_prefix

    async def try_get(self, cache_key: str, file_path: str) -> bytes | None:
        # Same cross-version dance as the constructor: .get() may or may
        # not have a typed return depending on the installed redis-py.
        return await self._redis.get(self._key(cache_key, file_path))  # type: ignore[no-any-return, unused-ignore]

    async def set(self, cache_key: str, file_path: str, data: bytes) -> None:
        await self._redis.set(self._key(cache_key, file_path), data)

    async def remove(self, file_path: str) -> None:
        pattern = f"{self._prefix}{self._digest(file_path)}:*"
        # Use SCAN (not KEYS) so we don't block Redis on large keyspaces.
        keys = [key async for key in self._redis.scan_iter(match=pattern)]
        if keys:
            await self._redis.delete(*keys)

    # --- internals --------------------------------------------------------

    def _key(self, cache_key: str, file_path: str) -> str:
        return f"{self._prefix}{self._digest(file_path)}:{cache_key}"

    @staticmethod
    def _digest(file_path: str) -> str:
        return hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:32]

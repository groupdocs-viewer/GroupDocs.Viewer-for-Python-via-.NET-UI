"""Custom FileCache that adds TTL on top of any existing cache.

Wraps another `FileCache` and expires entries after a configurable time.
Useful for use cases where source documents change underneath the viewer
and the cache must invalidate eventually even without an explicit `remove`.
"""
import time
from pathlib import Path

import uvicorn

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.memory import InMemoryCache
from groupdocs_viewer_ui.cache.protocol import FileCache
from groupdocs_viewer_ui.storage.local import LocalFileStorage
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer


class TTLCache:
    """Decorator that adds TTL semantics to any FileCache impl."""

    def __init__(self, inner: FileCache, *, ttl_seconds: float = 3600):
        self._inner = inner
        self._ttl = ttl_seconds
        self._timestamps: dict[tuple[str, str], float] = {}

    async def try_get(self, cache_key: str, file_path: str) -> bytes | None:
        ts = self._timestamps.get((file_path, cache_key))
        if ts is None or time.monotonic() - ts > self._ttl:
            return None
        return await self._inner.try_get(cache_key, file_path)

    async def set(self, cache_key: str, file_path: str, data: bytes) -> None:
        self._timestamps[(file_path, cache_key)] = time.monotonic()
        await self._inner.set(cache_key, file_path, data)

    async def remove(self, file_path: str) -> None:
        for key in [k for k in self._timestamps if k[0] == file_path]:
            del self._timestamps[key]
        await self._inner.remove(file_path)


ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# Five-minute TTL on top of an in-memory cache. Swap InMemoryCache for
# LocalFileCache or RedisCache without touching this code.
cache = TTLCache(InMemoryCache(), ttl_seconds=300)

storage = LocalFileStorage(DOCS)
app = create_app(
    Config(),
    storage=storage,
    cache=cache,
    viewer=SelfHostViewer(storage=storage),
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

"""Process-local in-memory file cache."""
from __future__ import annotations


class InMemoryCache:
    """Trivial dict-backed cache. Lives for the life of the process.

    No eviction in M2 — appropriate for dev / small deployments. Add an
    LRU bound when memory pressure becomes a real concern.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], bytes] = {}

    async def try_get(self, cache_key: str, file_path: str) -> bytes | None:
        return self._store.get((file_path, cache_key))

    async def set(self, cache_key: str, file_path: str, data: bytes) -> None:
        self._store[(file_path, cache_key)] = data

    async def remove(self, file_path: str) -> None:
        for key in [k for k in self._store if k[0] == file_path]:
            del self._store[key]

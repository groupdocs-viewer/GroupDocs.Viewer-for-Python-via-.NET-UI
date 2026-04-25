"""Cache protocol — pluggable persistence for rendered pages, thumbs, PDFs."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FileCache(Protocol):
    """Stores opaque ``bytes`` keyed by ``(file_path, cache_key)``.

    Higher-level code (e.g. ``CachingViewer``) is responsible for serializing
    structured payloads — DocumentInfo gets stored as JSON bytes, pages and
    PDFs as raw bytes. This keeps the cache backend trivial.
    """

    async def try_get(self, cache_key: str, file_path: str) -> bytes | None: ...

    async def set(self, cache_key: str, file_path: str, data: bytes) -> None: ...

    async def remove(self, file_path: str) -> None: ...

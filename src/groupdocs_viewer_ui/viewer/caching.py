"""Caching decorator for any ``Viewer`` implementation.

Mirrors the .NET ``CachingViewer`` pattern — check the cache before calling
through to the inner viewer, then store the result. Batched ``get_pages`` /
``get_thumbs`` only render the pages that are missing from the cache, so
warm requests are essentially free.
"""
from __future__ import annotations

import json
from collections.abc import Sequence

from groupdocs_viewer_ui.cache.keys import (
    FILE_INFO_CACHE_KEY,
    PDF_FILE_CACHE_KEY,
    page_cache_key,
    resource_cache_key,
    thumb_cache_key,
)
from groupdocs_viewer_ui.cache.protocol import FileCache
from groupdocs_viewer_ui.viewer.entities import (
    DocumentInfo,
    FileCredentials,
    Page,
    PageInfo,
    Thumb,
)
from groupdocs_viewer_ui.viewer.protocol import Viewer


class CachingViewer:
    """Wraps any ``Viewer`` with cache-aside reads and writes against ``FileCache``."""

    def __init__(self, inner: Viewer, cache: FileCache):
        self._inner = inner
        self._cache = cache

    @property
    def page_extension(self) -> str:
        return self._inner.page_extension

    @property
    def thumb_extension(self) -> str:
        return self._inner.thumb_extension

    async def get_document_info(self, creds: FileCredentials) -> DocumentInfo:
        cached = await self._cache.try_get(FILE_INFO_CACHE_KEY, creds.file_path)
        if cached is not None:
            return _document_info_from_bytes(cached)
        info = await self._inner.get_document_info(creds)
        await self._cache.set(
            FILE_INFO_CACHE_KEY, creds.file_path, _document_info_to_bytes(info)
        )
        return info

    async def get_page(self, creds: FileCredentials, page_number: int) -> Page:
        key = page_cache_key(page_number, self.page_extension)
        cached = await self._cache.try_get(key, creds.file_path)
        if cached is not None:
            return Page(number=page_number, data=cached)
        page = await self._inner.get_page(creds, page_number)
        await self._cache.set(key, creds.file_path, page.data)
        await self._cache_resources(creds.file_path, page)
        return page

    async def get_pages(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Page]:
        return await self._batched_get(
            creds,
            list(page_numbers),
            key_for=lambda n: page_cache_key(n, self.page_extension),
            renderer=self._inner.get_pages,
            wrap=lambda n, data: Page(number=n, data=data),
            cache_after_render=self._cache_page_after_render,
        )

    async def get_thumb(self, creds: FileCredentials, page_number: int) -> Thumb:
        key = thumb_cache_key(page_number, self.thumb_extension)
        cached = await self._cache.try_get(key, creds.file_path)
        if cached is not None:
            return Thumb(number=page_number, data=cached)
        thumb = await self._inner.get_thumb(creds, page_number)
        await self._cache.set(key, creds.file_path, thumb.data)
        return thumb

    async def get_thumbs(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Thumb]:
        return await self._batched_get(
            creds,
            list(page_numbers),
            key_for=lambda n: thumb_cache_key(n, self.thumb_extension),
            renderer=self._inner.get_thumbs,
            wrap=lambda n, data: Thumb(number=n, data=data),
            cache_after_render=self._cache_thumb_after_render,
        )

    async def get_pdf(self, creds: FileCredentials) -> bytes:
        cached = await self._cache.try_get(PDF_FILE_CACHE_KEY, creds.file_path)
        if cached is not None:
            return cached
        pdf = await self._inner.get_pdf(creds)
        await self._cache.set(PDF_FILE_CACHE_KEY, creds.file_path, pdf)
        return pdf

    async def get_page_resource(
        self, creds: FileCredentials, page_number: int, resource_name: str
    ) -> bytes:
        key = resource_cache_key(page_number, resource_name)
        cached = await self._cache.try_get(key, creds.file_path)
        if cached is not None:
            return cached
        data = await self._inner.get_page_resource(creds, page_number, resource_name)
        await self._cache.set(key, creds.file_path, data)
        return data

    # --- helpers ----------------------------------------------------------

    async def _batched_get(self, creds, numbers, *, key_for, renderer, wrap, cache_after_render):
        # First pass: pull whatever's already cached.
        results: dict[int, object] = {}
        missing: list[int] = []
        for n in numbers:
            cached = await self._cache.try_get(key_for(n), creds.file_path)
            if cached is None:
                missing.append(n)
            else:
                results[n] = wrap(n, cached)

        # Second pass: render the misses in one batch and cache them.
        if missing:
            rendered = await renderer(creds, missing)
            for entity in rendered:
                results[entity.number] = entity
                await cache_after_render(creds.file_path, entity)

        return [results[n] for n in numbers]

    async def _cache_page_after_render(self, file_path: str, page: Page) -> None:
        await self._cache.set(
            page_cache_key(page.number, self.page_extension), file_path, page.data
        )
        await self._cache_resources(file_path, page)

    async def _cache_thumb_after_render(self, file_path: str, thumb: Thumb) -> None:
        await self._cache.set(
            thumb_cache_key(thumb.number, self.thumb_extension), file_path, thumb.data
        )

    async def _cache_resources(self, file_path: str, page: Page) -> None:
        for resource in page.resources:
            await self._cache.set(
                resource_cache_key(page.number, resource.resource_name),
                file_path,
                resource.data,
            )


# --- DocumentInfo <-> bytes ---------------------------------------------------


def _document_info_to_bytes(info: DocumentInfo) -> bytes:
    payload = {
        "fileType": info.file_type,
        "printAllowed": info.print_allowed,
        "pages": [
            {"number": p.number, "width": p.width, "height": p.height, "name": p.name}
            for p in info.pages
        ],
    }
    return json.dumps(payload).encode("utf-8")


def _document_info_from_bytes(data: bytes) -> DocumentInfo:
    payload = json.loads(data.decode("utf-8"))
    return DocumentInfo(
        file_type=payload["fileType"],
        print_allowed=payload["printAllowed"],
        pages=[
            PageInfo(
                number=p["number"],
                width=p["width"],
                height=p["height"],
                name=p.get("name", ""),
            )
            for p in payload["pages"]
        ],
    )

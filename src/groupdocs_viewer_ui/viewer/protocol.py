"""Viewer engine protocol — pluggable rendering backend.

Shape mirrors the .NET ``GroupDocs.Viewer.UI.Core.IViewer`` interface so a
CachingViewer decorator can wrap any implementation.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from groupdocs_viewer_ui.viewer.entities import (
    DocumentInfo,
    FileCredentials,
    Page,
    Thumb,
)


@runtime_checkable
class Viewer(Protocol):
    """Render documents to HTML / image / PDF.

    The default implementation (``SelfHostViewer``) wraps ``groupdocs.viewer``
    and offloads its sync calls via ``asyncio.to_thread``. The protocol is
    async-signatured so a natively-async engine can slot in later without
    a breaking change.
    """

    @property
    def page_extension(self) -> str: ...

    @property
    def thumb_extension(self) -> str: ...

    async def get_document_info(self, creds: FileCredentials) -> DocumentInfo: ...

    async def get_page(self, creds: FileCredentials, page_number: int) -> Page: ...

    async def get_thumb(self, creds: FileCredentials, page_number: int) -> Thumb: ...

    async def get_pages(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Page]: ...

    async def get_thumbs(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Thumb]: ...

    async def get_pdf(self, creds: FileCredentials) -> bytes: ...

    async def get_page_resource(
        self, creds: FileCredentials, page_number: int, resource_name: str
    ) -> bytes: ...

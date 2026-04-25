"""Shared test fixtures."""
from __future__ import annotations

from collections.abc import Sequence

import pytest

from groupdocs_viewer_ui.viewer.entities import (
    DocumentInfo,
    FileCredentials,
    Page,
    PageInfo,
    Thumb,
)


class FakeViewer:
    """Minimal in-memory Viewer impl used to drive integration tests
    without depending on the real ``groupdocs.viewer`` library."""

    page_extension = ".html"
    thumb_extension = ".png"

    def __init__(
        self,
        total_pages: int = 3,
        *,
        password_required: bool = False,
        expected_password: str = "correct",
    ):
        self.total_pages = total_pages
        self.password_required = password_required
        self.expected_password = expected_password
        self.calls: list[tuple[str, tuple]] = []

    def _check_password(self, creds: FileCredentials) -> None:
        if not self.password_required:
            return
        if not creds.password:
            raise RuntimeError("This document requires a password to open.")
        if creds.password != self.expected_password:
            raise RuntimeError("The supplied password is incorrect.")

    async def get_document_info(self, creds: FileCredentials) -> DocumentInfo:
        self.calls.append(("get_document_info", (creds.file_path,)))
        self._check_password(creds)
        return DocumentInfo(
            file_type="docx",
            pages=[
                PageInfo(number=i, width=600, height=800)
                for i in range(1, self.total_pages + 1)
            ],
            print_allowed=True,
        )

    async def get_page(self, creds: FileCredentials, page_number: int) -> Page:
        self.calls.append(("get_page", (creds.file_path, page_number)))
        self._check_password(creds)
        return Page(
            number=page_number,
            data=f"<html>page {page_number}</html>".encode(),
        )

    async def get_pages(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Page]:
        self.calls.append(("get_pages", (creds.file_path, tuple(page_numbers))))
        self._check_password(creds)
        return [
            Page(number=n, data=f"<html>page {n}</html>".encode())
            for n in page_numbers
        ]

    async def get_thumb(self, creds: FileCredentials, page_number: int) -> Thumb:
        self.calls.append(("get_thumb", (creds.file_path, page_number)))
        self._check_password(creds)
        return Thumb(number=page_number, data=b"\x89PNG-fake")

    async def get_thumbs(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Thumb]:
        self.calls.append(("get_thumbs", (creds.file_path, tuple(page_numbers))))
        self._check_password(creds)
        return [Thumb(number=n, data=b"\x89PNG-fake") for n in page_numbers]

    async def get_pdf(self, creds: FileCredentials) -> bytes:
        self.calls.append(("get_pdf", (creds.file_path,)))
        self._check_password(creds)
        return b"%PDF-fake"

    async def get_page_resource(
        self, creds: FileCredentials, page_number: int, resource_name: str
    ) -> bytes:
        self.calls.append(
            ("get_page_resource", (creds.file_path, page_number, resource_name))
        )
        self._check_password(creds)
        return f"/* {resource_name} */".encode()


@pytest.fixture
def fake_viewer() -> FakeViewer:
    return FakeViewer()

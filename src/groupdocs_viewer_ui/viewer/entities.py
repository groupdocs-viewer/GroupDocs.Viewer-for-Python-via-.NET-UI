"""Viewer data entities — Python ports of ``GroupDocs.Viewer.UI.Core.Entities``."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileCredentials:
    """Everything needed to open a document: path + optional type hint + password."""

    file_path: str
    file_type: str | None = None
    password: str | None = None


@dataclass
class PageResource:
    """An asset referenced by an HTML-mode page (CSS, font, image).

    Populated only in HTML-with-external-resources mode (M3+).
    """

    resource_name: str
    data: bytes


@dataclass
class Page:
    """Rendered page payload — HTML bytes or image bytes."""

    number: int
    data: bytes
    resources: list[PageResource] = field(default_factory=list)


@dataclass
class Thumb:
    """Rendered page thumbnail (PNG/JPEG bytes)."""

    number: int
    data: bytes


@dataclass
class PageInfo:
    """Metadata for a single page — from ``Viewer.get_view_info``."""

    number: int
    width: int
    height: int
    name: str = ""


@dataclass
class DocumentInfo:
    """Result of inspecting a document before rendering."""

    file_type: str
    pages: list[PageInfo]
    print_allowed: bool = True

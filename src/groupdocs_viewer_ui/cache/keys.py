"""Cache key conventions — port of .NET ``CacheKeys``.

The CachingViewer and any FileCache impl share these names so cache files
on disk are interpretable across viewer / cache boundaries.
"""
from __future__ import annotations

FILE_INFO_CACHE_KEY = "info.json"
PDF_FILE_CACHE_KEY = "file.pdf"


def page_cache_key(page_number: int, page_extension: str) -> str:
    """e.g. ``p1.html`` for page 1 in HTML mode."""
    return f"p{page_number}{page_extension}"


def thumb_cache_key(page_number: int, thumb_extension: str) -> str:
    """e.g. ``p1_t.png`` for thumb of page 1."""
    return f"p{page_number}_t{thumb_extension}"


def resource_cache_key(page_number: int, resource_name: str) -> str:
    """e.g. ``p1_styles.css`` for an HTML-mode resource on page 1."""
    return f"p{page_number}_{resource_name}"

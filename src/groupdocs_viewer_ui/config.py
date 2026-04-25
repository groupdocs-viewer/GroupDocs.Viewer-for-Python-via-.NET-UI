"""Viewer UI configuration.

Mirrors the .NET ``GroupDocs.Viewer.UI.Core.Configuration.Config`` and
``GroupDocs.Viewer.UI.Api.Configuration.Options`` classes in snake_case.

String enum values (``rendering_mode``, ``initial_zoom``) match the exact
serialized form the .NET ``RenderingMode.Value`` and ``ZoomLevel.Value``
properties produce — the vendored Angular SPA reads these literal strings
from ``window.groupdocs.viewer``. **Do not change the values to look more
"pythonic"** — the SPA matches them exactly. See `RenderingMode.cs` and
`ZoomLevel.cs` in the .NET repo for the source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RenderingMode = Literal["html", "image"]
ZoomLevel = Literal[
    "Fit Page",
    "Fit Width",
    "Fit Height",
    "25%",
    "50%",
    "60%",
    "70%",
    "75%",
    "80%",
    "90%",
    "100%",
    "125%",
    "150%",
    "200%",
    "300%",
]
# Note: "Fit Page" is supported by the vendored Angular SPA but is NOT present
# in the .NET ZoomLevel enum (only Fit Width / Fit Height / percentages). It's
# the most ergonomic default — sees the whole page without scrolling — so we
# expose it here. If you ever drive Config from the .NET-side wire format
# directly, "Fit Page" won't round-trip; use "Fit Width" or "Fit Height" instead.


@dataclass
class Config:
    # Rendering
    rendering_mode: RenderingMode = "html"
    static_content_mode: bool = False

    # Preload / initial state
    preload_pages: int = 3
    initial_file: str | None = None
    initial_zoom: ZoomLevel = "Fit Page"

    # UI feature toggles (one-to-one with the SPA's window.groupdocs.viewer config)
    enable_header: bool = True
    enable_toolbar: bool = True
    enable_page_selector: bool = True
    enable_download_pdf: bool = True
    enable_file_upload: bool = True
    enable_file_browser: bool = True
    enable_context_menu: bool = True
    enable_zoom: bool = True
    enable_search: bool = True
    enable_file_name: bool = True
    enable_thumbnails: bool = True
    enable_print: bool = True
    enable_presentation: bool = True
    enable_hyperlinks: bool = True
    enable_scroll_animation: bool = True
    enable_language_selector: bool = True
    enable_help: bool = True

    # Localization
    default_language: str = "en"
    supported_languages: list[str] = field(default_factory=lambda: ["en"])

    # Hosting / API routing
    ui_path: str = "/viewer"
    ui_title: str = "GroupDocs.Viewer"
    api_path: str = "viewer-api"
    use_absolute_urls: bool = False
    api_domain: str = ""

    # Branding (spliced into the SPA index.html at request time)
    custom_css: str = ""
    custom_js: str = ""

    # Logo overrides — replace the SVG assets the SPA loads, or hide them.
    # When ``hide_logo_*`` is True the SVG is replaced with an empty placeholder
    # (matching the .NET ReplaceLogoResources behaviour). When ``custom_logo_*_path``
    # points at a file, its bytes are served instead. Both off → vendor default.
    hide_logo_image: bool = False
    custom_logo_image_path: str | None = None
    hide_logo_text: bool = False
    custom_logo_text_path: str | None = None

    # HTTP response cache for rendered pages/thumbs (seconds)
    response_cache_duration_seconds: int = 0

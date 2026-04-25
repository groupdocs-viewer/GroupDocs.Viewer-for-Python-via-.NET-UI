"""SPA index.html template rendering and ``window.groupdocs.viewer`` config."""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from groupdocs_viewer_ui.config import Config

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def build_window_config(config: Config) -> dict[str, Any]:
    """Build the JSON object the SPA reads from ``window.groupdocs.viewer``.

    Field names and value casing match the .NET serialization (see
    ``UIResourceExtensions.SerializeWindowConfig`` in the .NET repo) so the
    vendored Angular SPA is drop-in.
    """
    api_endpoint = "/" + config.api_path.strip("/")
    api_endpoint_config = {
        "filesTree": "/list-dir",
        "uploadFile": "/upload-file",
        "viewData": "/view-data",
        "createPages": "/create-pages",
        "createPdf": "/create-pdf",
        "printPdf": "/get-pdf",
    }
    return {
        "apiEndpoint": api_endpoint,
        "renderingMode": config.rendering_mode,
        "staticContentMode": config.static_content_mode,
        "initialFile": config.initial_file,
        "preloadPages": config.preload_pages,
        "initialZoom": config.initial_zoom,
        "enableHeader": config.enable_header,
        "enableToolbar": config.enable_toolbar,
        "enablePageSelector": config.enable_page_selector,
        "enableDownloadPdf": config.enable_download_pdf,
        "enableFileUpload": config.enable_file_upload,
        "enableFileBrowser": config.enable_file_browser,
        "enableContextMenu": config.enable_context_menu,
        "enableZoom": config.enable_zoom,
        "enableSearch": config.enable_search,
        "enableFileName": config.enable_file_name,
        "enableThumbnails": config.enable_thumbnails,
        "enablePrint": config.enable_print,
        "enablePresentation": config.enable_presentation,
        "enableHyperlinks": config.enable_hyperlinks,
        "enableScrollAnimation": config.enable_scroll_animation,
        "enableLanguageSelector": config.enable_language_selector,
        "enableHelp": config.enable_help,
        "defaultLanguage": config.default_language,
        "supportedLanguages": list(config.supported_languages),
        "showExitButton": False,
        "apiEndpointConfig": api_endpoint_config,
    }


def make_index_handler(
    config: Config, frontend_dir: Path = FRONTEND_DIR
) -> Callable[[Request], Awaitable[HTMLResponse]]:
    """Build a Starlette handler that renders index.html with config baked in.

    The template is read once at startup; substitutions happen per-request
    so config changes (e.g. via testing) take effect without a reload.
    """
    template = (frontend_dir / "index.html").read_text(encoding="utf-8")
    ui_path_with_slash = config.ui_path.rstrip("/") + "/"

    async def index(_request: Request) -> HTMLResponse:
        ui_config_json = json.dumps(build_window_config(config), indent=2)
        html = (
            template.replace("#uiPath#", ui_path_with_slash)
            .replace("#uiTitle#", config.ui_title)
            .replace("#uiConfig#", ui_config_json)
            .replace("#customCSS#", config.custom_css)
            .replace("#customJS#", config.custom_js)
        )
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, no-store"})

    return index

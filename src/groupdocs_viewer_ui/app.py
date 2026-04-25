"""ASGI application factory."""
from __future__ import annotations

from collections.abc import Awaitable
from pathlib import Path
from typing import Callable

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute, Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from groupdocs_viewer_ui import __version__
from groupdocs_viewer_ui.api.routes import build_api_routes
from groupdocs_viewer_ui.api.spa import FRONTEND_DIR, make_index_handler
from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder
from groupdocs_viewer_ui.cache.protocol import FileCache
from groupdocs_viewer_ui.config import Config
from groupdocs_viewer_ui.storage.protocol import FileStorage
from groupdocs_viewer_ui.viewer.caching import CachingViewer
from groupdocs_viewer_ui.viewer.protocol import Viewer

AuthCheck = Callable[[Request], Awaitable[None]]

# Same empty SVG the .NET ReplaceLogoResources uses when a logo is hidden.
_EMPTY_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'


async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


def _logo_override_bytes(*, hidden: bool, path: str | None) -> bytes | None:
    if hidden:
        return _EMPTY_SVG
    if path:
        return Path(path).read_bytes()
    return None


def _make_logo_route(url_path: str, content: bytes) -> Route:
    async def handler(_request: Request) -> Response:
        return Response(
            content,
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-cache, no-store"},
        )

    return Route(url_path, handler, methods=["GET"])


class _AuthCheckMiddleware:
    """ASGI middleware that runs ``auth_check`` before every HTTP request.

    The check is expected to either return ``None`` (allow) or raise an
    ``HTTPException`` (deny). We catch and convert the exception ourselves
    here — Starlette's ``ExceptionMiddleware`` sits *below* this middleware
    in the stack so it never sees an HTTPException raised at this level
    (the request response would already be in progress by the time it
    bubbled up). Lifespan / websocket events pass through untouched.
    """

    def __init__(self, app: ASGIApp, auth_check: AuthCheck) -> None:
        self.app = app
        self.auth_check = auth_check

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.auth_check(Request(scope, receive))
        except HTTPException as exc:
            response = JSONResponse(
                {"error": exc.detail or "Authentication required"},
                status_code=exc.status_code,
                headers=dict(getattr(exc, "headers", None) or {}),
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def create_app(
    config: Config | None = None,
    *,
    storage: FileStorage | None = None,
    cache: FileCache | None = None,
    viewer: Viewer | None = None,
    auth_check: AuthCheck | None = None,
) -> Starlette:
    """Build a Starlette ASGI app exposing the SPA + viewer API.

    Routes mounted (with default config):
        GET  /health                — liveness probe
        GET  /viewer, /viewer/      — SPA index.html (template-rendered)
        GET  /viewer/<asset>        — vendored Angular SPA static files
        POST /viewer-api/list-dir   — and the other 8 viewer endpoints

    ``storage`` and ``viewer`` are required in production but kept optional
    for tests of pieces that don't exercise the rendering path.
    """
    config = config or Config()
    url_builder = ApiUrlBuilder(
        api_path=config.api_path,
        use_absolute_urls=config.use_absolute_urls,
        api_domain=config.api_domain,
    )

    routes: list[BaseRoute] = [Route("/health", _health, methods=["GET"])]

    ui_path = config.ui_path.rstrip("/")
    if FRONTEND_DIR.is_dir():
        index_handler = make_index_handler(config)
        routes.append(Route(ui_path or "/", index_handler, methods=["GET"]))
        if ui_path:
            routes.append(Route(ui_path + "/", index_handler, methods=["GET"]))

            # Logo overrides — register BEFORE the StaticFiles mount so they
            # win the route match. Read at startup; bytes stay in memory.
            logo_image = _logo_override_bytes(
                hidden=config.hide_logo_image, path=config.custom_logo_image_path
            )
            if logo_image is not None:
                routes.append(
                    _make_logo_route(f"{ui_path}/assets/ui/logo-image.svg", logo_image)
                )
            logo_text = _logo_override_bytes(
                hidden=config.hide_logo_text, path=config.custom_logo_text_path
            )
            if logo_text is not None:
                routes.append(
                    _make_logo_route(f"{ui_path}/assets/ui/logo-text.svg", logo_text)
                )

            routes.append(Mount(ui_path, app=StaticFiles(directory=str(FRONTEND_DIR))))

    if storage is not None and viewer is not None:
        # Auto-wrap with CachingViewer when a cache is supplied — callers don't
        # need to remember to compose the decorator themselves.
        effective_viewer: Viewer = (
            CachingViewer(viewer, cache) if cache is not None else viewer
        )
        api_routes = build_api_routes(
            config, storage, cache, effective_viewer, url_builder
        )
        api_mount_path = "/" + config.api_path.strip("/")
        if auth_check is not None:
            # Wrap the API in its own Starlette so the middleware applies ONLY
            # to /viewer-api/* — never to /health, the SPA index, or static
            # assets. Users who want the broader scope wrap the whole app
            # themselves.
            api_app = Starlette(
                routes=api_routes,
                middleware=[
                    Middleware(_AuthCheckMiddleware, auth_check=auth_check)
                ],
            )
            routes.append(Mount(api_mount_path, app=api_app))
        else:
            routes.append(Mount(api_mount_path, routes=api_routes))
    else:
        effective_viewer = viewer  # type: ignore[assignment]

    app = Starlette(routes=routes)
    app.state.config = config
    app.state.storage = storage
    app.state.cache = cache
    app.state.viewer = effective_viewer
    app.state.url_builder = url_builder
    return app

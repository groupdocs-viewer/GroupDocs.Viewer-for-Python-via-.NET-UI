"""Viewer HTTP API — 9 endpoints matching the .NET ``ViewerController`` contract."""
from __future__ import annotations

import logging
import mimetypes
import urllib.parse
from pathlib import Path

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from groupdocs_viewer_ui import __version__
from groupdocs_viewer_ui.api.contracts import (
    CreatePagesRequest,
    CreatePdfRequest,
    CreatePdfResponse,
    FileSystemItem,
    ListDirRequest,
    PageData,
    UploadFileResponse,
    ViewDataRequest,
    ViewDataResponse,
)
from groupdocs_viewer_ui.api.url_builder import ApiUrlBuilder
from groupdocs_viewer_ui.cache.protocol import FileCache
from groupdocs_viewer_ui.config import Config
from groupdocs_viewer_ui.storage.protocol import FileStorage
from groupdocs_viewer_ui.viewer.entities import FileCredentials
from groupdocs_viewer_ui.viewer.protocol import Viewer

logger = logging.getLogger(__name__)


_EXTENSION_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _content_type_for_extension(ext: str) -> str:
    return _EXTENSION_CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _content_type_from_filename(name: str) -> str:
    guessed, _ = mimetypes.guess_type(name)
    return guessed or "application/octet-stream"


def _is_password_error(exc: BaseException) -> bool:
    return "password" in str(exc).lower()


def _password_response(provided: str | None) -> JSONResponse:
    msg = "Incorrect Password" if provided else "Password Required"
    return JSONResponse({"error": msg}, status_code=403)


async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": __version__})


def build_api_routes(
    config: Config,
    storage: FileStorage,
    cache: FileCache | None,
    viewer: Viewer,
    url_builder: ApiUrlBuilder,
) -> list[Route]:
    """Construct all 9 viewer API routes wired to the supplied collaborators."""

    async def list_dir(request: Request) -> Response:
        if not config.enable_file_browser:
            return PlainTextResponse("Browsing files is disabled.", status_code=500)
        try:
            req = ListDirRequest.model_validate(await request.json())
            entries = await storage.list_dirs_and_files(req.path)
            items = [
                FileSystemItem(
                    path=e.file_path,
                    name=Path(e.file_path).name or e.file_path,
                    is_dir=e.is_directory,
                    size=e.size,
                ).model_dump(by_alias=True)
                for e in entries
            ]
            return JSONResponse(items)
        except Exception:
            logger.exception("Failed to list directory")
            return PlainTextResponse("Failed to load file tree.", status_code=500)

    async def upload_file(request: Request) -> Response:
        if not config.enable_file_upload:
            return PlainTextResponse("Uploading files is disabled.", status_code=500)
        try:
            form = await request.form()
            rewrite_raw = form.get("rewrite", "")
            rewrite = str(rewrite_raw).strip().lower() == "true"

            url = str(form.get("url") or "").strip()
            if url:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(url, headers={"User-Agent": "Other"})
                    resp.raise_for_status()
                file_name = (
                    Path(urllib.parse.urlparse(url).path).name or "downloaded"
                )
                data = resp.content
            else:
                upload = next(
                    (v for v in form.values() if hasattr(v, "filename")),
                    None,
                )
                if upload is None:
                    return PlainTextResponse("No file uploaded.", status_code=400)
                file_name = upload.filename or "uploaded"
                data = await upload.read()

            saved_path = await storage.write_file(file_name, data, rewrite=rewrite)
            return JSONResponse(
                UploadFileResponse(file=saved_path).model_dump(by_alias=True)
            )
        except Exception:
            logger.exception("Failed to upload document")
            return PlainTextResponse("Failed to upload document.", status_code=500)

    async def view_data(request: Request) -> Response:
        req: ViewDataRequest | None = None
        try:
            req = ViewDataRequest.model_validate(await request.json())
            creds = FileCredentials(
                file_path=req.file, file_type=req.file_type, password=req.password
            )
            info = await viewer.get_document_info(creds)

            preload = _pages_to_preload(len(info.pages), config.preload_pages)
            await viewer.get_pages(creds, preload)
            wants_thumbs = config.enable_thumbnails and config.rendering_mode == "html"
            if wants_thumbs:
                await viewer.get_thumbs(creds, preload)

            preload_set = set(preload)
            pages = [
                PageData(
                    number=p.number,
                    width=p.width,
                    height=p.height,
                    page_url=(
                        url_builder.build_page_url(req.file, p.number)
                        if p.number in preload_set
                        else None
                    ),
                    thumb_url=(
                        url_builder.build_thumb_url(req.file, p.number)
                        if p.number in preload_set and wants_thumbs
                        else None
                    ),
                )
                for p in info.pages
            ]

            response = ViewDataResponse(
                file=req.file,
                file_type=info.file_type,
                file_name=Path(req.file).name or req.file,
                can_print=info.print_allowed,
                search_term=None,
                pages=pages,
            )
            return JSONResponse(response.model_dump(by_alias=True))
        except Exception as exc:
            if _is_password_error(exc):
                return _password_response(req.password if req else None)
            logger.exception("Failed to read document description")
            return PlainTextResponse(
                "Failed to read document description.", status_code=500
            )

    async def create_pages(request: Request) -> Response:
        req: CreatePagesRequest | None = None
        try:
            req = CreatePagesRequest.model_validate(await request.json())
            creds = FileCredentials(
                file_path=req.file, file_type=req.file_type, password=req.password
            )
            info = await viewer.get_document_info(creds)

            await viewer.get_pages(creds, req.pages)
            wants_thumbs = config.enable_thumbnails and config.rendering_mode == "html"
            if wants_thumbs:
                await viewer.get_thumbs(creds, req.pages)

            wanted = set(req.pages)
            page_data = [
                PageData(
                    number=p.number,
                    width=p.width,
                    height=p.height,
                    page_url=url_builder.build_page_url(req.file, p.number),
                    thumb_url=(
                        url_builder.build_thumb_url(req.file, p.number)
                        if wants_thumbs
                        else None
                    ),
                ).model_dump(by_alias=True)
                for p in info.pages
                if p.number in wanted
            ]
            return JSONResponse(page_data)
        except Exception as exc:
            if _is_password_error(exc):
                return _password_response(req.password if req else None)
            logger.exception("Failed to retrieve document pages")
            return PlainTextResponse(
                "Failed to retrieve document pages.", status_code=500
            )

    async def create_pdf(request: Request) -> Response:
        if not (config.enable_download_pdf or config.enable_print):
            return PlainTextResponse(
                "Creating PDF files is disabled.", status_code=500
            )
        req: CreatePdfRequest | None = None
        try:
            req = CreatePdfRequest.model_validate(await request.json())
            creds = FileCredentials(
                file_path=req.file, file_type=req.file_type, password=req.password
            )
            await viewer.get_pdf(creds)
            return JSONResponse(
                CreatePdfResponse(
                    pdf_url=url_builder.build_pdf_url(req.file)
                ).model_dump(by_alias=True)
            )
        except Exception as exc:
            if _is_password_error(exc):
                return _password_response(req.password if req else None)
            logger.exception("Failed to create PDF file")
            return PlainTextResponse("Failed to create PDF file.", status_code=500)

    async def get_page(request: Request) -> Response:
        try:
            file_path = request.query_params.get("file", "")
            page_number = int(request.query_params.get("page", "0"))
            page = await viewer.get_page(FileCredentials(file_path=file_path), page_number)
            return Response(
                page.data,
                media_type=_content_type_for_extension(viewer.page_extension),
                headers=_cache_headers(config),
            )
        except Exception:
            logger.exception("Failed to retrieve document page")
            return PlainTextResponse(
                "Failed to retrieve document page.", status_code=500
            )

    async def get_thumb(request: Request) -> Response:
        try:
            file_path = request.query_params.get("file", "")
            page_number = int(request.query_params.get("page", "0"))
            thumb = await viewer.get_thumb(
                FileCredentials(file_path=file_path), page_number
            )
            return Response(
                thumb.data,
                media_type=_content_type_for_extension(viewer.thumb_extension),
                headers=_cache_headers(config),
            )
        except Exception:
            logger.exception("Failed to retrieve document thumb")
            return PlainTextResponse(
                "Failed to retrieve document thumb.", status_code=500
            )

    async def get_pdf(request: Request) -> Response:
        if not (config.enable_download_pdf or config.enable_print):
            return PlainTextResponse(
                "Creating PDF files is disabled.", status_code=500
            )
        try:
            file_path = request.query_params.get("file", "")
            pdf_bytes = await viewer.get_pdf(FileCredentials(file_path=file_path))
            download_name = Path(file_path).stem + ".pdf"
            headers = {
                "Content-Disposition": f'attachment; filename="{download_name}"',
                **_cache_headers(config),
            }
            return Response(pdf_bytes, media_type="application/pdf", headers=headers)
        except Exception:
            logger.exception("Failed to retrieve PDF file")
            return PlainTextResponse("Failed to retrieve PDF file.", status_code=500)

    async def get_resource(request: Request) -> Response:
        if config.rendering_mode != "html":
            return PlainTextResponse(
                "Loading page resources is disabled in image mode.", status_code=500
            )
        try:
            file_path = request.query_params.get("file", "")
            page_number = int(request.query_params.get("page", "0"))
            resource = request.query_params.get("resource", "")
            data = await viewer.get_page_resource(
                FileCredentials(file_path=file_path), page_number, resource
            )
            if not data:
                return PlainTextResponse(
                    f"Resource {resource} was not found", status_code=404
                )
            return Response(
                data,
                media_type=_content_type_from_filename(resource),
                headers=_cache_headers(config),
            )
        except NotImplementedError as exc:
            return PlainTextResponse(str(exc), status_code=500)
        except Exception:
            logger.exception("Failed to load document page resource")
            return PlainTextResponse(
                "Failed to load document page resource.", status_code=500
            )

    return [
        Route("/list-dir", list_dir, methods=["POST"]),
        Route("/upload-file", upload_file, methods=["POST"]),
        Route("/view-data", view_data, methods=["POST"]),
        Route("/create-pages", create_pages, methods=["POST"]),
        Route("/create-pdf", create_pdf, methods=["POST"]),
        Route("/get-page", get_page, methods=["GET"]),
        Route("/get-thumb", get_thumb, methods=["GET"]),
        Route("/get-pdf", get_pdf, methods=["GET"]),
        Route("/get-resource", get_resource, methods=["GET"]),
    ]


def _pages_to_preload(total_pages: int, preload_pages: int) -> list[int]:
    if preload_pages == 0:
        return list(range(1, total_pages + 1))
    return list(range(1, min(total_pages, preload_pages) + 1))


def _cache_headers(config: Config) -> dict[str, str]:
    seconds = config.response_cache_duration_seconds
    if seconds <= 0:
        return {"Cache-Control": "no-cache, no-store"}
    return {"Cache-Control": f"public, max-age={seconds}"}

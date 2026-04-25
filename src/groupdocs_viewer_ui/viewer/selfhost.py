"""Default Viewer implementation wrapping ``groupdocs.viewer``.

The underlying ``groupdocs-viewer-net`` library is purely synchronous and
file-based (it writes rendered output to paths with a ``{0}`` placeholder).
We render into a temporary directory per call and read the bytes back; the
outer FileCache is responsible for cross-request persistence.

File input always flows through the ``FileStorage`` abstraction — the
viewer never opens paths directly. This matches .NET's
``BaseViewer.CreateViewer`` and is the only way it can work for cloud
storage backends (S3 / Azure paths aren't real filesystem paths).

All library calls are offloaded to the default thread pool via
``asyncio.to_thread``.
"""
from __future__ import annotations

import asyncio
import io
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from groupdocs_viewer_ui.storage.protocol import FileStorage
from groupdocs_viewer_ui.viewer.entities import (
    DocumentInfo,
    FileCredentials,
    Page,
    PageInfo,
    PageResource,
    Thumb,
)

RenderingMode = Literal["html", "image"]


class SelfHostViewer:
    """Render documents via the ``groupdocs-viewer-net`` library.

    The library is imported lazily inside each sync helper so this module
    is importable in environments where the dependency is not installed
    (useful for unit tests that only touch other parts of the package).

    HTML modes:
      * **embedded** (default) — every page is a self-contained HTML file
        with CSS, fonts, and images inlined.
      * **external** — pages reference ``<link>`` / ``<img>`` URLs back at
        the viewer's ``/get-resource`` endpoint. Enable by passing
        ``html_external_resources=True`` *and*
        ``resource_url_template_factory=ApiUrlBuilder(...).build_resource_url_template``.
    """

    def __init__(
        self,
        rendering_mode: str = "html",
        *,
        storage: FileStorage,
        thumb_width: int = 300,
        html_external_resources: bool = False,
        resource_url_template_factory: Callable[[str], str] | None = None,
    ):
        # Tolerant of casing — Config uses lowercase ("html"/"image") matching
        # the .NET RenderingMode.Value, but we still accept "Html"/"Image" so
        # case mismatch from callers isn't a debugging trap.
        normalized = str(rendering_mode).strip().lower()
        if normalized not in ("html", "image"):
            raise ValueError(
                f"rendering_mode must be 'html' or 'image', got {rendering_mode!r}"
            )
        self._mode: RenderingMode = normalized  # type: ignore[assignment]
        self._storage = storage
        self._thumb_width = thumb_width
        self._html_external_resources = html_external_resources
        self._resource_url_template_factory = resource_url_template_factory

        if html_external_resources and resource_url_template_factory is None:
            raise ValueError(
                "html_external_resources=True requires resource_url_template_factory "
                "(typically ApiUrlBuilder(...).build_resource_url_template)."
            )
        if html_external_resources and self._mode != "html":
            raise ValueError(
                "html_external_resources is only meaningful with rendering_mode='html'."
            )

    @property
    def page_extension(self) -> str:
        return ".html" if self._mode == "html" else ".png"

    @property
    def thumb_extension(self) -> str:
        return ".png"

    async def get_document_info(self, creds: FileCredentials) -> DocumentInfo:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(self._info_sync, creds, data)

    async def get_page(self, creds: FileCredentials, page_number: int) -> Page:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(self._page_sync, creds, data, page_number)

    async def get_thumb(self, creds: FileCredentials, page_number: int) -> Thumb:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(self._thumb_sync, creds, data, page_number)

    async def get_pages(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Page]:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(
            self._pages_sync, creds, data, list(page_numbers)
        )

    async def get_thumbs(
        self, creds: FileCredentials, page_numbers: Sequence[int]
    ) -> list[Thumb]:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(
            self._thumbs_sync, creds, data, list(page_numbers)
        )

    async def get_pdf(self, creds: FileCredentials) -> bytes:
        data = await self._storage.read_file(creds.file_path)
        return await asyncio.to_thread(self._pdf_sync, creds, data)

    async def get_page_resource(
        self, creds: FileCredentials, page_number: int, resource_name: str
    ) -> bytes:
        if not self._html_external_resources:
            raise NotImplementedError(
                "Page resources are only available in HTML-with-external-resources mode."
            )
        # Resources are produced as a side effect of rendering a page. If we
        # arrive here it means the cache was cold (CachingViewer didn't have
        # this resource), so render the page now — caching the resource for
        # next time is the wrapping CachingViewer's job.
        page = await self.get_page(creds, page_number)
        for resource in page.resources:
            if resource.resource_name == resource_name:
                return resource.data
        return b""  # Triggers 404 in the route handler.

    # --- sync helpers (run in thread pool) --------------------------------

    def _load_options(self, creds: FileCredentials) -> Any:
        # The groupdocs.viewer typing is sparse; treat its options as Any
        # so we can set attributes the type stubs don't enumerate.
        from groupdocs.viewer.options import LoadOptions

        if not creds.password:
            return None
        opts = LoadOptions()
        opts.password = creds.password
        return opts

    def _open(self, creds: FileCredentials, data: bytes) -> Any:
        from groupdocs.viewer import Viewer as GDViewer

        load = self._load_options(creds)
        stream = io.BytesIO(data)
        # The library accepts BytesIO at runtime even though its stubs say
        # Stream | None — the stubs predate the stream-input overload.
        return GDViewer(stream, load) if load else GDViewer(stream)  # type: ignore[arg-type]

    def _info_sync(self, creds: FileCredentials, data: bytes) -> DocumentInfo:
        from groupdocs.viewer.options import ViewInfoOptions

        with self._open(creds, data) as v:
            info_opts = (
                ViewInfoOptions.for_html_view()
                if self._mode == "html"
                else ViewInfoOptions.for_png_view()
            )
            info = v.get_view_info(info_opts)

        extension = getattr(info.file_type, "extension", str(info.file_type))
        return DocumentInfo(
            file_type=str(extension).replace(".", ""),
            pages=[
                PageInfo(
                    number=p.number,
                    width=int(p.width),
                    height=int(p.height),
                    name=getattr(p, "name", "") or "",
                )
                for p in info.pages
            ],
            print_allowed=bool(getattr(info, "printing_allowed", True)),
        )

    def _page_sync(
        self, creds: FileCredentials, data: bytes, page_number: int
    ) -> Page:
        results = self._render_to_tmp(creds, data, [page_number], kind="page")
        page_data, resources = results[page_number]
        return Page(number=page_number, data=page_data, resources=resources)

    def _pages_sync(
        self, creds: FileCredentials, data: bytes, page_numbers: list[int]
    ) -> list[Page]:
        results = self._render_to_tmp(creds, data, page_numbers, kind="page")
        return [
            Page(number=n, data=results[n][0], resources=results[n][1])
            for n in page_numbers
        ]

    def _thumb_sync(
        self, creds: FileCredentials, data: bytes, page_number: int
    ) -> Thumb:
        results = self._render_to_tmp(creds, data, [page_number], kind="thumb")
        page_data, _ = results[page_number]
        return Thumb(number=page_number, data=page_data)

    def _thumbs_sync(
        self, creds: FileCredentials, data: bytes, page_numbers: list[int]
    ) -> list[Thumb]:
        results = self._render_to_tmp(creds, data, page_numbers, kind="thumb")
        return [Thumb(number=n, data=results[n][0]) for n in page_numbers]

    def _pdf_sync(self, creds: FileCredentials, data: bytes) -> bytes:
        from groupdocs.viewer.options import PdfViewOptions

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.pdf"
            with self._open(creds, data) as v:
                # PdfViewOptions accepts a string template at runtime; the
                # stubs only enumerate the stream-factory overload.
                v.view(PdfViewOptions(str(out)))  # type: ignore[arg-type]
            return out.read_bytes()

    def _render_to_tmp(
        self,
        creds: FileCredentials,
        data: bytes,
        page_numbers: list[int],
        *,
        kind: Literal["page", "thumb"],
    ) -> dict[int, tuple[bytes, list[PageResource]]]:
        from groupdocs.viewer.options import HtmlViewOptions, PngViewOptions

        use_html = self._mode == "html" and kind == "page"
        ext = "html" if use_html else "png"
        use_external = use_html and self._html_external_resources

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            page_tpl = str(tmp_path / f"page_{{0}}.{ext}")

            # Type as Any — opts is one of three options-class subtypes,
            # and the library's stubs disagree across the constructors we use.
            opts: Any
            if use_external:
                # Resources land under <tmp>/page_<N>/<resource>; the URL
                # template's {0}/{1} are substituted by groupdocs.viewer.
                resource_path_tpl = str(tmp_path / "page_{0}" / "{1}")
                assert self._resource_url_template_factory is not None  # checked in __init__
                resource_url_tpl = self._resource_url_template_factory(creds.file_path)
                opts = HtmlViewOptions.for_external_resources(
                    page_tpl, resource_path_tpl, resource_url_tpl
                )
            elif use_html:
                opts = HtmlViewOptions.for_embedded_resources(page_tpl)
            else:
                # Stubs only enumerate the stream-factory overload of PngViewOptions;
                # the string-template form works at runtime.
                opts = PngViewOptions(page_tpl)  # type: ignore[arg-type]
                # NOTE: we deliberately do NOT set `max_width` / `width` for
                # thumbnails. Either property triggers a post-render resize
                # through System.Drawing.Common, which is fully removed for
                # non-Windows in the .NET 10 runtime that groupdocs.viewer 26.x
                # bundles (the `EnableUnixSupport` switch from .NET 6 is gone).
                # Render at native page size and let the SPA scale via CSS —
                # bigger thumb bytes but works on every platform. If thumb
                # bandwidth becomes a problem, post-process with Pillow.
                # `self._thumb_width` is intentionally unused here as a result.

            with self._open(creds, data) as v:
                v.view(opts, list(page_numbers))

            results: dict[int, tuple[bytes, list[PageResource]]] = {}
            for n in page_numbers:
                page_data = (tmp_path / f"page_{n}.{ext}").read_bytes()
                resources: list[PageResource] = []
                if use_external:
                    page_dir = tmp_path / f"page_{n}"
                    if page_dir.is_dir():
                        for resource_path in sorted(page_dir.iterdir()):
                            if resource_path.is_file():
                                resources.append(
                                    PageResource(
                                        resource_name=resource_path.name,
                                        data=resource_path.read_bytes(),
                                    )
                                )
                results[n] = (page_data, resources)

            return results

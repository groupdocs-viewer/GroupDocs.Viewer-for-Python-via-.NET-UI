"""Port of the .NET ``ApiUrlBuilder`` — builds the URLs the SPA uses
to fetch rendered pages, thumbs, PDFs, and HTML resources.
"""
from __future__ import annotations

from typing import Union
from urllib.parse import quote, urlencode


class ApiUrlBuilder:
    """Builds URLs that the SPA puts in ``pageUrl`` / ``thumbUrl`` / ``pdfUrl``.

    Relative URLs (``/get-page?...``) are the default and work when the SPA
    and API are served from the same origin with matching path base.
    Set ``use_absolute_urls=True`` + ``api_domain`` when hosting the API
    on a separate origin from the SPA.
    """

    def __init__(
        self,
        *,
        api_path: str = "viewer-api",
        use_absolute_urls: bool = False,
        api_domain: str = "",
    ):
        self.api_path = api_path
        self.use_absolute_urls = use_absolute_urls
        self.api_domain = api_domain

    def build_page_url(self, file: str, page: int) -> str:
        return self._build("get-page", {"file": file, "page": page})

    def build_thumb_url(self, file: str, page: int) -> str:
        return self._build("get-thumb", {"file": file, "page": page})

    def build_pdf_url(self, file: str) -> str:
        return self._build("get-pdf", {"file": file})

    def build_resource_url(self, file: str, page: int, resource: str) -> str:
        return self._build(
            "get-resource", {"file": file, "page": page, "resource": resource}
        )

    def build_resource_url_template(self, file: str) -> str:
        """Build a URL template for HTML-external-resources rendering.

        The returned string contains literal ``{0}`` and ``{1}`` placeholders
        that ``groupdocs.viewer`` substitutes at render time (page number and
        resource name). Unlike ``build_resource_url`` / etc., this URL is
        absolute relative to origin and **always** includes ``api_path`` —
        the browser fetches resources directly from inline ``<link href=...>``
        tags in the rendered HTML, with no SPA URL-prepending in front.
        """
        encoded_file = quote(file, safe="")
        api_prefix = "/" + self.api_path.strip("/")
        if self.use_absolute_urls and self.api_domain:
            api_prefix = self.api_domain.rstrip("/") + api_prefix
        return f"{api_prefix}/get-resource?file={encoded_file}&page={{0}}&resource={{1}}"

    def _build(
        self, method_name: str, values: dict[str, Union[str, int]]
    ) -> str:
        qs = urlencode(values)
        if not self.use_absolute_urls:
            return f"/{method_name}?{qs}"
        if not self.api_domain:
            raise ValueError(
                "api_domain must be set when use_absolute_urls=True"
            )
        base = self.api_domain.rstrip("/")
        path = self.api_path.strip("/")
        return f"{base}/{path}/{method_name}?{qs}"

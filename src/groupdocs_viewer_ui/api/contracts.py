"""Pydantic wire models for the viewer HTTP API.

Shapes match the .NET ``GroupDocs.Viewer.UI.Api.Models`` namespace so the
vendored Angular SPA drops in unchanged. Wire format is camelCase JSON;
Python fields stay snake_case.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# --- Requests -----------------------------------------------------------------


class ListDirRequest(_CamelModel):
    path: str = ""


class ViewDataRequest(_CamelModel):
    file: str
    file_type: str | None = None
    password: str | None = None


class CreatePagesRequest(_CamelModel):
    file: str
    file_type: str | None = None
    password: str | None = None
    pages: list[int]


class CreatePdfRequest(_CamelModel):
    file: str
    file_type: str | None = None
    password: str | None = None


# --- Responses ----------------------------------------------------------------


class FileSystemItem(_CamelModel):
    path: str
    name: str
    is_dir: bool
    size: int = 0


class PageData(_CamelModel):
    number: int
    width: int
    height: int
    page_url: str | None = None
    thumb_url: str | None = None


class ViewDataResponse(_CamelModel):
    file: str
    file_type: str
    file_name: str
    can_print: bool
    search_term: str | None = None
    pages: list[PageData]


class CreatePdfResponse(_CamelModel):
    pdf_url: str


class UploadFileResponse(_CamelModel):
    file: str

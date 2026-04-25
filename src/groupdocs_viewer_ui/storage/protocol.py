"""File storage protocol — pluggable backend for document files."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class FileSystemEntry:
    """A listing entry — a file or directory under a storage root."""

    file_path: str
    is_directory: bool
    size: int = 0


@runtime_checkable
class FileStorage(Protocol):
    """Read/write files from some backing store (local disk, S3, Azure, ...).

    Streaming read (``read_file_stream``) arrives in M3 alongside S3/Azure
    backends, where it matters for large-file memory pressure.
    """

    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]: ...

    async def read_file(self, file_path: str) -> bytes: ...

    async def write_file(
        self, file_name: str, data: bytes, *, rewrite: bool = False
    ) -> str: ...

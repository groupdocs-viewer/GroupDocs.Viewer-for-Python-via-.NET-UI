"""Azure Blob Storage backend.

Behind the ``[azure]`` extra (``pip install groupdocs-viewer-net-ui[azure]``).
``azure-storage-blob`` is imported lazily so the rest of the package works
without it.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from typing import Any

from groupdocs_viewer_ui.storage.protocol import FileSystemEntry


class AzureBlobFileStorage:
    """Reads and writes blobs in an Azure Blob Storage container.

    Provide either a ``connection_string`` (we'll build the container client
    for you) or a custom ``container_factory`` for SAS-token wiring or tests.
    """

    def __init__(
        self,
        container: str,
        *,
        connection_string: str | None = None,
        prefix: str = "",
        container_factory: Callable[[], Any] | None = None,
    ):
        self.container = container
        self.prefix = prefix.strip("/")
        self._connection_string = connection_string
        self._container_factory = container_factory

    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]:
        prefix_key = self._key(dir_path).rstrip("/")
        if prefix_key:
            prefix_key += "/"

        dirs: list[FileSystemEntry] = []
        files: list[FileSystemEntry] = []

        async with self._container_cm() as container:
            # walk_blobs(delimiter="/") is the analogue of S3's
            # list_objects_v2 with Delimiter="/" — it yields BlobProperties
            # for files at this level and BlobPrefix for sub-folders.
            async for item in container.walk_blobs(
                name_starts_with=prefix_key, delimiter="/"
            ):
                name: str = item.name
                if name == prefix_key:
                    continue
                is_directory = name.endswith("/")
                rel = self._strip_prefix(name.rstrip("/"))
                if is_directory:
                    dirs.append(
                        FileSystemEntry(
                            file_path=rel, is_directory=True, size=0
                        )
                    )
                else:
                    size = int(getattr(item, "size", 0) or 0)
                    files.append(
                        FileSystemEntry(
                            file_path=rel, is_directory=False, size=size
                        )
                    )

        dirs.sort(key=lambda e: e.file_path.lower())
        files.sort(key=lambda e: e.file_path.lower())
        return dirs + files

    async def read_file(self, file_path: str) -> bytes:
        async with self._container_cm() as container:
            blob = container.get_blob_client(self._key(file_path))
            stream = await blob.download_blob()
            # azure-storage-blob's StorageStreamDownloader returns Any from readall().
            return await stream.readall()  # type: ignore[no-any-return]

    async def write_file(
        self, file_name: str, data: bytes, *, rewrite: bool = False
    ) -> str:
        clean_name = PurePosixPath(file_name.replace("\\", "/")).name
        async with self._container_cm() as container:
            target_name = (
                clean_name if rewrite else await self._next_free_name(container, clean_name)
            )
            blob = container.get_blob_client(self._key(target_name))
            await blob.upload_blob(data, overwrite=True)
        return target_name

    # --- internals --------------------------------------------------------

    @asynccontextmanager
    async def _container_cm(self) -> AsyncIterator[Any]:
        if self._container_factory is not None:
            cm = self._container_factory()
            async with cm as container:
                yield container
            return

        if not self._connection_string:
            raise ValueError(
                "Provide either `connection_string` or `container_factory`."
            )

        try:
            from azure.storage.blob.aio import BlobServiceClient
        except ImportError as exc:
            raise ImportError(
                "AzureBlobFileStorage needs azure-storage-blob — install with "
                "`pip install groupdocs-viewer-net-ui[azure]`."
            ) from exc

        async with BlobServiceClient.from_connection_string(
            self._connection_string
        ) as service:
            container = service.get_container_client(self.container)
            yield container

    def _key(self, file_path: str) -> str:
        rel = file_path.replace("\\", "/").lstrip("/")
        return f"{self.prefix}/{rel}" if self.prefix else rel

    def _strip_prefix(self, key: str) -> str:
        if self.prefix and key.startswith(self.prefix + "/"):
            return key[len(self.prefix) + 1 :]
        return key

    async def _next_free_name(self, container: Any, base_name: str) -> str:
        if not await self._exists(container, base_name):
            return base_name
        p = PurePosixPath(base_name)
        stem, suffix = p.stem, p.suffix
        i = 1
        while True:
            candidate = f"{stem} ({i}){suffix}"
            if not await self._exists(container, candidate):
                return candidate
            i += 1

    async def _exists(self, container: Any, name: str) -> bool:
        blob = container.get_blob_client(self._key(name))
        return bool(await blob.exists())

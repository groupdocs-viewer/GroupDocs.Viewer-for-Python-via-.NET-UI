"""S3-backed file storage.

Behind the ``[s3]`` extra (``pip install groupdocs-viewer-net-ui[s3]``).
``aioboto3`` is imported lazily so the rest of the package works without it.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import PurePosixPath
from typing import Any

from groupdocs_viewer_ui.storage.protocol import FileSystemEntry


class S3FileStorage:
    """Reads and writes files in an S3 bucket.

    Defaults pull AWS credentials from the standard chain (env vars, shared
    config, IAM role). Pass a custom ``client_factory`` to use specific
    credentials, an alternate endpoint (LocalStack), or to inject a fake
    in tests.
    """

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "",
        client_factory: Callable[[], Any] | None = None,
    ):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client_factory = client_factory

    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]:
        prefix_key = self._key(dir_path).rstrip("/")
        if prefix_key:
            prefix_key += "/"

        dirs: list[FileSystemEntry] = []
        files: list[FileSystemEntry] = []

        async with self._client() as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=self.bucket, Prefix=prefix_key, Delimiter="/"
            ):
                for obj in page.get("Contents") or []:
                    key = obj["Key"]
                    if key == prefix_key:
                        continue
                    files.append(
                        FileSystemEntry(
                            file_path=self._strip_prefix(key),
                            is_directory=False,
                            size=obj.get("Size", 0),
                        )
                    )
                for cp in page.get("CommonPrefixes") or []:
                    folder_key = cp["Prefix"].rstrip("/")
                    dirs.append(
                        FileSystemEntry(
                            file_path=self._strip_prefix(folder_key),
                            is_directory=True,
                            size=0,
                        )
                    )

        dirs.sort(key=lambda e: e.file_path.lower())
        files.sort(key=lambda e: e.file_path.lower())
        return dirs + files

    async def read_file(self, file_path: str) -> bytes:
        async with self._client() as s3:
            resp = await s3.get_object(Bucket=self.bucket, Key=self._key(file_path))
            body = resp["Body"]
            try:
                return await body.read()
            finally:
                close = getattr(body, "close", None)
                if close is not None:
                    result = close()
                    if hasattr(result, "__await__"):
                        await result

    async def write_file(
        self, file_name: str, data: bytes, *, rewrite: bool = False
    ) -> str:
        # Strip path separators for safety — uploads land flat under the prefix.
        clean_name = PurePosixPath(file_name.replace("\\", "/")).name

        async with self._client() as s3:
            target_name = (
                clean_name if rewrite else await self._next_free_name(s3, clean_name)
            )
            await s3.put_object(
                Bucket=self.bucket, Key=self._key(target_name), Body=data
            )
        return target_name

    # --- internals --------------------------------------------------------

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[Any]:
        if self._client_factory is not None:
            cm = self._client_factory()
            async with cm as client:
                yield client
            return

        try:
            import aioboto3
        except ImportError as exc:
            raise ImportError(
                "S3FileStorage needs aioboto3 — install with "
                "`pip install groupdocs-viewer-net-ui[s3]`."
            ) from exc

        session = aioboto3.Session()
        async with session.client("s3") as client:
            yield client

    def _key(self, file_path: str) -> str:
        rel = file_path.replace("\\", "/").lstrip("/")
        return f"{self.prefix}/{rel}" if self.prefix else rel

    def _strip_prefix(self, key: str) -> str:
        if self.prefix and key.startswith(self.prefix + "/"):
            return key[len(self.prefix) + 1 :]
        return key

    async def _next_free_name(self, s3: Any, base_name: str) -> str:
        if not await self._exists(s3, base_name):
            return base_name
        p = PurePosixPath(base_name)
        stem, suffix = p.stem, p.suffix
        i = 1
        while True:
            candidate = f"{stem} ({i}){suffix}"
            if not await self._exists(s3, candidate):
                return candidate
            i += 1

    async def _exists(self, s3: Any, name: str) -> bool:
        # Lazy import — botocore is a transitive dep of aioboto3 so it's
        # present whenever this code path is reachable.
        from botocore.exceptions import ClientError

        try:
            await s3.head_object(Bucket=self.bucket, Key=self._key(name))
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

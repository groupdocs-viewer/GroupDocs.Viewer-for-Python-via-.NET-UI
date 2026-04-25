"""Disk-backed file cache.

Layout: ``<root>/<sha256(file_path)[:32]>/<cache_key>``. The hashed prefix
keeps directory names filesystem-safe; the readable suffix makes ad-hoc
debugging by hand viable (you can see ``p1.html``, ``info.json``, etc.).
"""
from __future__ import annotations

import asyncio
import hashlib
import shutil
from pathlib import Path


class LocalFileCache:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def try_get(self, cache_key: str, file_path: str) -> bytes | None:
        return await asyncio.to_thread(self._read_sync, cache_key, file_path)

    async def set(self, cache_key: str, file_path: str, data: bytes) -> None:
        await asyncio.to_thread(self._write_sync, cache_key, file_path, data)

    async def remove(self, file_path: str) -> None:
        await asyncio.to_thread(self._remove_sync, file_path)

    # --- sync helpers -----------------------------------------------------

    def _path_for(self, cache_key: str, file_path: str) -> Path:
        return self._dir_for(file_path) / cache_key

    def _dir_for(self, file_path: str) -> Path:
        digest = hashlib.sha256(file_path.encode("utf-8")).hexdigest()[:32]
        return self.root / digest

    def _read_sync(self, cache_key: str, file_path: str) -> bytes | None:
        path = self._path_for(cache_key, file_path)
        if not path.is_file():
            return None
        return path.read_bytes()

    def _write_sync(self, cache_key: str, file_path: str, data: bytes) -> None:
        path = self._path_for(cache_key, file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _remove_sync(self, file_path: str) -> None:
        directory = self._dir_for(file_path)
        if directory.is_dir():
            shutil.rmtree(directory)

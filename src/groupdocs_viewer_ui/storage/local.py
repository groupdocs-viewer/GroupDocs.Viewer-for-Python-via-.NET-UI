"""Local disk file storage."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Union

from groupdocs_viewer_ui.storage.protocol import FileSystemEntry


class LocalFileStorage:
    """File storage rooted at a local directory.

    All operations resolve paths inside ``root``. Attempts to escape the
    root (e.g. ``../etc/passwd``) raise ``PermissionError``.
    """

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]:
        return await asyncio.to_thread(self._list_sync, dir_path)

    async def read_file(self, file_path: str) -> bytes:
        return await asyncio.to_thread(self._resolve(file_path).read_bytes)

    async def write_file(
        self, file_name: str, data: bytes, *, rewrite: bool = False
    ) -> str:
        return await asyncio.to_thread(self._write_sync, file_name, data, rewrite)

    # --- sync helpers -----------------------------------------------------

    def _list_sync(self, dir_path: str) -> list[FileSystemEntry]:
        target = self._resolve(dir_path) if dir_path else self.root
        if not target.is_dir():
            return []

        dirs: list[FileSystemEntry] = []
        files: list[FileSystemEntry] = []
        for item in target.iterdir():
            if item.name.startswith("."):
                continue
            rel = item.relative_to(self.root).as_posix()
            if item.is_dir():
                dirs.append(FileSystemEntry(file_path=rel, is_directory=True, size=0))
            else:
                files.append(
                    FileSystemEntry(
                        file_path=rel,
                        is_directory=False,
                        size=item.stat().st_size,
                    )
                )

        dirs.sort(key=lambda e: e.file_path.lower())
        files.sort(key=lambda e: e.file_path.lower())
        return dirs + files

    def _write_sync(self, file_name: str, data: bytes, rewrite: bool) -> str:
        # Strip any path separators from the incoming name — uploads land
        # flat at the root, matching the .NET LocalFileStorage contract.
        target = self.root / Path(file_name).name
        if target.exists() and not rewrite:
            stem, suffix = target.stem, target.suffix
            i = 1
            while True:
                candidate = self.root / f"{stem} ({i}){suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                i += 1
        target.write_bytes(data)
        return target.relative_to(self.root).as_posix()

    def _resolve(self, relative: str) -> Path:
        normalized = relative.replace("\\", "/").lstrip("/")
        candidate = (self.root / normalized).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError(f"path outside storage root: {relative!r}") from exc
        return candidate

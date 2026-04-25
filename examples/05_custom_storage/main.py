"""Custom FileStorage backed by SQLite.

Stores documents as BLOBs in a SQLite database. Useful when you don't
want a separate filesystem layout, or when documents are uploaded by
users and you want them in the same store as the rest of your app data.

Implementing your own backend means satisfying three async methods —
that's it. No registration, no entry points, no plugin discovery.
"""
import asyncio
import sqlite3
from pathlib import Path

import uvicorn

from groupdocs_viewer_ui import Config, create_app
from groupdocs_viewer_ui.cache.local import LocalFileCache
from groupdocs_viewer_ui.storage.protocol import FileSystemEntry
from groupdocs_viewer_ui.viewer.selfhost import SelfHostViewer


class SqliteFileStorage:
    """Files are rows in a SQLite table. No folder semantics — every file
    lives at the root, which is fine for many small/medium deployments."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS files "
                "(name TEXT PRIMARY KEY, data BLOB NOT NULL)"
            )

    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]:
        return await asyncio.to_thread(self._list_sync)

    async def read_file(self, file_path: str) -> bytes:
        return await asyncio.to_thread(self._read_sync, file_path)

    async def write_file(
        self, file_name: str, data: bytes, *, rewrite: bool = False
    ) -> str:
        return await asyncio.to_thread(self._write_sync, file_name, data, rewrite)

    # --- sync helpers (run in thread pool) --------------------------------

    def _list_sync(self) -> list[FileSystemEntry]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT name, length(data) FROM files ORDER BY name"
            ).fetchall()
        return [
            FileSystemEntry(file_path=name, is_directory=False, size=size)
            for name, size in rows
        ]

    def _read_sync(self, file_path: str) -> bytes:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data FROM files WHERE name = ?", (file_path,)
            ).fetchone()
        if row is None:
            raise FileNotFoundError(file_path)
        return row[0]

    def _write_sync(self, file_name: str, data: bytes, rewrite: bool) -> str:
        with sqlite3.connect(self._db_path) as conn:
            if rewrite:
                conn.execute(
                    "INSERT OR REPLACE INTO files (name, data) VALUES (?, ?)",
                    (file_name, data),
                )
                return file_name
            target = file_name
            i = 1
            while conn.execute(
                "SELECT 1 FROM files WHERE name = ?", (target,)
            ).fetchone():
                stem, dot, ext = file_name.rpartition(".")
                target = f"{stem} ({i}).{ext}" if dot else f"{file_name} ({i})"
                i += 1
            conn.execute(
                "INSERT INTO files (name, data) VALUES (?, ?)", (target, data)
            )
            return target


ROOT = Path(__file__).parent
storage = SqliteFileStorage(ROOT / "documents.db")

app = create_app(
    Config(),
    storage=storage,
    cache=LocalFileCache(ROOT / ".viewer-cache"),
    viewer=SelfHostViewer(storage=storage),
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

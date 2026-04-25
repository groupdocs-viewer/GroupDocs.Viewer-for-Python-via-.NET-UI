# Custom Storage — SQLite

Plug in your own document store by satisfying the `FileStorage` protocol.

## The protocol

```python
class FileStorage(Protocol):
    async def list_dirs_and_files(self, dir_path: str) -> list[FileSystemEntry]: ...
    async def read_file(self, file_path: str) -> bytes: ...
    async def write_file(self, file_name: str, data: bytes, *, rewrite: bool = False) -> str: ...
```

That's it — three async methods. No registration, no entry points, no plugin discovery. Pass your impl into `create_app(storage=...)`.

## What this example does

`SqliteFileStorage` puts documents into a single SQLite table:

```
CREATE TABLE files (name TEXT PRIMARY KEY, data BLOB NOT NULL)
```

Every file lives at the root (no folders). The sync `sqlite3` calls are offloaded to the default thread pool via `asyncio.to_thread`, matching the pattern used by `LocalFileStorage`.

## Run

```bash
pip install groupdocs-viewer-net-ui uvicorn
python main.py
# → http://127.0.0.1:8080/viewer/
```

Upload a document via the SPA's Upload button — it lands in `documents.db`.

## Adapting to other backends

The same pattern works for anything: HTTP-fetched documents, S3 paths from a manifest, ORM-backed user uploads. Whatever your store is, wrap it in three async methods and `create_app` plumbs it through.

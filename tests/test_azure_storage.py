"""Behavioral tests for AzureBlobFileStorage using an in-test fake container."""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from groupdocs_viewer_ui.storage.azure import AzureBlobFileStorage

# --- a tiny Azure container fake ---------------------------------------------


class _BlobProperties:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


class _BlobPrefix:
    def __init__(self, name: str):
        self.name = name  # always ends with "/"


class _DownloadStream:
    def __init__(self, data: bytes):
        self._data = data

    async def readall(self) -> bytes:
        return self._data


class _BlobClient:
    def __init__(self, container: _FakeContainer, name: str):
        self._container = container
        self._name = name

    async def download_blob(self) -> _DownloadStream:
        if self._name not in self._container.blobs:
            raise FileNotFoundError(self._name)
        return _DownloadStream(self._container.blobs[self._name])

    async def upload_blob(self, data: bytes, *, overwrite: bool = False) -> None:
        if not overwrite and self._name in self._container.blobs:
            raise FileExistsError(self._name)
        self._container.blobs[self._name] = data

    async def exists(self) -> bool:
        return self._name in self._container.blobs


class _FakeContainer:
    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    def get_blob_client(self, name: str) -> _BlobClient:
        return _BlobClient(self, name)

    async def walk_blobs(self, *, name_starts_with: str = "", delimiter: str = "/"):
        prefix = name_starts_with or ""
        seen_dirs: set[str] = set()
        # Iterate in stable order so tests are deterministic.
        for name in sorted(self.blobs.keys()):
            if not name.startswith(prefix):
                continue
            tail = name[len(prefix):]
            if delimiter and delimiter in tail:
                folder = tail.split(delimiter, 1)[0]
                full = prefix + folder + delimiter
                if full in seen_dirs:
                    continue
                seen_dirs.add(full)
                yield _BlobPrefix(full)
            else:
                yield _BlobProperties(name=name, size=len(self.blobs[name]))


@pytest.fixture
def fake_container():
    container = _FakeContainer()

    @asynccontextmanager
    async def factory():
        yield container

    return container, factory


# --- tests --------------------------------------------------------------------


def test_construction_does_not_require_azure_sdk():
    storage = AzureBlobFileStorage("docs", prefix="archive")
    assert storage.container == "docs"
    assert storage.prefix == "archive"


@pytest.mark.asyncio
async def test_list_returns_files_and_folders_sorted(fake_container):
    container, factory = fake_container
    container.blobs.update(
        {"a.docx": b"aaa", "b.pdf": b"bb", "sub/c.txt": b"cc"}
    )
    storage = AzureBlobFileStorage("c", container_factory=factory)
    entries = await storage.list_dirs_and_files("")
    assert [(e.file_path, e.is_directory, e.size) for e in entries] == [
        ("sub", True, 0),
        ("a.docx", False, 3),
        ("b.pdf", False, 2),
    ]


@pytest.mark.asyncio
async def test_list_with_prefix_strips_it(fake_container):
    container, factory = fake_container
    container.blobs.update(
        {"docs/a.docx": b"aa", "docs/sub/c.txt": b"c", "other/x.txt": b"x"}
    )
    storage = AzureBlobFileStorage("c", prefix="docs", container_factory=factory)
    entries = await storage.list_dirs_and_files("")
    assert [e.file_path for e in entries] == ["sub", "a.docx"]


@pytest.mark.asyncio
async def test_read_file_returns_bytes(fake_container):
    container, factory = fake_container
    container.blobs["a.docx"] = b"hello"
    storage = AzureBlobFileStorage("c", container_factory=factory)
    assert await storage.read_file("a.docx") == b"hello"


@pytest.mark.asyncio
async def test_write_file_generates_unique_name(fake_container):
    container, factory = fake_container
    storage = AzureBlobFileStorage("c", container_factory=factory)
    first = await storage.write_file("doc.txt", b"1")
    second = await storage.write_file("doc.txt", b"2")
    assert first == "doc.txt"
    assert second == "doc (1).txt"
    assert container.blobs["doc.txt"] == b"1"
    assert container.blobs["doc (1).txt"] == b"2"


@pytest.mark.asyncio
async def test_write_file_rewrite_overwrites(fake_container):
    container, factory = fake_container
    storage = AzureBlobFileStorage("c", container_factory=factory)
    await storage.write_file("doc.txt", b"1")
    result = await storage.write_file("doc.txt", b"updated", rewrite=True)
    assert result == "doc.txt"
    assert container.blobs["doc.txt"] == b"updated"


@pytest.mark.asyncio
async def test_write_strips_path_separators(fake_container):
    container, factory = fake_container
    storage = AzureBlobFileStorage("c", container_factory=factory)
    result = await storage.write_file("../escape.txt", b"x")
    assert result == "escape.txt"
    assert "escape.txt" in container.blobs


def test_construction_without_anything_raises():
    storage = AzureBlobFileStorage("c")

    async def go():
        async with storage._container_cm():
            pass

    import asyncio

    with pytest.raises(ValueError, match="connection_string"):
        asyncio.run(go())

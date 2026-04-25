"""Behavioral tests for S3FileStorage using a hand-rolled fake S3 client.

Avoids pulling moto/aioboto3 into the dev deps for now — the fake here
covers the API surface S3FileStorage uses (list_objects_v2 paginator,
get_object, put_object, head_object).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from groupdocs_viewer_ui.storage.s3 import S3FileStorage


# --- a tiny S3 fake -----------------------------------------------------------


class _ClientError(Exception):
    """Stand-in for botocore.exceptions.ClientError."""

    def __init__(self, code: str):
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class _Body:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self) -> bytes:
        return self._data

    async def close(self) -> None:
        pass


class _Paginator:
    def __init__(self, store: dict[str, bytes]):
        self._store = store

    async def paginate(self, *, Bucket, Prefix, Delimiter):  # noqa: N803
        # Single-page response, mimicking list_objects_v2's shape.
        contents = []
        common_prefixes = set()
        for key, data in self._store.items():
            if not key.startswith(Prefix):
                continue
            tail = key[len(Prefix):]
            if Delimiter and Delimiter in tail:
                # Sub-folder; collapse into CommonPrefixes
                folder = tail.split(Delimiter, 1)[0] + Delimiter
                common_prefixes.add(Prefix + folder)
            else:
                contents.append({"Key": key, "Size": len(data)})
        yield {
            "Contents": contents,
            "CommonPrefixes": [{"Prefix": p} for p in sorted(common_prefixes)],
        }


class _FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def get_paginator(self, op: str) -> _Paginator:
        assert op == "list_objects_v2"
        return _Paginator(self.objects)

    async def get_object(self, *, Bucket, Key):  # noqa: N803
        if Key not in self.objects:
            raise _ClientError("NoSuchKey")
        return {"Body": _Body(self.objects[Key])}

    async def put_object(self, *, Bucket, Key, Body):  # noqa: N803
        self.objects[Key] = Body

    async def head_object(self, *, Bucket, Key):  # noqa: N803
        if Key not in self.objects:
            raise _ClientError("404")


def _patch_client_error(monkeypatch):
    """S3FileStorage._exists imports botocore.exceptions.ClientError lazily.
    Patch the import to point at our fake, since botocore may not be installed.
    """
    import sys
    import types

    fake_botocore = types.ModuleType("botocore")
    fake_exc = types.ModuleType("botocore.exceptions")
    fake_exc.ClientError = _ClientError  # type: ignore[attr-defined]
    fake_botocore.exceptions = fake_exc  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_exc)


@pytest.fixture
def fake_s3(monkeypatch):
    _patch_client_error(monkeypatch)
    client = _FakeS3()

    @asynccontextmanager
    async def factory():
        yield client

    return client, factory


# --- tests --------------------------------------------------------------------


def test_construction_does_not_require_aioboto3():
    storage = S3FileStorage("my-bucket", prefix="docs")
    assert storage.bucket == "my-bucket"
    assert storage.prefix == "docs"


@pytest.mark.asyncio
async def test_list_returns_files_and_folders(fake_s3):
    client, factory = fake_s3
    client.objects.update(
        {"a.docx": b"aaa", "b.pdf": b"bb", "sub/c.txt": b"cc"}
    )
    storage = S3FileStorage("bk", client_factory=factory)
    entries = await storage.list_dirs_and_files("")
    assert [(e.file_path, e.is_directory, e.size) for e in entries] == [
        ("sub", True, 0),
        ("a.docx", False, 3),
        ("b.pdf", False, 2),
    ]


@pytest.mark.asyncio
async def test_list_with_prefix_strips_prefix_from_results(fake_s3):
    client, factory = fake_s3
    client.objects.update(
        {"docs/a.docx": b"aa", "docs/sub/c.txt": b"c", "other/x.txt": b"x"}
    )
    storage = S3FileStorage("bk", prefix="docs", client_factory=factory)
    entries = await storage.list_dirs_and_files("")
    assert [e.file_path for e in entries] == ["sub", "a.docx"]


@pytest.mark.asyncio
async def test_read_file_returns_bytes(fake_s3):
    client, factory = fake_s3
    client.objects["a.docx"] = b"hello"
    storage = S3FileStorage("bk", client_factory=factory)
    assert await storage.read_file("a.docx") == b"hello"


@pytest.mark.asyncio
async def test_write_file_generates_unique_name(fake_s3):
    client, factory = fake_s3
    storage = S3FileStorage("bk", client_factory=factory)
    first = await storage.write_file("doc.txt", b"1")
    second = await storage.write_file("doc.txt", b"2")
    assert first == "doc.txt"
    assert second == "doc (1).txt"
    assert client.objects["doc.txt"] == b"1"
    assert client.objects["doc (1).txt"] == b"2"


@pytest.mark.asyncio
async def test_write_file_rewrite_overwrites(fake_s3):
    client, factory = fake_s3
    storage = S3FileStorage("bk", client_factory=factory)
    await storage.write_file("doc.txt", b"1")
    result = await storage.write_file("doc.txt", b"updated", rewrite=True)
    assert result == "doc.txt"
    assert client.objects["doc.txt"] == b"updated"


@pytest.mark.asyncio
async def test_write_strips_path_separators(fake_s3):
    client, factory = fake_s3
    storage = S3FileStorage("bk", client_factory=factory)
    result = await storage.write_file("../escape.txt", b"x")
    assert result == "escape.txt"
    assert "escape.txt" in client.objects


def test_construction_without_factory_raises_helpful_error_when_aioboto3_missing(monkeypatch):
    """If aioboto3 isn't installed, opening the client should raise an actionable error."""
    import sys

    storage = S3FileStorage("bk")
    # Force-fail the import.
    monkeypatch.setitem(sys.modules, "aioboto3", None)

    async def go():
        async with storage._client():  # noqa: SLF001
            pass

    import asyncio

    with pytest.raises(ImportError, match=r"\[s3\]"):
        asyncio.run(go())

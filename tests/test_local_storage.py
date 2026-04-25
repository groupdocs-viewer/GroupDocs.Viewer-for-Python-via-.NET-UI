from pathlib import Path

import pytest

from groupdocs_viewer_ui.storage.local import LocalFileStorage


@pytest.mark.asyncio
async def test_list_empty_root(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    assert await storage.list_dirs_and_files("") == []


@pytest.mark.asyncio
async def test_list_files_and_dirs_sorted_dirs_first(tmp_path: Path):
    (tmp_path / "a.docx").write_bytes(b"aaa")
    (tmp_path / "b.pdf").write_bytes(b"bb")
    (tmp_path / "sub").mkdir()

    storage = LocalFileStorage(tmp_path)
    entries = await storage.list_dirs_and_files("")
    assert [e.file_path for e in entries] == ["sub", "a.docx", "b.pdf"]
    assert entries[0].is_directory is True
    assert entries[1].is_directory is False
    assert entries[1].size == 3


@pytest.mark.asyncio
async def test_list_skips_hidden(tmp_path: Path):
    (tmp_path / ".hidden").write_bytes(b"x")
    (tmp_path / "visible.txt").write_bytes(b"x")
    storage = LocalFileStorage(tmp_path)
    entries = await storage.list_dirs_and_files("")
    assert [e.file_path for e in entries] == ["visible.txt"]


@pytest.mark.asyncio
async def test_read_file(tmp_path: Path):
    (tmp_path / "a.txt").write_bytes(b"hello")
    storage = LocalFileStorage(tmp_path)
    assert await storage.read_file("a.txt") == b"hello"


@pytest.mark.asyncio
async def test_write_file_generates_unique_name_by_default(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    first = await storage.write_file("doc.txt", b"1")
    second = await storage.write_file("doc.txt", b"2")
    assert first == "doc.txt"
    assert second == "doc (1).txt"
    assert (tmp_path / "doc.txt").read_bytes() == b"1"
    assert (tmp_path / "doc (1).txt").read_bytes() == b"2"


@pytest.mark.asyncio
async def test_write_file_rewrite_overwrites(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    await storage.write_file("doc.txt", b"1")
    result = await storage.write_file("doc.txt", b"updated", rewrite=True)
    assert result == "doc.txt"
    assert (tmp_path / "doc.txt").read_bytes() == b"updated"


@pytest.mark.asyncio
async def test_write_strips_incoming_path_separators(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    result = await storage.write_file("../escape.txt", b"x")
    # The incoming name is reduced to its basename; file lands at the root.
    assert result == "escape.txt"
    assert (tmp_path / "escape.txt").exists()


@pytest.mark.asyncio
async def test_read_blocks_path_traversal(tmp_path: Path):
    storage = LocalFileStorage(tmp_path)
    with pytest.raises(PermissionError):
        await storage.read_file("../etc/passwd")

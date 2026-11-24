
from pathlib import Path

import pytest

from infrastructure.adapters.file_storage import LocalFileStorage


class FakeUpload:
    def __init__(self, chunks: list[bytes]):
        self.chunks = iter(chunks)
        self.read_calls = []

    async def read(self, size: int = -1) -> bytes:
        self.read_calls.append(size)
        return next(self.chunks, b"")


@pytest.mark.asyncio
async def test_store_writes_upload_in_chunks(tmp_path: Path):
    storage = LocalFileStorage(base_dir=tmp_path)
    upload = FakeUpload([b"first ", b"second ", b"third"])

    stored_filename = await storage.store(
        project_id=10,
        original_filename="document.txt",
        source=upload,
        chunk_size=4,
    )

    stored_path = tmp_path / "assets" / "files" / "10" / stored_filename

    assert stored_path.is_file()
    assert stored_path.read_bytes() == b"first second third"
    assert upload.read_calls == [4, 4, 4, 4]
    assert stored_filename.endswith("_document.txt")


@pytest.mark.asyncio
async def test_store_generates_unique_sanitized_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import infrastructure.adapters.file_storage as storage_module

    generated_prefixes = iter(["a", "a", "bc"])

    def fake_choices(population, k):
        prefix = next(generated_prefixes)
        assert len(prefix) == k
        return list(prefix)

    monkeypatch.setattr(storage_module, "choices", fake_choices)

    storage = LocalFileStorage(base_dir=tmp_path)

    first_upload = FakeUpload([b"first"])
    second_upload = FakeUpload([b"second"])

    first_filename = await storage.store(
        project_id=10,
        original_filename="report file!.txt",
        source=first_upload,
        chunk_size=64,
    )

    second_filename = await storage.store(
        project_id=10,
        original_filename="report file!.txt",
        source=second_upload,
        chunk_size=64,
    )

    assert first_filename == "a_reportfile.txt"
    assert second_filename == "bc_reportfile.txt"

    project_dir = tmp_path / "assets" / "files" / "10"

    assert (project_dir / first_filename).read_bytes() == b"first"
    assert (project_dir / second_filename).read_bytes() == b"second"

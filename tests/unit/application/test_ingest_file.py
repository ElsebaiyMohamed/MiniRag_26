
import asyncio

import pytest

from application.errors import (
    AssetAlreadyExists,
    FileStorageError,
    UnsupportedUploadType,
    UploadTooLarge,
)
from application.ports import AssetRecord, NewAsset
from application.use_cases import IngestFile, IngestFileCommand
from ingestion.loaders import create_default_loader_registry


class FakeUpload:
    def __init__(
        self,
        filename="document.txt",
        content_type="text/plain",
        size=100,
    ):
        self.filename = filename
        self.content_type = content_type
        self.size = size

    async def read(self, size=-1):
        return b"test content"


class FakeFileStorage:
    def __init__(self, filename="stored_document.txt", error=None):
        self.filename = filename
        self.error = error
        self.calls = []

    async def store(
        self,
        project_id,
        original_filename,
        source,
        chunk_size,
    ):
        self.calls.append({
            "project_id": project_id,
            "original_filename": original_filename,
            "source": source,
            "chunk_size": chunk_size,
        })

        if self.error:
            raise self.error

        return self.filename

    async def delete(self, project_id, stored_filename):
        self.deleted_files = getattr(self, "deleted_files", [])
        self.deleted_files.append((project_id, stored_filename))

class FakeProjectRepository:
    def __init__(self, project_id=10):
        self.project_id = project_id
        self.calls = []

    async def get_or_create(self, project_id):
        self.calls.append(project_id)
        return self.project_id


class FakeAssetRepository:
    def __init__(self):
        self.assets = []

    async def create(self, asset: NewAsset):
        self.assets.append(asset)
        return AssetRecord(asset_name=asset.asset_name)


def build_use_case(
    *,
    allowed_mime_types=None,
    max_size_bytes=1024,
    storage_error=None,
):
    storage = FakeFileStorage(error=storage_error)
    projects = FakeProjectRepository()
    assets = FakeAssetRepository()

    use_case = IngestFile(
        loader_registry=create_default_loader_registry(),
        file_storage=storage,
        project_repository=projects,
        asset_repository=assets,
        allowed_mime_types=allowed_mime_types or {
            "text/plain",
            "application/pdf",
            "text/markdown",
            "text/x-markdown",
        },
        max_size_bytes=max_size_bytes,
        chunk_size=64,
    )

    return use_case, storage, projects, assets


def test_ingest_file_success():
    use_case, storage, projects, assets = build_use_case()
    upload = FakeUpload()

    result = asyncio.run(
        use_case.execute(
            IngestFileCommand(project_id=5, file=upload)
        )
    )

    assert result.file_id == "stored_document.txt"

    assert projects.calls == [5]
    assert len(storage.calls) == 1

    assert assets.assets == [
        NewAsset(
            project_id=10,
            asset_type="file",
            asset_name="stored_document.txt",
            asset_size=100,
            asset_status=0,
        )
    ]


def test_ingest_file_rejects_unsupported_extension():
    use_case, storage, projects, assets = build_use_case()
    upload = FakeUpload(filename="document.docx")

    with pytest.raises(UnsupportedUploadType):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(project_id=5, file=upload)
            )
        )

    assert projects.calls == []
    assert storage.calls == []
    assert assets.assets == []


def test_ingest_file_rejects_mime_type_not_supported_by_loader():
    use_case, storage, projects, assets = build_use_case()
    upload = FakeUpload(
        filename="document.txt",
        content_type="application/pdf",
    )

    with pytest.raises(UnsupportedUploadType):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(project_id=5, file=upload)
            )
        )

    assert projects.calls == []
    assert storage.calls == []
    assert assets.assets == []


def test_ingest_file_rejects_mime_type_outside_legacy_allowlist():
    use_case, storage, projects, assets = build_use_case(
        allowed_mime_types={"application/pdf"}
    )
    upload = FakeUpload(
        filename="document.txt",
        content_type="text/plain",
    )

    with pytest.raises(UnsupportedUploadType):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(project_id=5, file=upload)
            )
        )

    assert projects.calls == []
    assert storage.calls == []
    assert assets.assets == []


def test_ingest_file_rejects_oversized_file():
    use_case, storage, projects, assets = build_use_case(
        max_size_bytes=50
    )
    upload = FakeUpload(size=100)

    with pytest.raises(UploadTooLarge):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(project_id=5, file=upload)
            )
        )

    assert projects.calls == []
    assert storage.calls == []
    assert assets.assets == []


def test_ingest_file_translates_storage_failure():
    use_case, storage, projects, assets = build_use_case(
        storage_error=OSError("disk unavailable")
    )

    with pytest.raises(FileStorageError):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(
                    project_id=5,
                    file=FakeUpload(),
                )
            )
        )

    assert projects.calls == [5]
    assert len(storage.calls) == 1
    assert assets.assets == []

def test_ingest_file_removes_stored_file_when_asset_already_exists():
    use_case, storage, _projects, assets = build_use_case()

    async def duplicate_asset(asset):
        raise AssetAlreadyExists

    assets.create = duplicate_asset

    with pytest.raises(AssetAlreadyExists):
        asyncio.run(
            use_case.execute(
                IngestFileCommand(
                    project_id=5,
                    file=FakeUpload(),
                )
            )
        )

    assert storage.deleted_files == [
        (10, "stored_document.txt")
    ]
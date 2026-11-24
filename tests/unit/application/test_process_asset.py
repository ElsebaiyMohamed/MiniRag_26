
import asyncio
from pathlib import Path

import pytest

from application.errors import UnsupportedUploadType
from application.ports import NewChunk
from application.use_cases.process_asset import (
    ProcessAsset,
    ProcessAssetCommand,
    ProcessAssetResult,
)
from ingestion.chunkers import Chunk
from ingestion.loaders import LoadedDocument


class FakeFileResolver:
    def __init__(self, path: Path):
        self.path = path

    def resolve(self, project_id: int, asset_name: str) -> Path:
        return self.path


class FakeLoader:
    mime_types = ("text/plain",)

    def __init__(self, documents):
        self.documents = documents
        self.loaded_path = None

    def load(self, path: Path):
        self.loaded_path = path
        return self.documents


class FakeLoaderRegistry:
    def __init__(self, loader):
        self.loader = loader
        self.resolved_path = None

    def for_path(self, path: Path):
        self.resolved_path = path
        return self.loader


class FakeChunker:
    def __init__(self, chunks):
        self.chunks = chunks
        self.received_documents = None
        self.received_options = None

    def chunk(self, documents, chunk_size, chunk_overlap):
        self.received_documents = list(documents)
        self.received_options = (chunk_size, chunk_overlap)
        return self.chunks


class FakeChunkerFactory:
    def __init__(self, chunker):
        self.chunker = chunker
        self.requested_name = None

    def get_chunker(self, name: str):
        self.requested_name = name
        return self.chunker


class FakeProcessingRepository:
    def __init__(self, result: int = 1):
        self.result = result
        self.asset_id = None
        self.chunks = None
        self.calls = 0

    async def persist(self, asset_id: int, chunks: list[NewChunk]):
        self.calls += 1
        self.asset_id = asset_id
        self.chunks = chunks
        return self.result


def build_use_case(
    file_path: Path,
    chunks=None,
    persistence_result=1,
):
    documents = [
        LoadedDocument(
            text="This is a test document.",
            metadata={"source": "test.txt"},
        )
    ]

    loader = FakeLoader(documents)
    chunker = FakeChunker(
        chunks if chunks is not None else [
            Chunk(
                text="This is a test document.",
                order=0,
                metadata={"source": "test.txt"},
            )
        ]
    )

    loader_registry = FakeLoaderRegistry(loader)
    chunker_factory = FakeChunkerFactory(chunker)
    repository = FakeProcessingRepository(persistence_result)

    use_case = ProcessAsset(
        file_resolver=FakeFileResolver(file_path),
        loader_registry=loader_registry,
        chunker_factory=chunker_factory,
        processing_repository=repository,
    )

    return (
        use_case,
        loader,
        loader_registry,
        chunker,
        chunker_factory,
        repository,
    )


def test_process_asset_success(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    (
        use_case,
        loader,
        loader_registry,
        chunker,
        chunker_factory,
        repository,
    ) = build_use_case(file_path)

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="test.txt",
                chunker="default",
                chunk_size=100,
                overlap_size=20,
            )
        )
    )

    assert result == ProcessAssetResult(
        success=True,
        chunk_count=1,
    )

    assert loader.loaded_path == file_path
    assert loader_registry.resolved_path == file_path
    assert chunker_factory.requested_name == "default"
    assert chunker.received_options == (100, 20)

    assert repository.calls == 1
    assert repository.asset_id == 20
    assert repository.chunks == [
        NewChunk(
            project_id=10,
            asset_id=20,
            text="This is a test document.",
            order=0,
            metadata={"source": "test.txt"},
        )
    ]


def test_process_asset_returns_failure_for_missing_file(tmp_path):
    file_path = tmp_path / "missing.txt"

    (
        use_case,
        _loader,
        loader_registry,
        _chunker,
        _chunker_factory,
        repository,
    ) = build_use_case(file_path)

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="missing.txt",
            )
        )
    )

    assert result == ProcessAssetResult(success=False)
    assert loader_registry.resolved_path is None
    assert repository.calls == 0


def test_process_asset_returns_failure_for_empty_chunks(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("test content")

    (
        use_case,
        _loader,
        _loader_registry,
        _chunker,
        _chunker_factory,
        repository,
    ) = build_use_case(file_path, chunks=[])

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="empty.txt",
            )
        )
    )

    assert result == ProcessAssetResult(success=False)
    assert repository.calls == 0

def test_process_asset_returns_failure_for_empty_documents(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("")

    (
        use_case,
        loader,
        _loader_registry,
        _chunker,
        _chunker_factory,
        repository,
    ) = build_use_case(file_path)

    # Simulate a loader that successfully returns no documents.
    loader.documents = []

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="empty.txt",
            )
        )
    )

    assert result == ProcessAssetResult(success=False)
    assert repository.calls == 0

def test_process_asset_returns_failure_when_persistence_returns_zero(
    tmp_path,
):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    (
        use_case,
        _loader,
        _loader_registry,
        _chunker,
        _chunker_factory,
        repository,
    ) = build_use_case(
        file_path,
        persistence_result=0,
    )

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="test.txt",
            )
        )
    )

    assert result == ProcessAssetResult(success=False)
    assert repository.calls == 1
    assert repository.asset_id == 20


def test_process_asset_preserves_loader_and_chunker_options(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    (
        use_case,
        _loader,
        _loader_registry,
        chunker,
        chunker_factory,
        _repository,
    ) = build_use_case(file_path)

    asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="test.txt",
                chunker="custom",
                chunk_size=250,
                overlap_size=50,
            )
        )
    )

    assert chunker_factory.requested_name == "custom"
    assert chunker.received_options == (250, 50)

def test_process_asset_returns_failure_for_unsupported_loader(tmp_path):
    file_path = tmp_path / "unsupported.xyz"
    file_path.write_text("test content")

    class UnsupportedLoaderRegistry:
        def for_path(self, path):
            raise UnsupportedUploadType

    use_case, _, _, _, _, repository = build_use_case(file_path)
    use_case.loader_registry = UnsupportedLoaderRegistry()

    result = asyncio.run(
        use_case.execute(
            ProcessAssetCommand(
                project_id=10,
                asset_id=20,
                asset_name="unsupported.xyz",
            )
        )
    )

    assert result == ProcessAssetResult(success=False)
    assert repository.calls == 0


def test_process_asset_propagates_loader_failure(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")

    class FailingLoader:
        mime_types = ("text/plain",)

        def load(self, path):
            raise RuntimeError("Loader failed")

    use_case, _, loader_registry, _, _, repository = build_use_case(
        file_path
    )
    loader_registry.loader = FailingLoader()

    with pytest.raises(RuntimeError, match="Loader failed"):
        asyncio.run(
            use_case.execute(
                ProcessAssetCommand(
                    project_id=10,
                    asset_id=20,
                    asset_name="test.txt",
                )
            )
        )

    assert repository.calls == 0
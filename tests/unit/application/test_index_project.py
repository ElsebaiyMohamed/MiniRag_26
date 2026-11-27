
import asyncio

from application.ports import (
    EmbeddingResult,
    IndexableAsset,
    IndexableChunk,
    VectorInsertResult,
)
from application.use_cases.index_project import (
    IndexProject,
    IndexProjectCommand,
)
from models.enums.AssetTypeEnums import AssetStatus


class FakeAssetRepository:
    def __init__(self, assets):
        self.assets = assets
        self.status_updates = []
        self.calls = []

    async def get_project_assets(self, project_id, asset_type):
        self.calls.append((project_id, asset_type))
        return self.assets

    async def set_status(self, asset_id, status):
        self.status_updates.append((asset_id, status))


class FakeChunkRepository:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get_page(self, asset_id, page_no, page_size):
        self.calls.append((asset_id, page_no, page_size))
        return self.pages.get((asset_id, page_no), [])


class FakeEmbedder:
    embedding_size = 3

    def __init__(self, result=None):
        self.result = result or EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3]],
            success=True,
        )
        self.calls = []

    async def embed(self, texts):
        self.calls.append(texts)
        return self.result


class FakeVectorStore:
    def __init__(self, insert_result=None, collection_result=True):
        self.insert_result = insert_result or VectorInsertResult(
            success=1,
            failed=0,
        )
        self.collection_result = collection_result
        self.collection_calls = []
        self.delete_calls = []
        self.insert_calls = []

    async def create_collection(
        self, project_id, embedding_size, do_reset=False
    ):
        self.collection_calls.append(
            (project_id, embedding_size, do_reset)
        )
        return self.collection_result

    async def delete_asset_vectors(self, project_id, asset_id):
        self.delete_calls.append((project_id, asset_id))
        return 0

    async def insert_many(
        self,
        project_id,
        texts,
        vectors,
        chunk_ids,
        asset_ids,
        metadatas,
    ):
        self.insert_calls.append({
            "project_id": project_id,
            "texts": texts,
            "vectors": vectors,
            "chunk_ids": chunk_ids,
            "asset_ids": asset_ids,
            "metadatas": metadatas,
        })
        return self.insert_result


def build_use_case(
    assets,
    pages,
    *,
    embedding_result=None,
    insert_result=None,
    collection_result=True,
):
    asset_repository = FakeAssetRepository(assets)
    chunk_repository = FakeChunkRepository(pages)
    embedder = FakeEmbedder(embedding_result)
    vector_store = FakeVectorStore(
        insert_result=insert_result,
        collection_result=collection_result,
    )

    use_case = IndexProject(
        asset_repository=asset_repository,
        chunk_repository=chunk_repository,
        embedder=embedder,
        vector_store=vector_store,
    )

    return (
        use_case,
        asset_repository,
        chunk_repository,
        embedder,
        vector_store,
    )


def make_chunk(chunk_id, asset_id=20):
    return IndexableChunk(
        chunk_id=chunk_id,
        asset_id=asset_id,
        text=f"Chunk {chunk_id}",
        metadata={"source": "document.txt"},
    )


def test_index_project_success_with_pagination():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.CHUNKED.value,
        )
    ]

    pages = {
        (20, 1): [make_chunk(1), make_chunk(2)],
        (20, 2): [make_chunk(3), make_chunk(4)],
    }

    embedding_result = EmbeddingResult(
        vectors=[
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ],
        success=True,
    )

    (
        use_case,
        asset_repository,
        chunk_repository,
        embedder,
        vector_store,
    ) = build_use_case(
        assets,
        pages,
        embedding_result=embedding_result,
        insert_result=VectorInsertResult(success=2, failed=0),
    )

    result = asyncio.run(
        use_case.execute(
            IndexProjectCommand(
                project_id=10,
                page_size=2,
            )
        )
    )

    assert result.outcome == "success"
    assert result.project_status_before_run == {
        "total_files": 1,
        "uploaded_files": 0,
        "chunked_files": 1,
        "indexed_files": 0,
    }
    assert result.call_status == {
        "file_success": 1,
        "file_failed": 0,
        "chunk_success": 4,
        "chunk_failed": 0,
    }

    assert asset_repository.calls == [(10, "file")]
    assert asset_repository.status_updates == [
        (20, AssetStatus.INDEXED.value)
    ]

    assert chunk_repository.calls == [
        (20, 1, 2),
        (20, 2, 2),
        (20, 3, 2),
    ]

    assert len(embedder.calls) == 2
    assert vector_store.collection_calls == [(10, 3, False)]
    assert vector_store.delete_calls == [(10, 20)]
    assert len(vector_store.insert_calls) == 2


def test_index_project_deletes_all_asset_vectors_on_partial_failure():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.CHUNKED.value,
        )
    ]

    pages = {
        (20, 1): [make_chunk(1), make_chunk(2)],
    }

    (
        use_case,
        asset_repository,
        _chunk_repository,
        _embedder,
        vector_store,
    ) = build_use_case(
        assets,
        pages,
        embedding_result=EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            success=True,
        ),
        insert_result=VectorInsertResult(success=1, failed=1),
    )

    result = asyncio.run(
        use_case.execute(IndexProjectCommand(project_id=10))
    )

    assert result.outcome == "failed"
    assert result.call_status == {
        "file_success": 0,
        "file_failed": 1,
        "chunk_success": 0,
        "chunk_failed": 2,
    }

    # Initial cleanup + cleanup after partial insertion failure.
    assert vector_store.delete_calls == [
        (10, 20),
        (10, 20),
    ]

    # The asset must not be marked INDEXED.
    assert asset_repository.status_updates == []


def test_index_project_marks_asset_failed_when_embedding_fails():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.CHUNKED.value,
        )
    ]

    pages = {
        (20, 1): [make_chunk(1)],
    }

    (
        use_case,
        asset_repository,
        _chunk_repository,
        _embedder,
        vector_store,
    ) = build_use_case(
        assets,
        pages,
        embedding_result=EmbeddingResult(
            vectors=[],
            success=False,
            error="Embedding provider unavailable",
        ),
    )

    result = asyncio.run(
        use_case.execute(IndexProjectCommand(project_id=10))
    )

    assert result.outcome == "failed"
    assert result.call_status == {
        "file_success": 0,
        "file_failed": 1,
        "chunk_success": 0,
        "chunk_failed": 1,
    }

    assert vector_store.insert_calls == []
    assert vector_store.delete_calls == [
        (10, 20),
        (10, 20),
    ]
    assert asset_repository.status_updates == []


def test_index_project_returns_no_files_when_project_has_no_assets():
    (
        use_case,
        asset_repository,
        chunk_repository,
        embedder,
        vector_store,
    ) = build_use_case([], {})

    result = asyncio.run(
        use_case.execute(IndexProjectCommand(project_id=10))
    )

    assert result.outcome == "no_files"
    assert result.project_status_before_run == {
        "total_files": 0,
        "uploaded_files": 0,
        "chunked_files": 0,
        "indexed_files": 0,
    }
    assert result.call_status == {
        "file_success": 0,
        "file_failed": 0,
        "chunk_success": 0,
        "chunk_failed": 0,
    }

    assert asset_repository.calls == [(10, "file")]
    assert chunk_repository.calls == []
    assert embedder.calls == []
    assert vector_store.collection_calls == []


def test_index_project_requires_chunking_when_only_uploaded_assets_exist():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.UPLOADED.value,
        )
    ]

    (
        use_case,
        _asset_repository,
        chunk_repository,
        embedder,
        vector_store,
    ) = build_use_case(assets, {})

    result = asyncio.run(
        use_case.execute(IndexProjectCommand(project_id=10))
    )

    assert result.outcome == "needs_chunking"
    assert result.project_status_before_run == {
        "total_files": 1,
        "uploaded_files": 1,
        "chunked_files": 0,
        "indexed_files": 0,
    }

    assert chunk_repository.calls == []
    assert embedder.calls == []
    assert vector_store.collection_calls == []


def test_index_project_returns_collection_error_when_creation_fails():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.CHUNKED.value,
        )
    ]

    (
        use_case,
        asset_repository,
        chunk_repository,
        embedder,
        vector_store,
    ) = build_use_case(
        assets,
        {},
        collection_result=False,
    )

    result = asyncio.run(
        use_case.execute(IndexProjectCommand(project_id=10))
    )

    assert result.outcome == "collection_error"
    assert result.project_status_before_run == {
        "total_files": 1,
        "uploaded_files": 0,
        "chunked_files": 1,
        "indexed_files": 0,
    }

    assert vector_store.collection_calls == [(10, 3, False)]
    assert vector_store.delete_calls == []
    assert chunk_repository.calls == []
    assert embedder.calls == []
    assert asset_repository.status_updates == []


def test_index_project_reindexes_existing_assets_when_resetting():
    assets = [
        IndexableAsset(
            asset_id=20,
            asset_name="document.txt",
            asset_status=AssetStatus.INDEXED.value,
        )
    ]

    pages = {
        (20, 1): [make_chunk(1)],
    }

    (
        use_case,
        asset_repository,
        _chunk_repository,
        _embedder,
        vector_store,
    ) = build_use_case(
        assets,
        pages,
        embedding_result=EmbeddingResult(
            vectors=[[0.1, 0.2, 0.3]],
            success=True,
        ),
        insert_result=VectorInsertResult(success=1, failed=0),
    )

    result = asyncio.run(
        use_case.execute(
            IndexProjectCommand(
                project_id=10,
                do_reset=True,
            )
        )
    )

    assert result.outcome == "success"
    assert result.project_status_before_run == {
        "total_files": 1,
        "uploaded_files": 0,
        "chunked_files": 0,
        "indexed_files": 1,
    }
    assert result.call_status == {
        "file_success": 1,
        "file_failed": 0,
        "chunk_success": 1,
        "chunk_failed": 0,
    }

    assert vector_store.collection_calls == [(10, 3, True)]
    assert asset_repository.status_updates == [
        (20, AssetStatus.CHUNKED.value),
        (20, AssetStatus.INDEXED.value),
    ]
    assert vector_store.delete_calls == [(10, 20)]

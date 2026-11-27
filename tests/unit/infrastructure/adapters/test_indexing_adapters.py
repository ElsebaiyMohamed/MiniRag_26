
from types import SimpleNamespace

import pytest

from application.ports import (
    EmbeddingResult,
    IndexableAsset,
    IndexableChunk,
    VectorInsertResult,
)
from infrastructure.adapters.embedding_adapter import LLMEmbedder
from infrastructure.adapters.repositories import (
    SqlAlchemyAssetIndexRepository,
    SqlAlchemyChunkRepository,
)
from infrastructure.adapters.vector_store_adapter import (
    PgVectorStoreAdapter,
)
from models.enums import DocumentTypeEnum


@pytest.mark.asyncio
async def test_asset_index_repository_maps_assets(monkeypatch):
    assets = [
        SimpleNamespace(
            asset_id=10,
            asset_name="document.txt",
            asset_status=1,
        )
    ]

    async def fake_get_all_project_assets(
        asset_project_id,
        asset_type,
    ):
        assert asset_project_id == 5
        assert asset_type == "file"
        return assets

    monkeypatch.setattr(
        "infrastructure.adapters.repositories.AssetDataModel",
        lambda db_client: SimpleNamespace(
            get_all_project_assets=fake_get_all_project_assets,
        ),
    )

    repository = SqlAlchemyAssetIndexRepository(object())

    result = await repository.get_project_assets(5, "file")

    assert result == [
        IndexableAsset(
            asset_id=10,
            asset_name="document.txt",
            asset_status=1,
        )
    ]


@pytest.mark.asyncio
async def test_asset_index_repository_updates_status(monkeypatch):
    calls = []

    async def fake_set_asset_status(asset_id, status):
        calls.append((asset_id, status))

    monkeypatch.setattr(
        "infrastructure.adapters.repositories.AssetDataModel",
        lambda db_client: SimpleNamespace(
            set_asset_status=fake_set_asset_status,
        ),
    )

    repository = SqlAlchemyAssetIndexRepository(object())

    await repository.set_status(10, 2)

    assert calls == [(10, 2)]


@pytest.mark.asyncio
async def test_chunk_repository_maps_page_and_empty_metadata(monkeypatch):
    chunks = [
        SimpleNamespace(
            chunk_id=100,
            chunk_asset_id=10,
            chunk_text="First chunk",
            chunk_metadata={"source": "document.txt"},
        ),
        SimpleNamespace(
            chunk_id=101,
            chunk_asset_id=10,
            chunk_text="Second chunk",
            chunk_metadata=None,
        ),
    ]

    calls = []

    async def fake_get_project_asset_chunks(
        asset_id,
        page_no,
        page_size,
    ):
        calls.append((asset_id, page_no, page_size))
        return chunks

    monkeypatch.setattr(
        "infrastructure.adapters.repositories.ChunkDataModel",
        lambda db_client: SimpleNamespace(
            get_project_asset_chunks=fake_get_project_asset_chunks,
        ),
    )

    repository = SqlAlchemyChunkRepository(object())

    result = await repository.get_page(10, 2, 20)

    assert calls == [(10, 2, 20)]
    assert result == [
        IndexableChunk(
            chunk_id=100,
            asset_id=10,
            text="First chunk",
            metadata={"source": "document.txt"},
        ),
        IndexableChunk(
            chunk_id=101,
            asset_id=10,
            text="Second chunk",
            metadata={},
        ),
    ]


@pytest.mark.asyncio
async def test_llm_embedder_maps_successful_embedding_result():
    class FakeEmbeddingClient:
        embedding_size = 3

        def __init__(self):
            self.calls = []

        async def embed_text(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                content=[[0.1, 0.2, 0.3]],
                success=True,
                error_message=None,
            )

    client = FakeEmbeddingClient()
    embedder = LLMEmbedder(client)

    result = await embedder.embed(["test text"])

    assert result == EmbeddingResult(
        vectors=[[0.1, 0.2, 0.3]],
        success=True,
        error=None,
    )
    assert embedder.embedding_size == 3
    assert client.calls == [
        {
            "prompts": ["test text"],
            "document_type": DocumentTypeEnum.DOCUMENT.value,
        }
    ]


@pytest.mark.asyncio
async def test_llm_embedder_maps_provider_failure():
    class FakeEmbeddingClient:
        embedding_size = 3

        async def embed_text(self, **kwargs):
            return SimpleNamespace(
                content=None,
                success=False,
                error_message="Provider unavailable",
            )

    embedder = LLMEmbedder(FakeEmbeddingClient())

    result = await embedder.embed(["test text"])

    assert result == EmbeddingResult(
        vectors=[],
        success=False,
        error="Provider unavailable",
    )


@pytest.mark.asyncio
async def test_pgvector_adapter_creates_collection():
    class FakeVectorDB:
        def __init__(self):
            self.calls = []

        async def create_collection(self, **kwargs):
            self.calls.append(kwargs)
            return True

    client = FakeVectorDB()
    adapter = PgVectorStoreAdapter(client)

    result = await adapter.create_collection(
        project_id=5,
        embedding_size=768,
        do_reset=True,
    )

    assert result is True
    assert client.calls == [
        {
            "collection_name": "collection_5",
            "embedding_size": 768,
            "do_reset": True,
        }
    ]


@pytest.mark.asyncio
async def test_pgvector_adapter_deletes_asset_vectors():
    class FakeVectorDB:
        async def delete_embeddings_by_asset_id(self, **kwargs):
            self.calls = kwargs
            return 4

    client = FakeVectorDB()
    adapter = PgVectorStoreAdapter(client)

    result = await adapter.delete_asset_vectors(5, 10)

    assert result == 4
    assert client.calls == {
        "collection_name": "collection_5",
        "asset_id": 10,
    }


@pytest.mark.asyncio
async def test_pgvector_adapter_maps_insert_counts():
    class FakeVectorDB:
        def __init__(self):
            self.calls = []

        async def insert_many(self, **kwargs):
            self.calls.append(kwargs)
            return {"success": 8, "failed": 2}

    client = FakeVectorDB()
    adapter = PgVectorStoreAdapter(client)

    result = await adapter.insert_many(
        project_id=5,
        texts=["first", "second"],
        vectors=[[0.1, 0.2], [0.3, 0.4]],
        chunk_ids=[100, 101],
        asset_ids=[10, 10],
        metadatas=[{"page": 1}, {"page": 2}],
    )

    assert result == VectorInsertResult(success=8, failed=2)
    assert client.calls == [
        {
            "collection_name": "collection_5",
            "texts": ["first", "second"],
            "vectors": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"page": 1}, {"page": 2}],
            "record_ids": [100, 101],
            "asset_ids": [10, 10],
        }
    ]

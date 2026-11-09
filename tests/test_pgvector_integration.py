import os
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from models.db_schemas import Asset, DataChunk, Project
from stores.vectordb.providers.PgVector import PgVector


@pytest.mark.asyncio
async def test_pgvector_collection_insert_search_and_asset_delete(pgvector_session_factory):
    collection_name = f"issue30_{uuid4().hex[:12]}"

    async with pgvector_session_factory() as session:
        project = Project()
        session.add(project)
        await session.flush()
        asset_one = Asset(
            asset_project_id=project.project_id,
            asset_type="FILE",
            asset_name="one.txt",
            asset_size=1,
            asset_status=0,
        )
        asset_two = Asset(
            asset_project_id=project.project_id,
            asset_type="FILE",
            asset_name="two.txt",
            asset_size=1,
            asset_status=0,
        )
        session.add_all([asset_one, asset_two])
        await session.flush()
        chunks = [
            DataChunk(
                chunk_text="one",
                chunk_metadata={},
                chunk_order=1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_one.asset_id,
            ),
            DataChunk(
                chunk_text="two",
                chunk_metadata={},
                chunk_order=1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_two.asset_id,
            ),
        ]
        session.add_all(chunks)
        await session.commit()
        chunk_ids = [chunk.chunk_id for chunk in chunks]

    store = PgVector(
        db_client=pgvector_session_factory,
        default_vector_size=2,
        distance_method="cosine",
        index_threshold=2,
    )
    try:
        await store.connect()
        assert await store.create_collection(collection_name, embedding_size=2)
        assert await store.is_collection_existed(collection_name)
        assert store.get_pg_collection_name(collection_name) in await store.list_all_collections()
        assert await store.insert_many(
            collection_name=collection_name,
            texts=["nearest", "other asset"],
            vectors=[[1.0, 0.0], [0.0, 1.0]],
            metadatas=[{"source": "test"}, None],
            record_ids=chunk_ids,
            asset_ids=[asset_one.asset_id, asset_two.asset_id],
        ) == {"success": 2, "failed": 0}
        assert await store.is_index_existed(collection_name)
        collection_info = await store.get_collection_info(collection_name)
        assert collection_info["table_info"]["tablename"] == (
            store.get_pg_collection_name(collection_name)
        )
        assert collection_info["record_count"] == 2

        results = await store.search_by_vector(collection_name, [1.0, 0.0], limit=2)
        assert [result.text for result in results] == ["nearest", "other asset"]
        assert await store.delete_embeddings_by_asset_id(collection_name, asset_one.asset_id) == 1
        remaining = await store.search_by_vector(collection_name, [1.0, 0.0], limit=2)
        assert [result.text for result in remaining] == ["other asset"]
        assert await store.reset_vector_index(collection_name)
        assert await store.delete_collection(collection_name)
        assert not await store.is_collection_existed(collection_name)
    finally:
        await store.delete_collection(collection_name)
        await store.disconnect()


import pytest
from sqlalchemy import select, func

from application.ports import NewChunk
from infrastructure.adapters.repositories import (
    SqlAlchemyAssetProcessingRepository,
)
from models.db_schemas import Asset, DataChunk, Project
from models.enums.AssetTypeEnums import AssetStatus


@pytest.mark.asyncio
async def test_persist_chunks_and_update_asset_status_atomically(
    pgvector_session_factory,
):
    async with pgvector_session_factory() as session:
        session.add(Project(project_id=50))
        asset = Asset(
            asset_project_id=50,
            asset_type="file",
            asset_name="document.txt",
            asset_size=128,
            asset_status=AssetStatus.UPLOADED.value,
        )
        session.add(asset)
        await session.commit()
        asset_id = asset.asset_id

    repository = SqlAlchemyAssetProcessingRepository(
        pgvector_session_factory
    )

    chunks = [
        NewChunk(
            project_id=50,
            asset_id=asset_id,
            text="First chunk",
            order=0,
            metadata={"source": "document.txt"},
        ),
        NewChunk(
            project_id=50,
            asset_id=asset_id,
            text="Second chunk",
            order=1,
            metadata={"source": "document.txt"},
        ),
    ]

    result = await repository.persist(asset_id, chunks)

    assert result == 2

    async with pgvector_session_factory() as session:
        persisted_asset = await session.get(Asset, asset_id)

        persisted_chunks = (
            await session.scalars(
                select(DataChunk)
                .where(DataChunk.chunk_asset_id == asset_id)
                .order_by(DataChunk.chunk_order)
            )
        ).all()

    assert persisted_asset.asset_status == AssetStatus.CHUNKED.value

    assert len(persisted_chunks) == 2

    assert persisted_chunks[0].chunk_text == "First chunk"
    assert persisted_chunks[0].chunk_order == 0
    assert persisted_chunks[0].chunk_metadata == {
        "source": "document.txt"
    }

    assert persisted_chunks[1].chunk_text == "Second chunk"
    assert persisted_chunks[1].chunk_order == 1


@pytest.mark.asyncio
async def test_persist_returns_zero_when_asset_does_not_exist(
    pgvector_session_factory,
):
    async with pgvector_session_factory() as session:
        session.add(Project(project_id=51))
        await session.commit()

    repository = SqlAlchemyAssetProcessingRepository(
        pgvector_session_factory
    )

    chunks = [
        NewChunk(
            project_id=51,
            asset_id=999,
            text="Should not be inserted",
            order=0,
            metadata={},
        )
    ]

    result = await repository.persist(999, chunks)

    assert result == 0

    async with pgvector_session_factory() as session:
        chunk_count = await session.scalar(
            select(func.count())
            .select_from(DataChunk)
            .where(DataChunk.chunk_asset_id == 999)
        )

    assert chunk_count == 0


@pytest.mark.asyncio
async def test_persist_rolls_back_status_when_chunk_insertion_fails(
    pgvector_session_factory,
):
    async with pgvector_session_factory() as session:
        session.add(Project(project_id=52))
        asset = Asset(
            asset_project_id=52,
            asset_type="file",
            asset_name="rollback.txt",
            asset_size=128,
            asset_status=AssetStatus.UPLOADED.value,
        )
        session.add(asset)
        await session.commit()
        asset_id = asset.asset_id

    repository = SqlAlchemyAssetProcessingRepository(
        pgvector_session_factory
    )

    # NULL violates the database NOT NULL constraint on chunk_text.
    chunks = [
        NewChunk(
            project_id=52,
            asset_id=asset_id,
            text=None,
            order=0,
            metadata={},
        )
    ]

    result = await repository.persist(asset_id, chunks)

    assert result == 0

    async with pgvector_session_factory() as session:
        persisted_asset = await session.get(Asset, asset_id)

        chunk_count = await session.scalar(
            select(func.count())
            .select_from(DataChunk)
            .where(DataChunk.chunk_asset_id == asset_id)
        )

    # The status update must also have been rolled back.
    assert persisted_asset.asset_status == AssetStatus.UPLOADED.value
    assert chunk_count == 0

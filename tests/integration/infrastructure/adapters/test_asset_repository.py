
import uuid

import pytest
from sqlalchemy import select

from application.ports import AssetRecord, NewAsset
from infrastructure.adapters.repositories import SqlAlchemyAssetRepository
from models.db_schemas import Asset, Project


@pytest.mark.asyncio
async def test_create_asset_persists_asset_and_returns_record(
    pgvector_session_factory,
):
    async with pgvector_session_factory() as session:
        session.add(Project(project_id=50))
        await session.commit()

    repository = SqlAlchemyAssetRepository(pgvector_session_factory)

    new_asset = NewAsset(
        project_id=50,
        asset_type="file",
        asset_name="stored_document.txt",
        asset_size=128,
        asset_status=0,
    )

    result = await repository.create(new_asset)

    assert result == AssetRecord(asset_name="stored_document.txt")

    async with pgvector_session_factory() as session:
        asset = await session.scalar(
            select(Asset).where(Asset.asset_name == "stored_document.txt")
        )

        project = await session.get(Project, 50)

    assert asset is not None

    # Verify the repository persisted all supplied fields.
    assert asset.asset_project_id == 50
    assert asset.asset_type == "file"
    assert asset.asset_name == "stored_document.txt"
    assert asset.asset_size == 128
    assert asset.asset_status == 0

    # Verify generated and default fields.
    assert isinstance(asset.asset_uuid, uuid.UUID)
    assert asset.asset_config is None
    assert asset.asset_pushed_at is not None

    # Verify the asset references the expected existing project.
    assert project is not None
    assert asset.asset_project_id == project.project_id

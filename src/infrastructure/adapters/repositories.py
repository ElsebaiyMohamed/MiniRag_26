from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from application.errors import AssetAlreadyExists
from application.ports import (
    AssetRecord,
    AssetRepository,
    NewAsset,
    ProjectRepository,
    AssetProcessingRepository,
    NewChunk,
)
from models.AssetDataModel import AssetDataModel
from models.ProjectDataModel import ProjectDataModel
from models.db_schemas import Asset, DataChunk
from models.enums.AssetTypeEnums import AssetStatus


class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, db_client):
        self.model = ProjectDataModel(db_client)

    async def get_or_create(self, project_id: int) -> int:
        project = await self.model.get_project_or_create_one(
            project_id=project_id
        )
        return project.project_id


class SqlAlchemyAssetRepository(AssetRepository):
    def __init__(self, db_client):
        self.model = AssetDataModel(db_client)

    async def create(self, asset: NewAsset) -> AssetRecord:
        db_asset = Asset(
            asset_project_id=asset.project_id,
            asset_type=asset.asset_type,
            asset_name=asset.asset_name,
            asset_size=asset.asset_size,
            asset_status=asset.asset_status,
        )

        try:
            created_asset = await self.model.create_asset(db_asset)
        except IntegrityError as exc:
            original_error = exc.orig
            diagnostics = getattr(original_error, "diag", None)
            constraint_name = getattr(
                diagnostics,
                "constraint_name",
                None,
            )

            if constraint_name == "uq_assets_project_asset_name":
                raise AssetAlreadyExists from exc

            raise

        return AssetRecord(asset_name=created_asset.asset_name)

class SqlAlchemyAssetProcessingRepository(
    AssetProcessingRepository
):
    def __init__(self, db_client):
        self.db_client = db_client

    async def persist(
        self,
        asset_id: int,
        chunks: list[NewChunk],
    ) -> int:
        if not chunks:
            return 0
        if any(chunk.asset_id != asset_id for chunk in chunks):
            return 0
        try:
            async with self.db_client() as session:
                async with session.begin():
                    stmt = (
                        update(Asset)
                        .where(Asset.asset_id == asset_id)
                        .values(
                            asset_status=AssetStatus.CHUNKED.value
                        )
                    )

                    result = await session.execute(stmt)

                    if result.rowcount == 0:
                        return 0

                    db_chunks = [
                        DataChunk(
                            chunk_project_id=chunk.project_id,
                            chunk_asset_id=chunk.asset_id,
                            chunk_text=chunk.text,
                            chunk_order=chunk.order,
                            chunk_metadata=chunk.metadata,
                        )
                        for chunk in chunks
                    ]

                    session.add_all(db_chunks)
                    await session.flush()

                return len(db_chunks)

        except Exception:
            return 0

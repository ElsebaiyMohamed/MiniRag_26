
from application.ports import (
    AssetRecord,
    AssetRepository,
    NewAsset,
    ProjectRepository,
)

from models.AssetDataModel import AssetDataModel
from models.ProjectDataModel import ProjectDataModel
from models.db_schemas import Asset


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

        created_asset = await self.model.create_asset(db_asset)

        return AssetRecord(asset_name=created_asset.asset_name)

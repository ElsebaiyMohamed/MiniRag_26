from sqlalchemy import select, update

from .BaseDataModel import BaseDataModel
from .db_schemas import Asset


class AssetDataModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_asset(self, asset: Asset):
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)

        return asset


    async def get_asset_by_id(self, asset_id: int):
        async with self.db_client() as session:
                query = select(Asset).where(Asset.asset_id==asset_id)
                asset = (await session.execute(query)).scalar_one_or_none()
                return asset

    async def get_asset_by_name(self, asset_project_id: int, asset_name: str):
        async with self.db_client() as session:
                query = select(Asset).where(Asset.asset_project_id==asset_project_id,
                                            Asset.asset_name == asset_name)
                asset = (await session.execute(query)).scalar_one_or_none()
                return asset

    async def create_many_assets(self, assets: list, batch_size: int=100):
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(assets), batch_size):
                    session.add_all(assets[i:i+batch_size])
            await session.commit()

        return len(assets)

    async def get_all_project_assets(self, asset_project_id: int, asset_type: str,
                                    asset_status: int=None):
        async with (self.db_client() as session):
            if asset_status is None:
                stmt = select(Asset).where(
                    Asset.asset_project_id == asset_project_id,
                    Asset.asset_type == asset_type,
                )
            else:
                stmt = select(Asset).where(
                    Asset.asset_project_id == asset_project_id,
                                Asset.asset_type == asset_type,
                                Asset.asset_status==asset_status
                )
            result = await session.execute(stmt)
            records = result.scalars().all()
            return records

    async def set_asset_status(self, asset_id: int, status: int):
        async with self.db_client() as session:
            async with session.begin():
                stmt = update(Asset).where(Asset.asset_id == asset_id).values(asset_status=status)
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    return False
        return True

    async def delete_asset(self, asset_id: int) -> bool:
        async with self.db_client() as session:
            async with session.begin():
                query = select(Asset).where(Asset.asset_id == asset_id)
                asset = (await session.execute(query)).scalar_one_or_none()

                if not asset:
                    return False

                # Deleting via session.delete() fires the ORM cascade
                await session.delete(asset)
                return True

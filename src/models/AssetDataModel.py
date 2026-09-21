from bson.objectid import ObjectId
from pymongo import InsertOne

from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .enums import DataBaseEnum


class AssetDataModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]
        
    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        await instance.init_collection()
        return instance
    
    async def init_collection(self):
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_ASSET_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]
            indexes = Asset.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index['key'],
                    name=index['name'],
                    unique=index['unique']
                )    
    async def create_asset(self, asset: Asset):
        result = await self.collection.insert_one(asset.model_dump(by_alias=True, exclude_unset=True)) 
        asset.id = result.inserted_id
        return asset
    
    async def get_asset(self, asset_id: str):
        result = await self.collection.find_one({'_id': ObjectId(asset_id)})
        if result is None: 
            return None
        return Asset(**result)
        
        
    async def create_many_assets(self, assets: list, batch_size: int=100):
        for i in range(0, len(assets), batch_size):
            batch = assets[i:i+batch_size]
            
            operations = [InsertOne(asset.dict(by_alias=True, exclude_unset=True)) for asset in batch]
            await self.collection.bulk_write(operations)
            
        return len(assets)
    
    async def get_all_project_assets(self, asset_project_id: ObjectId, asset_type: str=None):
        return await self.collection.find(
            {
                'asset_project_id': ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id,
                'asset_type': asset_type
            }
        ).to_list(length=None)

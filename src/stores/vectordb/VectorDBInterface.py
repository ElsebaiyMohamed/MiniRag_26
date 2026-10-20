from abc import ABC, abstractmethod

class VectorDBInterface(ABC):

    @abstractmethod
    async def connect(self):
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    async def is_collection_existed(self, collection_name: str) -> bool:
        raise NotImplementedError
    @abstractmethod
    async def list_all_collections(self) -> list:
        raise NotImplementedError
    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> dict:
        raise NotImplementedError
    @abstractmethod
    async def delete_collection(self, collection_name: str) :
        raise NotImplementedError
    @abstractmethod
    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool=False) -> bool:
        raise NotImplementedError
    @abstractmethod
    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict=None, record_id: str=None, asset_id: int=None) :
        raise NotImplementedError
    @abstractmethod
    async def insert_many(self, collection_name: str, texts: list, vectors: list, metadatas: list=None,
                    record_ids: list=None, asset_ids: list=None, batch_size: int=50) :
        raise NotImplementedError
    @abstractmethod
    async def search_by_vector(self, collection_name: str, vector: list, limit: int=10) :
        raise NotImplementedError

    @abstractmethod
    async def delete_embeddings_by_asset_id(self, collection_name: str,
                                            asset_id: int) -> int:
        raise NotImplementedError

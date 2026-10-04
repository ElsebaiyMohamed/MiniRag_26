from abc import ABC, abstractmethod

class VectorDBInterface(ABC):
    
    @abstractmethod
    def connect(self):
        raise NotImplementedError
    
    @abstractmethod
    def disconnect(self):
        raise NotImplementedError
    
    @abstractmethod
    def is_collection_existed(self, collection_name: str) -> bool:
        raise NotImplementedError
    @abstractmethod
    def list_all_collections(self) -> list:
        raise NotImplementedError
    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict:
        raise NotImplementedError
    @abstractmethod
    def delete_collection(self, collection_name: str) :
        raise NotImplementedError
    @abstractmethod
    def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool=False) -> bool:
        raise NotImplementedError
    @abstractmethod
    def insert_one(self, collection_name: str, text: str, vector: list, metadata: dict=None, record_id: str=None) :
        raise NotImplementedError
    @abstractmethod
    def insert_many(self, collection_name: str, texts: list, vectors: list, metadatas: list=None, 
                    record_ids: list=None, batch_size: int=50) :
        raise NotImplementedError
    @abstractmethod
    def search_by_vector(self, collection_name: str, vector: list, limit: int=10) :
        raise NotImplementedError

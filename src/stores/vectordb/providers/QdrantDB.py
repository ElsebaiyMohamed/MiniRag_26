import logging

from qdrant_client import QdrantClient, models

from ..VectorDBInterface import VectorDBInterface
from models.enums import DistanceMethodEnums


class QdrantDB(VectorDBInterface):
    def __init__(self, db_path: str, distance_method: str) -> None:
        self.client: QdrantClient= None
        self.db_path = db_path
        
        if distance_method == DistanceMethodEnums.COSIENE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT
        else: 
            self.distance_method = None
            
        self.logger = logging.getLogger(__name__)
        
    def connect(self):
        self.client = QdrantClient(path=self.db_path)
    def disconnect(self):
        self.client = None
    def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)
    def list_all_coleections(self) -> list:
        return self.client.get_collections()
    def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)
    def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name=collection_name):
            self.client.delete_collection(collection_name=collection_name)
            return True
        return False
    def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False) -> bool:
        if do_reset:
            _ = self.delete_collection(collection_name=collection_name)
        
        if not self.is_collection_existed(collection_name=collection_name):
            self.client.create_collection(
                collection_name=collection_name, 
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method
                )
            )
            return True
        return False
    def insert_one(self, collection_name: str, text: str, vector: list, metadata: dict = None, record_id: str = None):
        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Can't insert new record to non existed collection {collection_name}")
            return False
        record = [
                models.Record(
                    vector=vector,
                    payload={
                        'text': text,
                        'metadata': metadata
                    }
                )
            ]
        _ = self._add_records(collection_name, record)
        return True
    def insert_many(self, collection_name: str, texts: list, vectors: list, metadatas: list = None,
                    record_ids: list = None, batch_size: int = 50):
        
        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Can't insert new record to non existed collection {collection_name}")
            return False
        if metadatas is None:
            metadatas = [None] *  len(vectors)
        for i in range(0, len(vectors), batch_size):
            batch_end = i + batch_size
            batch_text = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_records = [
                models.Record(
                                        vector=batch_vectors[j],
                                        payload={
                                            'text': batch_text[j],
                                            'metadata': batch_metadatas[j]
                                        }
                                    )
                for j in range(len(batch_text))
            ]
            _ = self._add_records(collection_name, batch_records)

    def _add_records(self, collection_name: str, records: models.Record):
        try:
            _ = self.cilent.upload_records(
                    collection_name=collection_name,
                    records=records
                )
            return True
        except Exception as e:
            self.logger.error(f"Error while inserting at collection {collection_name} \n {e}")
            return False

    def search_by_vector(self, collection_name: str, vector: list, limit: int=5) :
        return self.client.search(
            collection_name=collection_name,
            query_vector=vector, 
            limit=limit
            )

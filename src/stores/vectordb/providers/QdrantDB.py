import logging

from qdrant_client import QdrantClient, models

from ..VectorDBInterface import VectorDBInterface
from models.enums import DistanceMethodEnums
from models.schemas import RetrievedDocument

class QdrantDB(VectorDBInterface):
    def __init__(self, db_client, default_vector_size: int = 786, distance_method: str = None, index_threshold: int=None) -> None:
        self.client: QdrantClient= None
        self.db_client = db_client
        
        if distance_method == DistanceMethodEnums.COSIENE.value:
            self.distance_method = models.Distance.COSINE
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT
        else: 
            self.distance_method = None
            
        self.logger = logging.getLogger('uvicorn')
        
    async def connect(self):
        self.client = QdrantClient(path=self.db_client)
    async def disconnect(self):
        self.client = None
    async def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)
    async def list_all_collections(self) -> list:
        return self.client.get_collections()
    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)
    async def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name=collection_name):
            self.client.delete_collection(collection_name=collection_name)
            return True
        return False
    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False) -> bool:
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
    async def insert_one(self, collection_name: str, text: str, vector: list, metadata: dict = None, record_id: str = None):
        if not self.is_collection_existed(collection_name=collection_name):
            self.logger.error(f"Can't insert new record to non existed collection {collection_name}")
            return False
        record = [
                models.PointStruct(
                    id=record_id,
                    vector=vector,
                    payload={
                        'text': text,
                        'metadata': metadata
                    }
                )
            ]
        _ = await self._add_records(collection_name, record)
        return True
    async def insert_many(self, collection_name: str, texts: list, vectors: list, metadatas: list = None,
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
            batch_record_ids = record_ids[i:batch_end]
            batch_records = [
                models.PointStruct(
                    id=batch_record_ids[j],
                    vector=batch_vectors[j],
                    payload={
                        'text': batch_text[j],
                        'metadata': batch_metadatas[j]
                    }
                )
                for j in range(len(batch_text))
            ]
            _ = await self._add_records(collection_name, batch_records)

    async def _add_records(self, collection_name: str, records: models.PointStruct):
        try:
            _ = self.client.upload_points(
                    collection_name=collection_name,
                    points=records
                ) 
            return True
        except Exception as e:
            self.logger.error(f"Error while inserting at collection {collection_name} \n {e}")
            return False

    async def search_by_vector(self, collection_name: str, vector: list, limit: int=5) :
        results =  self.client.query_points(
                collection_name=collection_name,
                query=vector, 
                limit=limit
            )

        if not results or len(results.points) == 0:
            return None
        return [
            RetrievedDocument(**{
                'score': point.score,
                'text': point.payload['text']
            })
            for point in results.points
        ]

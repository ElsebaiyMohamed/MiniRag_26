from typing import List
import uuid

from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from models.enums import DocumentTypeEnum


class NLPController(BaseController):
    
    def __init__(self, vectordb_client, generation_client, embedding_client):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        
    def create_collection_name(self, project_id: str):
        return f'collection_{project_id}'.strip()
    
    def reset_vectordb_collection(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        return self.vectordb_client.delete_collection(collection_name)
    
    def get_vectordb_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        collection__info = self.vectordb_client.get_collection_info(collection_name)
        return collection__info
    
    def index2vectordb(self, project: Project, chunks: List[DataChunk], do_reset: bool=False):
        collection_name = self.create_collection_name(project.project_id)
        chunk_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, str(c.id))) for c in chunks]
        chunk_texts = [c.chunk_text for c in chunks]
        chunk_metadatas = [c.chunk_metadata for c in chunks]
        
        vectors = self.embedding_client.batch_embed_text(
                prompt=chunk_texts, 
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )

        
        self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )
        
        self.vectordb_client.insert_many(
            collection_name=collection_name, 
            texts=chunk_texts, 
            metadatas=chunk_metadatas, 
            vectors=vectors,
            record_ids=chunk_ids
        )
        return True

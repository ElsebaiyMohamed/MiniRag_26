from typing import List
import uuid

from .BaseController import BaseController
from models.db_schemas import Project, DataChunk
from models.enums import DocumentTypeEnum


class NLPController(BaseController):
    
    def __init__(self, vectordb_client, generation_client, embedding_client, template_parser=None):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        
    def create_collection_name(self, project_id: int):
        return f'collection_{project_id}'.strip()
    
    async def reset_vectordb_collection(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        return await self.vectordb_client.delete_collection(collection_name)
    
    async def get_vectordb_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        collection__info = await self.vectordb_client.get_collection_info(collection_name)
        return collection__info
    
    async def index2vectordb(self, project: Project, chunks: List[DataChunk], do_reset: bool=False):
        collection_name = self.create_collection_name(project.project_id)
        chunk_ids = [str(c.chunk_uuid) for c in chunks]
        chunk_texts = [c.chunk_text for c in chunks]
        chunk_metadatas = [c.chunk_metadata for c in chunks]
        
        vectors = self.embedding_client.batch_embed_text(
                prompt=chunk_texts, 
                document_type=DocumentTypeEnum.DOCUMENT.value,
            )

        
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )
        
        await self.vectordb_client.insert_many(
            collection_name=collection_name, 
            texts=chunk_texts, 
            metadatas=chunk_metadatas, 
            vectors=vectors,
            record_ids=chunk_ids
        )
        return True
    
    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):
        collection_name = self.create_collection_name(project.project_id)
        vector = self.embedding_client.embed_text(
                    collection_name=collection_name, 
                    prompt=text, 
                    document_type=DocumentTypeEnum.QUERY.value
                )
        if not vector or len(vector) == 0:
            return False
        
        result = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=vector,
            limit=limit
        )
        if not result: 
            return False
        
        return result

    async def answer_rag_question(self, project: Project, query: str, limit: int=10):
        retrieved_docs = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit
        )
        if not retrieved_docs or len(retrieved_docs) == 0:
            return None, None, None
        
        system_prompt = self.template_parser.get('rag', 'system_prompt')
        documents_prompts = [
                self.template_parser.get('rag', 'document_prompt', {
                        'doc_num': idx+1,
                        'chunk_text': doc.text
                    })
            for idx, doc in enumerate(retrieved_docs)
        ]
        
        documents_prompts = '\n\n'.join(documents_prompts)
        
        full_prompt = documents_prompts + self.template_parser.get('rag', 'footer_prompt', {
            'query': query
        })
        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enum.SYSTEM.value
            )
        ]
        
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )
        return answer, full_prompt, chat_history

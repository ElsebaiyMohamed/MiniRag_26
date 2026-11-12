from typing import List

from models.db_schemas import Project, DataChunk, Asset
from models.enums import DocumentTypeEnum
from .BaseController import BaseController


class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, embedding_client, template_parser=None):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser

    def create_collection_name(self, project_id: int):
        return f"collection_{project_id}".strip()

    async def reset_vectordb_collection(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        return await self.vectordb_client.delete_collection(collection_name)

    async def reset_vectordb_collection_asset_vectors(self, project: Project, asset: Asset):

        collection_name = self.create_collection_name(project.project_id)
        return await self.vectordb_client.delete_embeddings_by_asset_id(collection_name, asset.asset_id)

    async def get_vectordb_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project.project_id)
        collection__info = await self.vectordb_client.get_collection_info(collection_name)
        return collection__info

    async def index2vectordb(self, project: Project, chunks: List[DataChunk],
                             do_reset: bool = False):
        collection_name = self.create_collection_name(project.project_id)
        chunk_ids = [c.chunk_id for c in chunks]
        chunk_asset_ids = [c.chunk_asset_id for c in chunks]
        chunk_texts = [c.chunk_text for c in chunks]
        chunk_metadatas = [c.chunk_metadata for c in chunks]

        results = await self.embedding_client.embed_text(
            prompts=chunk_texts,
            document_type=DocumentTypeEnum.DOCUMENT.value,
        )

        # Handle embedding provider failure gracefully according to the contract
        if not results.success or not results.content:
            return {
                "success": 0,
                "failed": len(chunk_texts),
                "error": results.error_message or "Embedding generation failed",
            }

        is_created = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size, do_reset=do_reset
        )
        if not is_created:
            return {"success": 0, "failed": len(chunk_texts), "error": "Failed to create vector database collection"}

        insertion_status: dict = await self.vectordb_client.insert_many(
        collection_name=collection_name,
        texts=chunk_texts,
        metadatas=chunk_metadatas,
        vectors = results.content,
        record_ids=chunk_ids,
        asset_ids=chunk_asset_ids,
        )
        return insertion_status

    async def search_vector_db_collection(self, project: Project, text: str,
                                          limit: int = 10):
        collection_name = self.create_collection_name(project.project_id)
        embed_result = await self.embedding_client.embed_text(prompts=text, document_type=DocumentTypeEnum.QUERY.value)
        if not embed_result.success:
            return False, embed_result

        result = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector = embed_result.content,
            limit=limit
        )

        # Clear large raw vector data from telemetry object universally before returning
        embed_result.content = []

        if not result:
            return False, embed_result

        return result, embed_result

    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        retrieved_docs, query_embed_result = await self.search_vector_db_collection(
            project=project, text=query, limit=limit
        )

        # If search or embedding failed, return the failure status directly
        if query_embed_result and not query_embed_result.success:
            return None, query_embed_result, None, None, "Embedding generation failed during search"

        if not retrieved_docs or len(retrieved_docs) == 0:
            return None, query_embed_result, None, None, "No relevant documents found in vector database"

        system_prompt = self.template_parser.get("rag", "system_prompt")
        documents_prompts = [            self.template_parser.get("rag", "document_prompt", {"doc_num": idx + 1, "chunk_text": doc.text})for idx, doc in enumerate(retrieved_docs)
        ]

        documents_prompts = "\n\n".join(documents_prompts)
        full_prompt = documents_prompts + self.template_parser.get("rag", "footer_prompt", {"query": query})

        chat_history = [
            self.generation_client.construct_prompt(prompt=system_prompt,
                                                    role=self.generation_client.enum.SYSTEM.value)
        ]

        generation_result = await self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

        if not generation_result.success:
            return None, query_embed_result, full_prompt, chat_history, generation_result.error_message

        return generation_result, query_embed_result, full_prompt, chat_history, None

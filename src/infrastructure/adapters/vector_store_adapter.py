from application.ports import VectorInsertResult, VectorStore


class PgVectorStoreAdapter(VectorStore):
    """Adapter exposing the pgvector provider through the VectorStore port."""

    def __init__(self, vectordb_client):
        self.vectordb_client = vectordb_client

    @staticmethod
    def _collection_name(project_id: int) -> str:
        return f"collection_{project_id}"

    async def create_collection(
        self,
        project_id: int,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        return await self.vectordb_client.create_collection(
            collection_name=self._collection_name(project_id),
            embedding_size=embedding_size,
            do_reset=do_reset,
        )

    async def delete_asset_vectors(
        self,
        project_id: int,
        asset_id: int,
    ) -> int:
        return await self.vectordb_client.delete_embeddings_by_asset_id(
            collection_name=self._collection_name(project_id),
            asset_id=asset_id,
        )

    async def insert_many(
        self,
        project_id: int,
        texts: list[str],
        vectors: list[list[float]],
        chunk_ids: list[int],
        asset_ids: list[int],
        metadatas: list[dict],
    ) -> VectorInsertResult:
        result = await self.vectordb_client.insert_many(
            collection_name=self._collection_name(project_id),
            texts=texts,
            vectors=vectors,
            metadatas=metadatas,
            record_ids=chunk_ids,
            asset_ids=asset_ids,
        )

        return VectorInsertResult(
            success=int(result.get("success", 0)),
            failed=int(result.get("failed", 0)),
        )
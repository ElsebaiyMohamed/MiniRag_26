from application.ports import Embedder, EmbeddingResult
from models.enums import DocumentTypeEnum


class LLMEmbedder(Embedder):
    """Adapter between the application Embedder port and the LLM provider."""

    def __init__(self, embedding_client):
        self.embedding_client = embedding_client
        self.embedding_size = embedding_client.embedding_size

    async def embed(
        self,
        texts: list[str],
    ) -> EmbeddingResult:
        result = await self.embedding_client.embed_text(
            prompts=texts,
            document_type=DocumentTypeEnum.DOCUMENT.value,
        )

        content = result.content
        vectors = content if isinstance(content, list) else []

        success = bool(result.success) and isinstance(content, list)

        return EmbeddingResult(
            vectors=vectors,
            success=success,
            error=(
                getattr(result, "error_message", None)
                if not success
                else None
            ),
        )

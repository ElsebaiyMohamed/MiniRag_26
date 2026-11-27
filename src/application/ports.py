
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol


class UploadSource(Protocol):
    """Framework-independent interface for an uploaded file."""

    filename: str | None
    content_type: str | None
    size: int

    async def read(self, size: int = -1) -> bytes:
        ...

class LoadedDocumentInfo(Protocol):
    """Framework-independent loaded document representation."""

    text: str
    metadata: dict

class DocumentLoaderInfo(Protocol):
    """Metadata and loading interface exposed by a registered loader."""

    mime_types: tuple[str, ...]

    def load(self, path: Path) -> list[LoadedDocumentInfo]:
        ...


class LoaderResolver(Protocol):
    """Resolves a document loader from a file path."""

    def for_path(self, path: Path) -> DocumentLoaderInfo:
        ...


class FileStorage(Protocol):
    """Stores uploaded files and returns their stored filename."""

    async def store(
        self,
        project_id: int,
        original_filename: str,
        source: UploadSource,
        chunk_size: int,
    ) -> str:
        ...

    async def delete(
        self,
        project_id: int,
        stored_filename: str,
    ) -> None:
        ...


class ProjectRepository(Protocol):
    """Ensures that a project exists."""

    async def get_or_create(self, project_id: int) -> int:
        ...


@dataclass(frozen=True)
class NewAsset:
    project_id: int
    asset_type: str
    asset_name: str
    asset_size: int
    asset_status: int


@dataclass(frozen=True)
class AssetRecord:
    asset_name: str


class AssetRepository(Protocol):
    """Persists asset records."""

    async def create(self, asset: NewAsset) -> AssetRecord:
        ...

class AssetFileResolver(Protocol):
    """Resolves the physical path of a stored asset."""

    def resolve(self, project_id: int, asset_name: str) -> Path:
        ...


class ChunkInfo(Protocol):
    """Framework-independent chunk representation."""

    text: str
    order: int
    metadata: dict[str, Any]


class ChunkerInfo(Protocol):
    """Interface exposed by a configured chunker."""

    def chunk(
        self,
        documents: Iterable[LoadedDocumentInfo],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[ChunkInfo]:
        ...


class ChunkerResolver(Protocol):
    """Resolves a configured chunker."""

    def get_chunker(self, name: str) -> ChunkerInfo:
        ...


@dataclass(frozen=True)
class NewChunk:
    """Application-level representation of a chunk to persist."""

    project_id: int
    asset_id: int
    text: str
    order: int
    metadata: dict[str, Any]


class AssetProcessingRepository(Protocol):
    """Persists an asset's chunks and updates its processing status."""

    async def persist(
        self,
        asset_id: int,
        chunks: list[NewChunk],
    ) -> int:
        ...


@dataclass(frozen=True)
class IndexableAsset:
    """Framework-independent asset representation for indexing."""

    asset_id: int
    asset_name: str
    asset_status: int


@dataclass(frozen=True)
class IndexableChunk:
    """Framework-independent chunk representation for vector indexing."""

    chunk_id: int
    asset_id: int
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EmbeddingResult:
    """Application-level result returned by an embedding provider."""

    vectors: list[list[float]]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class VectorInsertResult:
    """Application-level result returned by a vector store insertion."""

    success: int
    failed: int


class AssetIndexRepository(Protocol):
    """Retrieves project assets and updates their indexing status."""

    async def get_project_assets(
        self,
        project_id: int,
        asset_type: str,
    ) -> list[IndexableAsset]:
        ...

    async def set_status(
        self,
        asset_id: int,
        status: int,
    ) -> None:
        ...


class ChunkRepository(Protocol):
    """Retrieves an asset's chunks in pages."""

    async def get_page(
        self,
        asset_id: int,
        page_no: int,
        page_size: int,
    ) -> list[IndexableChunk]:
        ...


class Embedder(Protocol):
    """Generates embeddings without exposing provider-specific result types."""

    embedding_size: int

    async def embed(
        self,
        texts: list[str],
    ) -> EmbeddingResult:
        ...


class VectorStore(Protocol):
    """Provides the vector operations required by project indexing."""

    async def create_collection(
        self,
        project_id: int,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        ...

    async def delete_asset_vectors(
        self,
        project_id: int,
        asset_id: int,
    ) -> int:
        ...

    async def insert_many(
        self,
        project_id: int,
        texts: list[str],
        vectors: list[list[float]],
        chunk_ids: list[int],
        asset_ids: list[int],
        metadatas: list[dict[str, Any]],
    ) -> VectorInsertResult:
        ...

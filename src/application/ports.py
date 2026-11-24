
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class UploadSource(Protocol):
    """Framework-independent interface for an uploaded file."""

    filename: str | None
    content_type: str | None
    size: int

    async def read(self, size: int = -1) -> bytes:
        ...


class DocumentLoaderInfo(Protocol):
    """Metadata exposed by a registered document loader."""

    mime_types: tuple[str, ...]


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

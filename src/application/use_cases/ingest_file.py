
from dataclasses import dataclass
from pathlib import Path

from application.errors import (
    AssetAlreadyExists,
    FileStorageError,
    UnsupportedUploadType,
    UploadTooLarge,
)
from application.ports import (
    AssetRepository,
    FileStorage,
    LoaderResolver,
    NewAsset,
    ProjectRepository,
    UploadSource,
)
from models.enums import AssetType, AssetStatus


@dataclass(frozen=True)
class IngestFileCommand:
    project_id: int
    file: UploadSource


@dataclass(frozen=True)
class IngestFileResult:
    file_id: str


class IngestFile:
    def __init__(
        self,
        loader_registry: LoaderResolver,
        file_storage: FileStorage,
        project_repository: ProjectRepository,
        asset_repository: AssetRepository,
        allowed_mime_types: set[str],
        max_size_bytes: int,
        chunk_size: int,
    ):
        self.loader_registry = loader_registry
        self.file_storage = file_storage
        self.project_repository = project_repository
        self.asset_repository = asset_repository
        self.allowed_mime_types = {
            mime.lower() for mime in allowed_mime_types
        }
        self.max_size_bytes = max_size_bytes
        self.chunk_size = chunk_size

    async def execute(self, command: IngestFileCommand) -> IngestFileResult:
        file = command.file
        filename = file.filename or ""

        loader = self.loader_registry.for_path(Path(filename))

        mime_type = (file.content_type or "").split(";")[0].strip().lower()
        loader_mime_types = {
            value.lower() for value in loader.mime_types
        }

        if (
            mime_type not in loader_mime_types
            or mime_type not in self.allowed_mime_types
        ):
            raise UnsupportedUploadType

        if file.size > self.max_size_bytes:
            raise UploadTooLarge

        project_id = await self.project_repository.get_or_create(
            command.project_id
        )

        try:
            stored_filename = await self.file_storage.store(
                project_id=project_id,
                original_filename=filename,
                source=file,
                chunk_size=self.chunk_size,
            )
        except Exception as exc:
            raise FileStorageError from exc

        try:
            asset = await self.asset_repository.create(
                NewAsset(
                    project_id=project_id,
                    asset_type=AssetType.FILE.value,
                    asset_name=stored_filename,
                    asset_size=file.size,
                    asset_status=AssetStatus.UPLOADED.value,
                )
            )
        except AssetAlreadyExists:
            try:
                await self.file_storage.delete(
                    project_id=project_id,
                    stored_filename=stored_filename,
                )
            except Exception:
                # Preserve the duplicate response even if cleanup fails.
                import logging

                logging.getLogger(__name__).exception(
                    "Failed to remove duplicate upload file: %s",
                    stored_filename,
                )

            raise

        return IngestFileResult(file_id=asset.asset_name)

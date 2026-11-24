import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from application.errors import UnsupportedUploadType
from application.ports import (
    AssetFileResolver,
    AssetProcessingRepository,
    ChunkerResolver,
    ChunkInfo,
    LoadedDocumentInfo,
    LoaderResolver,
    NewChunk,
)


@dataclass(frozen=True)
class ProcessAssetCommand:
    project_id: int
    asset_id: int
    asset_name: str
    chunker: str = "default"
    chunk_size: int = 100
    overlap_size: int = 20


@dataclass(frozen=True)
class ProcessAssetResult:
    success: bool
    chunk_count: int = 0


class ProcessAsset:
    def __init__(
        self,
        file_resolver: AssetFileResolver,
        loader_registry: LoaderResolver,
        chunker_factory: ChunkerResolver,
        processing_repository: AssetProcessingRepository,
    ):
        self.file_resolver = file_resolver
        self.loader_registry = loader_registry
        self.chunker_factory = chunker_factory
        self.processing_repository = processing_repository

    async def execute(
        self,
        command: ProcessAssetCommand,
    ) -> ProcessAssetResult:
        file_path = self.file_resolver.resolve(
            project_id=command.project_id,
            asset_name=command.asset_name,
        )

        chunks = await asyncio.to_thread(
            self._load_and_chunk,
            file_path,
            command.chunker,
            command.chunk_size,
            command.overlap_size,
        )

        if not chunks:
            return ProcessAssetResult(success=False)

        new_chunks = [
            NewChunk(
                project_id=command.project_id,
                asset_id=command.asset_id,
                text=chunk.text,
                order=chunk.order,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]

        persisted_count = await self.processing_repository.persist(
            asset_id=command.asset_id,
            chunks=new_chunks,
        )

        if persisted_count == 0:
            return ProcessAssetResult(success=False)

        return ProcessAssetResult(
            success=True,
            chunk_count=persisted_count,
        )

    def _load_and_chunk(
        self,
        file_path: Path,
        chunker_name: str,
        chunk_size: int,
        overlap_size: int,
    ) -> list[ChunkInfo] | None:
        if not file_path.is_file():
            return None

        try:
            loader = self.loader_registry.for_path(file_path)
        except UnsupportedUploadType:
            return None

        documents: list[LoadedDocumentInfo] = list(loader.load(file_path))

        if not documents:
            return None

        chunker = self.chunker_factory.get_chunker(
            name=chunker_name
        )

        return chunker.chunk(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
        )
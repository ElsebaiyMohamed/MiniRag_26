
from dataclasses import dataclass

from models.enums.AssetTypeEnums import AssetStatus, AssetType

from application.ports import (
    AssetIndexRepository,
    ChunkRepository,
    Embedder,
    VectorStore,
)


@dataclass(frozen=True)
class IndexProjectCommand:
    project_id: int
    do_reset: bool = False
    page_size: int = 10


@dataclass(frozen=True)
class IndexProjectResult:
    outcome: str
    project_status_before_run: dict[str, int]
    call_status: dict[str, int]


class IndexProject:
    """Indexes a project's chunked assets into a vector store."""

    def __init__(
        self,
        asset_repository: AssetIndexRepository,
        chunk_repository: ChunkRepository,
        embedder: Embedder,
        vector_store: VectorStore,
    ):
        self.asset_repository = asset_repository
        self.chunk_repository = chunk_repository
        self.embedder = embedder
        self.vector_store = vector_store

    async def execute(
        self,
        command: IndexProjectCommand,
    ) -> IndexProjectResult:
        assets = await self.asset_repository.get_project_assets(
            project_id=command.project_id,
            asset_type=AssetType.FILE.value,
        )

        call_status = {
            "file_success": 0,
            "file_failed": 0,
            "chunk_success": 0,
            "chunk_failed": 0,
        }

        if not assets:
            return IndexProjectResult(
                outcome="no_files",
                project_status_before_run={
                    "total_files": 0,
                    "uploaded_files": 0,
                    "chunked_files": 0,
                    "indexed_files": 0,
                },
                call_status=call_status,
            )

        project_status = {
            "total_files": len(assets),
            "uploaded_files": sum(
                asset.asset_status == AssetStatus.UPLOADED.value
                for asset in assets
            ),
            "chunked_files": sum(
                asset.asset_status == AssetStatus.CHUNKED.value
                for asset in assets
            ),
            "indexed_files": sum(
                asset.asset_status == AssetStatus.INDEXED.value
                for asset in assets
            ),
        }

        if command.do_reset:
            for asset in assets:
                if asset.asset_status == AssetStatus.INDEXED.value:
                    await self.asset_repository.set_status(
                        asset_id=asset.asset_id,
                        status=AssetStatus.CHUNKED.value,
                    )

            collection_created = await self.vector_store.create_collection(
                project_id=command.project_id,
                embedding_size=self.embedder.embedding_size,
                do_reset=True,
            )

            if not collection_created:
                return IndexProjectResult(
                    outcome="collection_error",
                    project_status_before_run=project_status,
                    call_status=call_status,
                )

            assets_to_index = [
                asset
                for asset in assets
                if asset.asset_status in (
                    AssetStatus.CHUNKED.value,
                    AssetStatus.INDEXED.value,
                )
            ]

            if not assets_to_index:
                outcome = (
                    "needs_chunking"
                    if project_status["uploaded_files"] > 0
                    else "nothing_to_index"
                )
                return IndexProjectResult(
                    outcome=outcome,
                    project_status_before_run=project_status,
                    call_status=call_status,
                )
        else:
            assets_to_index = [
                asset
                for asset in assets
                if asset.asset_status == AssetStatus.CHUNKED.value
            ]

            if not assets_to_index:
                outcome = (
                    "needs_chunking"
                    if project_status["uploaded_files"] > 0
                    else "nothing_to_index"
                )
                return IndexProjectResult(
                    outcome=outcome,
                    project_status_before_run=project_status,
                    call_status=call_status,
                )

            collection_created = await self.vector_store.create_collection(
                project_id=command.project_id,
                embedding_size=self.embedder.embedding_size,
                do_reset=False,
            )

            if not collection_created:
                return IndexProjectResult(
                    outcome="collection_error",
                    project_status_before_run=project_status,
                    call_status=call_status,
                )

        for asset in assets_to_index:
            page_no = 1
            asset_success = 0
            asset_failed = 0

            # Remove old vectors first, making retries safe.
            await self.vector_store.delete_asset_vectors(
                project_id=command.project_id,
                asset_id=asset.asset_id,
            )

            while True:
                chunks = await self.chunk_repository.get_page(
                    asset_id=asset.asset_id,
                    page_no=page_no,
                    page_size=command.page_size,
                )

                if not chunks:
                    break

                page_no += 1
                texts = [chunk.text for chunk in chunks]

                try:
                    embedding_result = await self.embedder.embed(texts)

                    if (
                        not embedding_result.success
                        or len(embedding_result.vectors) != len(chunks)
                    ):
                        asset_failed += len(chunks)
                        continue

                    insertion_result = await self.vector_store.insert_many(
                        project_id=command.project_id,
                        texts=texts,
                        vectors=embedding_result.vectors,
                        chunk_ids=[chunk.chunk_id for chunk in chunks],
                        asset_ids=[chunk.asset_id for chunk in chunks],
                        metadatas=[chunk.metadata for chunk in chunks],
                    )

                    asset_success += insertion_result.success
                    asset_failed += insertion_result.failed

                except Exception:
                    asset_failed += len(chunks)

            # An asset is indexed only when every chunk was inserted.
            if asset_failed > 0 or asset_success == 0:
                call_status["file_failed"] += 1
                call_status["chunk_failed"] += asset_success + asset_failed

                await self.vector_store.delete_asset_vectors(
                    project_id=command.project_id,
                    asset_id=asset.asset_id,
                )
            else:
                await self.asset_repository.set_status(
                    asset_id=asset.asset_id,
                    status=AssetStatus.INDEXED.value,
                )
                call_status["file_success"] += 1
                call_status["chunk_success"] += asset_success

        outcome = (
            "success"
            if call_status["file_success"] > 0
            else "failed"
        )

        return IndexProjectResult(
            outcome=outcome,
            project_status_before_run=project_status,
            call_status=call_status,
        )

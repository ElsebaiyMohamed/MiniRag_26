import asyncio
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse

from application.errors import (
    FileStorageError,
    UnsupportedUploadType,
    UploadTooLarge,
)
from application.use_cases.ingest_file import (
    IngestFile,
    IngestFileCommand,
)
from controllers import ProcessController
from helpers import Settings, get_settings
from infrastructure.adapters.file_storage import LocalFileStorage
from infrastructure.adapters.repositories import (
    SqlAlchemyAssetRepository,
    SqlAlchemyProjectRepository,
)
from models import ProjectDataModel, ChunkDataModel, AssetDataModel
from models.db_schemas import DataChunk
from models.enums import ResponseSignal, AssetType, AssetStatus
from models.schemas import ProcessRequest
from utils.metrics import DOCUMENT_PROCESSING_DURATION

log_it = logging.getLogger("uvicorn.error")

data_router = APIRouter(prefix="/api/v1/data", tags=["v1", "data"])


@data_router.post("/upload/{project_id}")
async def upload(
    request: Request,
    project_id: int,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
):
    use_case = IngestFile(
        loader_registry=request.app.loader_registry,
        file_storage=LocalFileStorage(
            base_dir=Path(__file__).resolve().parents[1]
        ),
        project_repository=SqlAlchemyProjectRepository(
            request.app.db_client
        ),
        asset_repository=SqlAlchemyAssetRepository(
            request.app.db_client
        ),
        allowed_mime_types=set(
            app_settings.FILE_ALLOWED_EXTENTIONS
        ),
        max_size_bytes=(
            app_settings.FILE_MAX_SIZE_IN_MB * 1024 * 1024
        ),
        chunk_size=app_settings.FILE_DEAFAULT_CHUNK_SIZE,
    )

    try:
        result = await use_case.execute(
            IngestFileCommand(
                project_id=project_id,
                file=file,
            )
        )

    except UnsupportedUploadType:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
            },
        )

    except UploadTooLarge:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_SIZE_EXCEEDED.value
            },
        )

    except FileStorageError as exc:
        log_it.error("Error while uploading file: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            "file_id": result.file_id,
        },
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest):
    processor_controller = ProcessController(
        project_id=project_id,
        loader_registry=request.app.loader_registry,
        chunker_factory=request.app.chunker_factory
    )
    project_model = await ProjectDataModel.create_instance(
        db_client=request.app.db_client
    )
    project = await project_model.get_project(project_id=project_id)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )
    chunk_model = await ChunkDataModel.create_instance(db_client=request.app.db_client)

    asset_model = await AssetDataModel.create_instance(db_client=request.app.db_client)
    all_project_files = await asset_model.get_all_project_assets(
        asset_project_id=project.project_id, asset_type=AssetType.FILE.value
    )
    total_project_files_num = len(all_project_files)
    if not total_project_files_num:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.NO_FILES_ERROR.value},
        )
    if process_request.do_reset:
        log_it.info("reset all chunks at project")
        for dummy_asset in all_project_files:
            await asset_model.set_asset_status(dummy_asset.asset_id,
                                            AssetStatus.UPLOADED.value)
            dummy_asset.asset_status = AssetStatus.UPLOADED.value
        no_deleted = await chunk_model.delete_chunks_by_project_id(
            project_id=project.project_id
        )

        project_files = all_project_files
    else:
        project_files = [asset for asset in all_project_files if asset.asset_status==AssetStatus.UPLOADED.value]

    if not project_files:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": ResponseSignal.FILES_ALREADY_PROCESSED.value,
                "total_no_files": total_project_files_num,
                "no_files_proceeds": 0,
                "no_files_success": 0,
                "no_records_added": 0,
                },
        )

    project_file_ids = {record.asset_id: record.asset_name for record in project_files}
    no_of_records = 0
    total_no_files = len(project_file_ids)
    failed_files = 0

    for asset_id, file_id in project_file_ids.items():
        file_type = os.path.splitext(file_id)[-1].lower().lstrip(".")
        if f".{file_type}" not in request.app.loader_registry.supported_extensions():
            file_type = "other"

        start_time = time.perf_counter()
        outcome = "failure"

        try:
            # Limit concurrent document-processing operations.
            async with request.app.processing_semaphore:

                # Loading and splitting happen entirely in a worker thread.
                file_chunks = await asyncio.to_thread(
                    processor_controller.process_file,
                    file_id=file_id,
                    chunker=process_request.chunker,
                    chunk_size=process_request.chunk_size,
                    overlap_size=process_request.overlap_size,
                )

            if not file_chunks:
                log_it.error(
                    f"SKIP: File Name: {file_id} could not be processed"
                )
                failed_files += 1
                continue

            # Database operations remain on the event-loop thread.
            file_chunks_record = [
                DataChunk(
                    chunk_text=chunk.text,
                    chunk_metadata=chunk.metadata,
                    chunk_order=chunk.order,
                    chunk_project_id=project.project_id,
                    chunk_asset_id=asset_id,
                )
                for chunk in file_chunks
            ]

            record_count = await chunk_model.create_many_chunks(
                chunks=file_chunks_record
            )

            if record_count == 0:
                failed_files += 1
                continue

            no_of_records += record_count

            await asset_model.set_asset_status(
                asset_id,
                AssetStatus.CHUNKED.value,
            )

            outcome = "success"

        finally:
            DOCUMENT_PROCESSING_DURATION.labels(
                file_type=file_type,
                outcome=outcome,
            ).observe(time.perf_counter() - start_time)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "total_no_files": total_project_files_num,
            "no_files_proceeds": total_no_files,
            "no_files_success": total_no_files - failed_files,
            "no_records_added": no_of_records,
        },
    )

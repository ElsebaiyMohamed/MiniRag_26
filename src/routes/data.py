import logging

import aiofiles
from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse

from helpers import Settings, get_settings
from controllers import DataController, ProjectController, ProcessController
from models.enums import ResponseSignal, AssetType
from models.schemas import ProcessRequest
from models import ProjectDataModel, ChunkDataModel, AssetDataModel 
from models.db_schemas import DataChunk, Asset


log_it = logging.getLogger('uvicorn.error')

data_router = APIRouter(prefix="/api/v1/data",
                        tags=["v1", "data"]
                        )

@data_router.post("/upload/{project_id}")
async def upload(request: Request, project_id: str, file: UploadFile, app_settings: Settings=Depends(get_settings)):
    data_contoller = DataController()
    is_valid, signal = data_contoller.validate(file)  

    if not is_valid:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={
                                "signal": signal
                            }
                            
                            )
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    project_dir_path = ProjectController().get_project_path(project_id=project_id)
    file_id = data_contoller.gen_uniqe_filename(file.filename, project_dir_path)
    file_path = data_contoller.join_path(project_dir_path, file_id)
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(app_settings.FILE_DEAFAULT_CHINK_SIZE):
                await f.write(chunk)
    except Exception as e:
        log_it.error(f'Error while uploading file: \n {e}')
        return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    'signal': ResponseSignal.FILE_UPLOAD_FIALED.value
                }
                )

    asset_model = await AssetDataModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.id,
        asset_type=AssetType.FILE.value,
        asset_name=file_id,
        asset_size= file.size
    )
    asset_record = await asset_model.create_asset(asset_resource)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'signal': ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            'file_id': str(asset_record.id)
        } 
    )

@data_router.post('/process/{project_id}')
async def process_endpoint(request: Request, project_id: str, process_request: ProcessRequest):
    
    processor_controller = ProcessController(project_id=project_id)
    project_model = await ProjectDataModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    chunk_model = await ChunkDataModel.create_instance(db_client=request.app.db_client)

    

    asset_model = await AssetDataModel.create_instance(db_client=request.app.db_client)

    project_files = await asset_model.get_all_project_assets(
        asset_project_id=project.id,
        asset_type=AssetType.FILE.value
    )
    project_file_ids = {
        record.id: record.asset_name for record in project_files
    }
    
    if not project_file_ids:
        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                'signal': ResponseSignal.NO_FILES_ERROR.value
                            } 
                        )
    if process_request.do_reset: 
        no_deleted = await chunk_model.delete_chunks_by_project_id(project_id=project.id)
        
    no_of_records = 0
    total_no_files = len(project_file_ids)
    faild_files = 0
    for asset_id, file_id in project_file_ids.items():
        file_content = processor_controller.get_file_content(file_id)
        if file_content is None:
            log_it.error(f'SKIP: File Name: {file_id} not exist')
            faild_files += 1
            continue
        
        file_chunks = processor_controller.process_file_content(file_content=file_content,
                                                                chunk_size=process_request.chunk_size, 
                                                                overlap_size=process_request.overlap_size)
        
        if file_chunks is None or not file_chunks:
            return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            'file_id': file_id,
                            'signal': ResponseSignal.PROCESSING_FIALD.values
                        } 
                    )
        file_chunks_record = [DataChunk(
                                    chunk_text=chunk.page_content,
                                    chunk_metadata=chunk.metadata,
                                    chunk_order= i+1,
                                    chunk_project_id=project.id,
                                    chunk_asset_id=asset_id    
                                ) 
                                for i, chunk in enumerate(file_chunks)
                            ]
        
        
        no_of_records += await chunk_model.create_many_chunks(chunks=file_chunks_record)
        
    
    
    
    
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={ 
                'signal': ResponseSignal.PROCESSING_SUCCESS.value, 
                'no_files': total_no_files,
                'no_files_success': total_no_files - faild_files,
                'no_records': no_of_records
            } 
        )

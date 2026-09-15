import logging

import aiofiles
from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse

from helpers import Settings, get_settings
from controllers import DataController, ProjectController
from models import ResponseSignal

log_it = logging.getLogger('uvicorn.error')

data_router = APIRouter(prefix="/api/v1/data",
                        tags=["v1", "data"]
                        )

@data_router.post("/upload/{project_id}")
async def upload(project_id: str, file: UploadFile, app_settings: Settings=Depends(get_settings)):
    
    data_contoller = DataController()
    is_valid, signal = data_contoller.validate(file)  

    if not is_valid:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={
                                "signal": signal
                            }
                            
                            )
    
    project_dir_path = ProjectController().get_project_path(project_id=project_id)
    cleaned_filename = data_contoller.gen_uniqe_filename(file.filename, project_dir_path)
    cleaned_filename = data_contoller.join_path(project_dir_path, cleaned_filename)
    try:
        async with aiofiles.open(cleaned_filename, 'wb') as f:
            while chunk := await file.read(app_settings.FILE_DEAFAULT_CHINK_SIZE):
                await f.write(chunk)
    except Exception as e:
        log_it.erorr(f'Error while uploading file: \n {e}')
        return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    'signal': ResponseSignal.FILE_UPLOAD_FIALED.value
                }
                )
        
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'signal': ResponseSignal.FILE_UPLOAD_SUCCESS.value,
            'file_id': cleaned_filename
        } 
    )

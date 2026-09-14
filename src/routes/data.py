import os
import aiofiles

from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse

from helpers import Settings, get_settings
from controllers import DataController, ProjectController
from models import ResponseSignal

data_router = APIRouter(prefix="/api/v1/data",
                        tags=["v1", "data"]
                        )

@data_router.post("/upload/{project_id}")
async def upload(project_id: str, file: UploadFile, app_settings: Settings=Depends(get_settings)):
    
    is_valid, signal = DataController().validate(file)  

    if not is_valid:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                            content={
                                "signal": signal
                            }
                            
                            )
    
    project_dir_path = ProjectController().get_project_path(project_id=project_id)
    file_path = os.path.join(project_dir_path, file.filename)
    async with aiofiles.open(file_path, 'wb') as f:
        while chunk := await file.read(app_settings.FILE_DEAFAULT_CHINK_SIZE):
            await f.write(chunk)
            
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'signal': ResponseSignal.FILE_UPLOAD_SUCCESS.value
        } 
    )

from fastapi import FastAPI, APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse

from helpers import Settings, get_settings
from controllers import DataController, ProjectController

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
    
    
    
    
    # if is_valid:
    #     return JSONResponse(status_code=status.HTTP_200_OK, 
    #                         content={
    #                                 "signal": signal
    #                             }
                                
    #                             )
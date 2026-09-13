from fastapi import FastAPI, APIRouter, Depends, UploadFile
from helpers import Settings, get_settings


data_router = APIRouter(prefix="/api/v1/data",
                        tags=["v1", "data"]
                        )

@data_router.post("/upload/{project_id}")
async def upload(project_id: str, file: UploadFile, app_settings: Settings=Depends(get_settings)):
    pass

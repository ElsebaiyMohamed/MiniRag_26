from fastapi import FastAPI, APIRouter, Depends
from helpers import Settings, get_settings


base_router = APIRouter(prefix="/api/v1",
                        tags=["v1"]
                        )

@base_router.get("/")
async def read_root(app_settings: Settings=Depends(get_settings)):

    return {'app_name': app_settings.APP_NAME, 
            'version': app_settings.APP_VERSION, 
            'description': app_settings.APP_DESCRIPTION
            }
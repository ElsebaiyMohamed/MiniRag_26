from fastapi import FastAPI, APIRouter
import os

base_router = APIRouter(prefix="/api/v1",
                        tags=["v1"]
                        )

@base_router.get("/")
async def read_root():
    APP_NAME = os.getenv("APP_NAME", "MiniRag_26")
    APP_VERSION = os.getenv("APP_VERSION", "0.1")
    DESCRIPTION = os.getenv("APP_DESCRIPTION", "Question Answering System")
    
    return {'app_name': APP_NAME, 
            'version': APP_VERSION, 
            'description': DESCRIPTION
            }
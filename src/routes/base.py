from fastapi import APIRouter, Depends

from __version__ import __version__
from helpers import Settings, get_settings

base_router = APIRouter(tags=["v1"])


@base_router.get("/")
async def read_root(app_settings: Settings = Depends(get_settings)):
    return {
        "app_name": app_settings.APP_NAME,
        "version": __version__,
        "description": app_settings.APP_DESCRIPTION,
    }


@base_router.get("/version")
async def read_version():
    return {
        "version": __version__,
    }
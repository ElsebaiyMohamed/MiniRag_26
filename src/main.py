from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from routes import base, data
from helpers import get_settings

app = FastAPI(title="MiniRag_26", version="0.1", description="Question Answering System")

@app.on_event('startup')
async def start_db_client():
    settings = get_settings()
    
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

@app.on_event('shutdown')

async def shutdown_db_client():
    app.mongo_conn.close()

app.include_router(base.base_router)
app.include_router(data.data_router)



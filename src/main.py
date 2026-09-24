from contextlib import asynccontextmanager

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from routes import base, data
from helpers import get_settings
from stores.llm import LLMProviderFactory

    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    settings = get_settings()
    
    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    llm_factory = LLMProviderFactory(settings)
    app.generation_client = llm_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    app.embedding_client = llm_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID, embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    yield  # The application runs while paused here
    
    # --- SHUTDOWN LOGIC ---
    app.mongo_conn.close()

app = FastAPI(
    title="MiniRag_26", 
    version="0.1", 
    description="Question Answering System",
    lifespan=lifespan
)


app.include_router(base.base_router)
app.include_router(data.data_router)



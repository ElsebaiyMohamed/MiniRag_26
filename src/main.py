from contextlib import asynccontextmanager

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from routes import base, data, nlp
from helpers import get_settings
from models.enums import AppDataBase
from stores.llm import LLMProviderFactory
from stores.vectordb import VectorDBProviderFactory
from stores.llm.templates import TemplateParser
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    settings = get_settings()
    app.template_parser = TemplateParser(language=settings.PRIMARY_LANG, default_language=settings.DEFAULT_LANG)
    
    if settings.MAIN_DATABASE == AppDataBase.MONGO.value:
        app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
        app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]
    elif settings.MAIN_DATABASE == AppDataBase.POSTGRES.value:
        postgres_conn = f'postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}'
        app.db_engine = create_async_engine(postgres_conn)
        app.db_client = sessionmaker(
            bind=app.db_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    else:
        app.db_client = None
        
    
    llm_factory = LLMProviderFactory(settings)
    app.generation_client = llm_factory.create(provider=settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
    app.embedding_client = llm_factory.create(provider=settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id=settings.EMBEDDING_MODEL_ID, embedding_size=settings.EMBEDDING_MODEL_SIZE)
    
    vectordb_provider_factory = VectorDBProviderFactory(settings)
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTORDB_BACKEND
    )
    app.vectordb_client.connect()
    yield  # The application runs while paused here
    
    # --- SHUTDOWN LOGIC ---
    if settings.MAIN_DATABASE == AppDataBase.MONGO.value:
        app.mongo_conn.close()
    elif settings.MAIN_DATABASE == AppDataBase.POSTGRES.value:
        app.db_engine.dispose()
    else:
        pass
    app.vectordb_client.disconnect()
    

app = FastAPI(
    title="MiniRag_26", 
    version="0.1", 
    description="Question Answering System",
    lifespan=lifespan
)


app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)



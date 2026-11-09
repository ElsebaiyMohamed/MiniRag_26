import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import main


class FakeLLMFactory:
    def __init__(self, settings):
        self.settings = settings
        self.generation_client = SimpleNamespace(set_generation_model=Mock())
        self.embedding_client = SimpleNamespace(set_embedding_model=Mock())
        self.created = []

    def create(self, provider):
        self.created.append(provider)
        return self.generation_client if len(self.created) == 1 else self.embedding_client


class FakeVectorDBFactory:
    def __init__(self, settings, db_client):
        self.settings = settings
        self.db_client = db_client
        self.client = SimpleNamespace(connect=AsyncMock(), disconnect=AsyncMock())

    def create(self, provider):
        return self.client


@pytest.mark.asyncio
async def test_application_lifespan_configures_and_closes_clients(monkeypatch):
    settings = SimpleNamespace(
        PRIMARY_LANG="en",
        DEFAULT_LANG="en",
        POSTGRES_USERNAME="user",
        POSTGRES_PASSWORD="password",
        POSTGRES_HOST="db",
        POSTGRES_PORT=5432,
        POSTGRES_MAIN_DATABASE="rag",
        GENERATION_BACKEND="OPENAI",
        GENERATION_MODEL_ID="generation-model",
        EMBEDDING_BACKEND="COHERE",
        EMBEDDING_MODEL_ID="embedding-model",
        EMBEDDING_MODEL_SIZE=3,
        VECTORDB_BACKEND="PGVECTOR",
    )
    engine = SimpleNamespace(dispose=AsyncMock())
    session_factory = object()
    llm_factory = FakeLLMFactory(settings)
    vector_factory = FakeVectorDBFactory(settings, session_factory)
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "create_async_engine", Mock(return_value=engine))
    monkeypatch.setattr(main, "sessionmaker", Mock(return_value=session_factory))
    monkeypatch.setattr(main, "LLMProviderFactory", lambda config: llm_factory)
    monkeypatch.setattr(main, "VectorDBProviderFactory", lambda config, db_client: vector_factory)

    app = FastAPI()
    async with main.lifespan(app):
        assert app.db_client is session_factory
        assert app.generation_client is llm_factory.generation_client
        assert app.embedding_client is llm_factory.embedding_client
        assert app.vectordb_client is vector_factory.client
        vector_factory.client.connect.assert_awaited_once()

    vector_factory.client.disconnect.assert_awaited_once()
    engine.dispose.assert_awaited_once()
    llm_factory.generation_client.set_generation_model.assert_called_once_with(
        model_id="generation-model"
    )
    llm_factory.embedding_client.set_embedding_model.assert_called_once_with(
        model_id="embedding-model", embedding_size=3
    )

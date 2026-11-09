import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from controllers.BaseController import BaseController
from models.enums import LLMEnum, VectorDBEnums
from stores.llm import LLMProviderFactory
from stores.vectordb import VectorDBProviderFactory


@pytest.fixture
def settings():
    return SimpleNamespace(
        OPENAI_API_KEY="openai-key",
        OPENAI_API_URL="https://openai.example",
        COHERE_API_KEY="cohere-key",
        INPUT_DEFAULT_MAX_CHAR=100,
        DEAFAULT_MAX_OUTPUT_TOKENS=200,
        GENERATION_DEFAULT_TEMPERATURE=0.25,
        VECTOR_DB_DISTANCE_METRIC="cosine",
        EMBEDDING_MODEL_SIZE=3,
        VECTOR_DB_PGVEC_INDEX_THRESHOLD=10,
    )


def test_llm_factory_creates_each_supported_provider(monkeypatch, settings):
    module = importlib.import_module("stores.llm.LLMProviderFactory")
    openai_instance = object()
    cohere_instance = object()
    openai_provider = Mock(return_value=openai_instance)
    cohere_provider = Mock(return_value=cohere_instance)
    monkeypatch.setattr(module, "OpenAiProvider", openai_provider)
    monkeypatch.setattr(module, "CohereProvider", cohere_provider)
    factory = LLMProviderFactory(settings)

    assert factory.create(LLMEnum.OPENAI.value) is openai_instance
    openai_provider.assert_called_once_with(
        api_key="openai-key",
        api_url="https://openai.example",
        default_max_char=100,
        default_output_max_tokens=200,
        default_generation_temperature=0.25,
    )
    assert factory.create(LLMEnum.COHERE.value) is cohere_instance
    cohere_provider.assert_called_once()


def test_llm_factory_rejects_unknown_provider(settings):
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMProviderFactory(settings).create("UNKNOWN")


def test_vectordb_factory_creates_pgvector_and_rejects_unknown(monkeypatch, settings):
    module = importlib.import_module("stores.vectordb.VectorDBProviderFactory")
    monkeypatch.setattr(BaseController, "__init__", lambda self: None)
    provider = object()
    pgvector = Mock(return_value=provider)
    monkeypatch.setattr(module, "PgVector", pgvector)
    db_client = object()
    factory = VectorDBProviderFactory(settings, db_client=db_client)

    assert factory.create(VectorDBEnums.PGVECTOR.value) is provider
    pgvector.assert_called_once_with(
        db_client=db_client,
        distance_method="cosine",
        default_vector_size=3,
        index_threshold=10,
    )
    with pytest.raises(ValueError, match="Unsupported VectorDB provider"):
        factory.create("UNKNOWN")

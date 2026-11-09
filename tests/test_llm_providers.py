import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from models.enums import CohereEnum, DocumentTypeEnum, OpenAIEnum
from stores.llm.providers.CohereProvider import CohereProvider
from stores.llm.providers.OpenAiProvider import OpenAiProvider


@pytest.fixture
def openai_provider():
    provider = OpenAiProvider(api_key="test-key")
    provider.set_generation_model("test-generation")
    provider.set_embedding_model("test-embedding", embedding_size=2)
    return provider


@pytest.fixture
def cohere_provider():
    provider = CohereProvider(api_key="test-key")
    provider.set_generation_model("test-generation")
    provider.set_embedding_model("test-embedding", embedding_size=2)
    return provider


@pytest.mark.asyncio
async def test_openai_generate_text_sends_history_and_returns_content(openai_provider):
    create = AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))]
    ))
    openai_provider.client.chat.completions.create = create
    history = [{"role": "system", "content": "instructions"}]

    result = await openai_provider.generate_text(
        "question", chat_history=history, max_output_tokens=20, temperature=0.4
    )

    assert result == "answer"
    kwargs = create.await_args.kwargs
    assert kwargs["model"] == "test-generation"
    assert kwargs["messages"] == [
        *history,
        {"role": OpenAIEnum.USER.value, "content": "question"},
    ]
    assert kwargs["max_tokens"] == 20
    assert kwargs["temperature"] == 0.4
    assert history == [{"role": "system", "content": "instructions"}]


@pytest.mark.asyncio
async def test_openai_embedding_handles_single_and_multiple_inputs(openai_provider):
    create = AsyncMock(return_value=SimpleNamespace(data=[
        SimpleNamespace(embedding=[1.0, 0.0]),
        SimpleNamespace(embedding=[0.0, 1.0]),
    ]))
    openai_provider.client.embeddings.create = create

    single = await openai_provider.embed_text("one")
    multiple = await openai_provider.embed_text(["one", "two"])

    assert single == [1.0, 0.0]
    assert multiple == [[1.0, 0.0], [0.0, 1.0]]
    assert create.await_count == 2
    assert create.await_args.kwargs["model"] == "test-embedding"


@pytest.mark.asyncio
async def test_openai_embedding_provider_failure_returns_none(openai_provider):
    openai_provider.client.embeddings.create = AsyncMock(side_effect=RuntimeError("offline"))

    assert await openai_provider.embed_text("one") is None


@pytest.mark.asyncio
async def test_openai_missing_model_returns_none(openai_provider):
    openai_provider.generation_model_id = None
    openai_provider.embedding_model_id = None

    assert await openai_provider.generate_text("question") is None
    assert await openai_provider.embed_text("question") is None


@pytest.mark.asyncio
async def test_cohere_generate_text_sends_history_and_returns_content(cohere_provider):
    chat = AsyncMock(return_value=SimpleNamespace(
        message=SimpleNamespace(content=[SimpleNamespace(text="answer")])
    ))
    cohere_provider.client.chat = chat
    history = [{"role": "system", "content": "instructions"}]

    result = await cohere_provider.generate_text(
        "question", chat_history=history, max_output_tokens=30, temperature=0.2
    )

    assert result == "answer"
    kwargs = chat.await_args.kwargs
    assert kwargs["model"] == "test-generation"
    assert kwargs["messages"] == [
        *history,
        {"role": CohereEnum.USER.value, "content": "question"},
    ]
    assert kwargs["max_tokens"] == 30
    assert kwargs["temperature"] == 0.2
    assert history == [{"role": "system", "content": "instructions"}]


@pytest.mark.asyncio
async def test_cohere_embedding_selects_query_and_document_input_types(cohere_provider):
    embed = AsyncMock(return_value=SimpleNamespace(
        embeddings=SimpleNamespace(float=[[1.0, 0.0], [0.0, 1.0]])
    ))
    cohere_provider.client.embed = embed

    single = await cohere_provider.embed_text("query", DocumentTypeEnum.QUERY.value)
    multiple = await cohere_provider.embed_text(["one", "two"])

    assert single == [1.0, 0.0]
    assert multiple == [[1.0, 0.0], [0.0, 1.0]]
    assert embed.await_args_list[0].kwargs["input_type"] == CohereEnum.QUERY.value
    assert embed.await_args_list[1].kwargs["input_type"] == CohereEnum.DOCUMENT.value
    assert embed.await_args_list[0].kwargs["embedding_types"] == ["float"]


@pytest.mark.asyncio
async def test_cohere_missing_models_and_empty_responses_return_none(cohere_provider):
    cohere_provider.generation_model_id = None
    cohere_provider.embedding_model_id = None
    assert await cohere_provider.generate_text("question") is None
    assert await cohere_provider.embed_text("question") is None

    cohere_provider.set_generation_model("test-generation")
    cohere_provider.set_embedding_model("test-embedding", embedding_size=2)
    cohere_provider.client.chat = AsyncMock(return_value=SimpleNamespace(message=None))
    cohere_provider.client.embed = AsyncMock(return_value=SimpleNamespace(embeddings=None))

    assert await cohere_provider.generate_text("question") is None
    assert await cohere_provider.embed_text("question") is None

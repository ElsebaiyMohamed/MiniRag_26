import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from helpers import get_settings
from models.enums import LLMEnum
from models.schemas import LLMResult
from stores.llm.LLMProviderFactory import LLMProviderFactory


@pytest.fixture
def app_settings(monkeypatch):
    """Mocks required configuration settings for testing."""
    settings = get_settings()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(settings, "OPENAI_API_URL", "https://openai.example")
    monkeypatch.setattr(settings, "COHERE_API_KEY", "test-cohere-key")
    monkeypatch.setattr(settings, "INPUT_DEFAULT_MAX_CHAR", 1000)
    monkeypatch.setattr(settings, "DEAFAULT_MAX_OUTPUT_TOKENS", 100)
    monkeypatch.setattr(settings, "GENERATION_DEFAULT_TEMPERATURE", 0.1)
    monkeypatch.setattr(settings, "LLM_REQUEST_TIMEOUT_SEC", 5.0)
    return settings


@pytest.fixture
def llm_factory(app_settings):
    return LLMProviderFactory(app_settings)


# ==========================================
# COHERE PROVIDER PUBLIC METHOD TESTS
# ==========================================

@pytest.mark.asyncio
async def test_cohere_generate_text_contract(llm_factory):
    provider = llm_factory.create(LLMEnum.COHERE.value)
    provider.set_generation_model("command-r-plus")

    mock_sdk_response = MagicMock()
    mock_sdk_response.message.content = [{"text": "Cohere test response."}]
    mock_sdk_response.usage.tokens.input_tokens = 10
    mock_sdk_response.usage.tokens.output_tokens = 5

    with patch.object(provider.client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_sdk_response

        # Test public method call
        result = await provider.generate_text("Test prompt")

        assert isinstance(result, LLMResult)
        assert result.success is True
        assert isinstance(result.content, str)
        assert result.provider == "cohere"
        assert result.model == "command-r-plus"
        assert result.operation == "generate_text"
        assert isinstance(result.latency_ms, float)
        assert isinstance(result.total_tokens, int)


@pytest.mark.asyncio
async def test_cohere_embed_text_contract(llm_factory):
    expected_dim = 3
    provider = llm_factory.create(LLMEnum.COHERE.value)
    provider.set_embedding_model("embed-english-v3.0", embedding_size=expected_dim)

    mock_sdk_response = MagicMock()
    mock_sdk_response.embeddings.float = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_sdk_response.usage.tokens.input_tokens = 6

    with patch.object(provider.client, "embed", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = mock_sdk_response

        # Test single string input public method call
        single_result = await provider.embed_text("single prompt")
        assert isinstance(single_result, LLMResult)
        assert single_result.success is True
        assert isinstance(single_result.content, list)
        assert len(single_result.content) == expected_dim

        # Test batch list input public method call
        batch_result = await provider.embed_text(["prompt one", "prompt two"])
        assert isinstance(batch_result, LLMResult)
        assert batch_result.success is True
        assert isinstance(batch_result.content, list)
        assert len(batch_result.content) == 2


# ==========================================
# OPENAI PROVIDER PUBLIC METHOD TESTS
# ==========================================

@pytest.mark.asyncio
async def test_openai_generate_text_contract(llm_factory):
    provider = llm_factory.create(LLMEnum.OPENAI.value)
    provider.set_generation_model("gpt-4o")

    mock_sdk_response = MagicMock()
    mock_sdk_response.choices = [MagicMock()]
    mock_sdk_response.choices[0].message.content = "OpenAI test response."
    mock_sdk_response.usage.prompt_tokens = 12
    mock_sdk_response.usage.completion_tokens = 8
    mock_sdk_response.usage.total_tokens = 20

    with patch.object(provider.client.chat.completions, "create",
                      new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_sdk_response

        # Test public method call
        result = await provider.generate_text("Test prompt")

        assert isinstance(result, LLMResult)
        assert result.success is True
        assert isinstance(result.content, str)
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.operation == "generate_text"
        assert isinstance(result.latency_ms, float)
        assert isinstance(result.total_tokens, int)


@pytest.mark.asyncio
async def test_openai_embed_text_contract(llm_factory):
    expected_dim = 2
    provider = llm_factory.create(LLMEnum.OPENAI.value)
    provider.set_embedding_model("text-embedding-3-small", embedding_size=expected_dim)

    mock_sdk_response = MagicMock()
    mock_data_item = MagicMock()
    mock_data_item.embedding = [0.11, 0.22]
    mock_sdk_response.data = [mock_data_item]
    mock_sdk_response.usage.prompt_tokens = 4
    mock_sdk_response.usage.total_tokens = 4

    with patch.object(provider.client.embeddings, "create",
                      new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = mock_sdk_response

        # Test public method call
        result = await provider.embed_text("embed prompt")

        assert isinstance(result, LLMResult)
        assert result.success is True
        assert isinstance(result.content, list)
        assert len(result.content) == expected_dim
        assert isinstance(result.total_tokens, int)


@pytest.mark.asyncio
async def test_error_and_timeout_failure_contract(llm_factory):
    """Ensures exceptions and timeouts map cleanly to a failed LLMResult contract."""
    provider = llm_factory.create(LLMEnum.OPENAI.value)
    provider.set_generation_model("gpt-4o")

    with patch.object(provider.client.chat.completions, "create",
                      new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("Simulated Network Error")

        # Test public method failure handling
        result = await provider.generate_text("Trigger error")

        assert isinstance(result, LLMResult)
        assert result.success is False
        assert result.content is None
        assert isinstance(result.error_message, str)
        assert len(result.error_message) > 0
        assert isinstance(result.latency_ms, float)

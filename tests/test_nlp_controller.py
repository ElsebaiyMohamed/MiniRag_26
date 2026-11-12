import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from controllers.NLPController import NLPController
from models.schemas import LLMResult


@pytest.mark.asyncio
async def test_index_returns_failed_count_when_embedding_fails(settings_stub):
    failed_embedding_result = LLMResult(
        content=None, provider="openai", model="test", operation="embed_text",
        latency_ms=10.0, success=False, error_message="Embedding API error"
    )
    embedding = SimpleNamespace(
        embed_text=AsyncMock(return_value=failed_embedding_result), embedding_size=3)
    vector_db = SimpleNamespace(create_collection=AsyncMock(), insert_many=AsyncMock())
    controller = NLPController(vector_db, None, embedding)
    chunk = SimpleNamespace(
        chunk_id=1, chunk_asset_id=2, chunk_text="text", chunk_metadata={}
    )

    result = await controller.index2vectordb(
        SimpleNamespace(project_id=7), [chunk]
    )

    assert result["success"] == 0
    assert result["failed"] == 1
    vector_db.create_collection.assert_not_awaited()
    vector_db.insert_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_returns_false_when_embedding_or_vector_results_are_missing(
        settings_stub,
):
    failed_embedding_result = LLMResult(
        content=None, provider="openai", model="test", operation="embed_text",
        latency_ms=5.0, success=False, error_message="Failed"
    )
    embedding = SimpleNamespace(
        embed_text=AsyncMock(return_value=failed_embedding_result), embedding_size=3)
    vector_db = SimpleNamespace(search_by_vector=AsyncMock(return_value=False))
    controller = NLPController(vector_db, None, embedding)

    result_docs, embed_res = await controller.search_vector_db_collection(
        SimpleNamespace(project_id=1), "query"
    )
    assert result_docs is False
    assert embed_res.success is False

    # Test when embedding succeeds but vector search returns False
    success_embedding_result = LLMResult(
        content=[0.1, 0.2, 0.3], provider="openai", model="test",
        operation="embed_text",
        latency_ms=5.0, success=True
    )
    embedding.embed_text.return_value = success_embedding_result

    result_docs, embed_res = await controller.search_vector_db_collection(
        SimpleNamespace(project_id=1), "query"
    )
    assert result_docs is False
    assert embed_res.success is True
    assert embed_res.content == []  # Cleared out for search response telemetry


@pytest.mark.asyncio
async def test_answer_returns_error_when_retrieval_finds_no_documents(
        settings_stub,
):
    success_embedding_result = LLMResult(
        content=[0.1, 0.2, 0.3], provider="openai", model="test",
        operation="embed_text",
        latency_ms=5.0, success=True
    )
    controller = NLPController(
        vectordb_client=SimpleNamespace(search_by_vector=AsyncMock(return_value=[])),
        generation_client=SimpleNamespace(generate_text=AsyncMock()),
        embedding_client=SimpleNamespace(
            embed_text=AsyncMock(return_value=success_embedding_result)),
        template_parser=SimpleNamespace(),
    )

    answer, embed_res, prompt, history, err = await controller.answer_rag_question(
        project=SimpleNamespace(project_id=1), query="question"
    )
    assert answer is None
    assert err == "No relevant documents found in vector database"

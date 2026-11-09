import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from controllers.NLPController import NLPController
from models.enums import DocumentTypeEnum


@pytest.mark.asyncio
async def test_index_returns_failed_count_when_embedding_fails():
    embedding = SimpleNamespace(embed_text=AsyncMock(return_value=None), embedding_size=3)
    vector_db = SimpleNamespace(create_collection=AsyncMock(), insert_many=AsyncMock())
    controller = NLPController(vector_db, None, embedding)
    chunk = SimpleNamespace(
        chunk_id=1, chunk_asset_id=2, chunk_text="text", chunk_metadata={}
    )

    result = await controller.index2vectordb(
        SimpleNamespace(project_id=7), [chunk]
    )

    assert result == {"success": 0, "failed": 1}
    vector_db.create_collection.assert_not_awaited()
    vector_db.insert_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_returns_false_when_embedding_or_vector_results_are_missing():
    embedding = SimpleNamespace(embed_text=AsyncMock(return_value=None), embedding_size=3)
    vector_db = SimpleNamespace(search_by_vector=AsyncMock(return_value=False))
    controller = NLPController(vector_db, None, embedding)

    assert await controller.search_vector_db_collection(
        SimpleNamespace(project_id=1), "query"
    ) is False
    embedding.embed_text.assert_awaited_once_with(
        prompts="query", document_type=DocumentTypeEnum.QUERY.value
    )

    embedding.embed_text.return_value = [0.1, 0.2, 0.3]
    assert await controller.search_vector_db_collection(
        SimpleNamespace(project_id=1), "query"
    ) is False


@pytest.mark.asyncio
async def test_answer_returns_empty_tuple_when_retrieval_finds_no_documents():
    controller = NLPController(
        vectordb_client=SimpleNamespace(),
        generation_client=SimpleNamespace(generate_text=AsyncMock()),
        embedding_client=SimpleNamespace(embed_text=AsyncMock(return_value=None)),
        template_parser=SimpleNamespace(),
    )

    assert await controller.answer_rag_question(
        SimpleNamespace(project_id=1), "question"
    ) == (None, None, None)

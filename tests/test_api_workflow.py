
import asyncio
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import httpx
import pytest
from fastapi import FastAPI

from ingestion.chunkers import create_default_chunker_factory

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
)

from application.ports import AssetRecord
from infrastructure.adapters.file_storage import (
    LocalFileStorage as RealLocalFileStorage,
)
from infrastructure.adapters.asset_file_resolver import (
    LocalAssetFileResolver as RealLocalAssetFileResolver,
)
from ingestion.loaders import create_default_loader_registry
from models import AssetDataModel, ChunkDataModel, ProjectDataModel
from models.enums import AssetStatus, OpenAIEnum, ResponseSignal
from models.schemas import LLMResult, RetrievedDocument
from routes import data as data_routes
from routes import nlp as nlp_routes
from stores.llm.templates import TemplateParser


class FakeProjectModel:
    def __init__(self):
        self.project = None

    async def get_project(self, project_id):
        return (
            self.project
            if self.project and self.project.project_id == project_id
            else None
        )

    async def get_project_or_create_one(self, project_id):
        if self.project is None:
            self.project = SimpleNamespace(project_id=project_id)
        return self.project


class FakeAssetModel:
    def __init__(self):
        self.assets = []

    async def create_asset(self, asset):
        asset.asset_id = len(self.assets) + 1
        self.assets.append(asset)
        return asset

    async def get_all_project_assets(self, asset_project_id, asset_type):
        return self.assets

    async def set_asset_status(self, asset_id, status):
        next(
            asset for asset in self.assets
            if asset.asset_id == asset_id
        ).asset_status = status

class FakeProjectRepository:
    def __init__(self, projects):
        self.projects = projects

    async def get_or_create(self, project_id):
        project = await self.projects.get_project_or_create_one(
            project_id=project_id
        )
        return project.project_id


class FakeAssetRepository:
    def __init__(self, assets):
        self.assets = assets

    async def create(self, asset):
        db_asset = SimpleNamespace(
            asset_project_id=asset.project_id,
            asset_type=asset.asset_type,
            asset_name=asset.asset_name,
            asset_size=asset.asset_size,
            asset_status=asset.asset_status,
        )

        created_asset = await self.assets.create_asset(db_asset)

        return AssetRecord(asset_name=created_asset.asset_name)

class FakeChunkModel:
    def __init__(self):
        self.chunks = []

    async def create_many_chunks(self, chunks):
        for chunk in chunks:
            chunk.chunk_id = len(self.chunks) + 1
            self.chunks.append(chunk)
        return len(chunks)

    async def get_project_asset_chunks(self, asset_id, page_no):
        return [
            chunk for chunk in self.chunks
            if chunk.chunk_asset_id == asset_id and page_no == 1
        ]


class FakeUploadController:
    def __init__(self, loader_registry):
        self.loader_registry = loader_registry

    async def validate(self, upload):
        supported_types = {
            ".txt": {"text/plain"},
            ".md": {
                "text/markdown",
                "text/x-markdown",
                "text/plain",
            },
            ".markdown": {
                "text/markdown",
                "text/x-markdown",
            },
        }

        extension = Path(upload.filename).suffix.lower()

        if upload.content_type in supported_types.get(extension, set()):
            return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value

        return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

    def gen_unique_filename(self, filename, project_path):
        return f"test_{filename}"

    @staticmethod
    def join_path(project_path, filename):
        return os.path.join(project_path, filename)


class TrackingLoaderRegistry:
    """Wrap the real registry and record the document-loading thread."""

    def __init__(self, registry):
        self.registry = registry
        self.processing_thread_id = None

    def supported_extensions(self):
        return self.registry.supported_extensions()

    def for_path(self, path):
        loader = self.registry.for_path(path)
        registry = self

        class TrackingLoader:
            def load(self, file_path):
                registry.processing_thread_id = threading.get_ident()
                return loader.load(file_path)

            @property
            def mime_types(self):
                return loader.mime_types

        return TrackingLoader()


class FakeAssetProcessingRepository:
    """Fake atomic persistence adapter for API workflow tests."""

    def __init__(self, assets, chunks_model):
        self.assets = assets
        self.chunks_model = chunks_model

    async def persist(self, asset_id, chunks):
        asset = next(
            (
                item
                for item in self.assets.assets
                if item.asset_id == asset_id
            ),
            None,
        )

        if asset is None or not chunks:
            return 0

        for chunk in chunks:
            db_chunk = SimpleNamespace(
                chunk_id=len(self.chunks_model.chunks) + 1,
                chunk_project_id=chunk.project_id,
                chunk_asset_id=chunk.asset_id,
                chunk_text=chunk.text,
                chunk_order=chunk.order,
                chunk_metadata=chunk.metadata,
            )
            self.chunks_model.chunks.append(db_chunk)

        asset.asset_status = AssetStatus.CHUNKED.value
        return len(chunks)

class FakeEmbeddingClient:
    embedding_size = 2

    async def embed_text(self, prompts, document_type=None):
        def embed(text):
            return [float(len(text)), 1.0]

        content = (
            embed(prompts)
            if isinstance(prompts, str)
            else [embed(text) for text in prompts]
        )

        return LLMResult(
            content=content,
            provider="openai",
            model="text-embedding-3-small",
            operation="embed_text",
            latency_ms=1.5,
            success=True,
            prompt_tokens=4,
            total_tokens=4,
        )

class FakeRankingEmbeddingClient:
    embedding_size = 2

    QUERY_VECTOR: ClassVar[list[float]] = [1.0, 0.0]
    TARGET_VECTOR: ClassVar[list[float]] = [1.0, 0.0]
    DISTRACTOR_VECTOR: ClassVar[list[float]] = [0.0, 1.0]

    async def embed_text(self, prompts, document_type=None):
        def embed(text):
            if document_type == "query":
                return self.QUERY_VECTOR

            if "vector indexing verification" in text:
                return self.TARGET_VECTOR

            return self.DISTRACTOR_VECTOR

        content = (
            embed(prompts)
            if isinstance(prompts, str)
            else [embed(text) for text in prompts]
        )

        return LLMResult(
            content=content,
            provider="fake",
            model="deterministic-ranking",
            operation="embed_text",
            latency_ms=0.0,
            success=True,
            prompt_tokens=0,
            total_tokens=0,
        )

class FakeGenerationClient:
    enum = OpenAIEnum

    @staticmethod
    def construct_prompt(prompt, role):
        return {"role": role, "content": prompt}

    async def generate_text(self, prompt, chat_history):
        return LLMResult(
            content="The document says the answer is 42.",
            provider="openai",
            model="gpt-4o",
            operation="generate_text",
            latency_ms=12.0,
            success=True,
            prompt_tokens=25,
            completion_tokens=8,
            total_tokens=33,
        )


class FakeVectorDB:
    def __init__(self, distance_method="cosine"):
        if distance_method not in {"cosine", "dot"}:
            raise ValueError(
                f"Unsupported distance method: {distance_method}"
            )

        self.distance_method = distance_method
        self.records = []

    async def create_collection(
        self,
        collection_name,
        embedding_size,
        do_reset=False,
    ):
        if do_reset:
            self.records.clear()
        return True

    async def insert_many(
        self,
        collection_name,
        texts,
        metadatas,
        vectors,
        record_ids,
        asset_ids,
    ):
        self.records.extend(
            (text, vector)
            for text, vector in zip(texts, vectors)
        )

        return {"success": len(texts), "failed": 0}

    def _calculate_score(self, first, second):
        dot_product = sum(
            left * right
            for left, right in zip(first, second)
        )

        if self.distance_method == "dot":
            return dot_product

        first_norm = sum(value ** 2 for value in first) ** 0.5
        second_norm = sum(value ** 2 for value in second) ** 0.5

        if first_norm == 0 or second_norm == 0:
            return 0.0

        return dot_product / (first_norm * second_norm)

    async def search_by_vector(self, collection_name, vector, limit):
        ranked_records = sorted(
            self.records,
            key=lambda record: self._calculate_score(
                record[1],
                vector,
            ),
            reverse=True,
        )

        return [
            RetrievedDocument(
                text=text,
                score=self._calculate_score(record_vector, vector),
            )
            for text, record_vector in ranked_records[:limit]
        ]

    async def delete_embeddings_by_asset_id(self, collection_name, asset_id):
        return 0

    async def delete_collection(self, collection_name):
        self.records.clear()
        return True

    async def get_collection_info(self, collection_name):
        return {"record_count": len(self.records)}

@pytest.fixture
def workflow_models(monkeypatch):
    projects = FakeProjectModel()
    assets = FakeAssetModel()
    chunks = FakeChunkModel()

    async def create_project_model(cls, db_client):
        return projects

    async def create_asset_model(cls, db_client):
        return assets

    async def create_chunk_model(cls, db_client):
        return chunks

    monkeypatch.setattr(
        ProjectDataModel,
        "create_instance",
        classmethod(create_project_model),
    )

    monkeypatch.setattr(
        AssetDataModel,
        "create_instance",
        classmethod(create_asset_model),
    )

    monkeypatch.setattr(
        ChunkDataModel,
        "create_instance",
        classmethod(create_chunk_model),
    )

    return projects, assets, chunks


@pytest.fixture
def upload_api(tmp_path, monkeypatch, workflow_models):
    projects, assets, _ = workflow_models

    monkeypatch.setattr(
        data_routes,
        "LocalFileStorage",
        lambda base_dir: RealLocalFileStorage(tmp_path),
    )
    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyProjectRepository",
        lambda db_client: FakeProjectRepository(projects),
    )
    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyAssetRepository",
        lambda db_client: FakeAssetRepository(assets),
    )

    app = FastAPI()
    app.include_router(data_routes.data_router)

    app.loader_registry = create_default_loader_registry()
    app.db_client = object()

    settings = SimpleNamespace(
        FILE_DEAFAULT_CHUNK_SIZE=16,
        FILE_ALLOWED_EXTENTIONS=[
            "text/plain",
            "text/markdown",
            "text/x-markdown",
        ],
        FILE_MAX_SIZE_IN_MB=10,
    )

    app.dependency_overrides[data_routes.get_settings] = (
        lambda: settings
    )

    return app, settings


@pytest.mark.asyncio
async def test_upload_route_success(upload_api):
    app, _ = upload_api

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "source.txt",
                    b"Upload API test.",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 200
    assert response.json()["signal"] == (
        ResponseSignal.FILE_UPLOAD_SUCCESS.value
    )
    assert response.json()["file_id"]
    assert response.json()["file_id"].endswith("_source.txt")


@pytest.mark.asyncio
async def test_upload_route_rejects_unsupported_type(upload_api):
    app, _ = upload_api

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "unsupported.pdf",
                    b"PDF content",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "signal": ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
    }


@pytest.mark.asyncio
async def test_upload_route_rejects_oversized_file(upload_api):
    app, settings = upload_api

    # A zero-MB limit makes any non-empty upload oversized.
    settings.FILE_MAX_SIZE_IN_MB = 0

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "source.txt",
                    b"Non-empty file",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "signal": ResponseSignal.FILE_SIZE_EXCEEDED.value
    }


@pytest.mark.asyncio
async def test_upload_route_handles_storage_failure(
    upload_api,
    monkeypatch,
):
    app, _ = upload_api

    class FailingFileStorage:
        async def store(
            self,
            project_id,
            original_filename,
            source,
            chunk_size,
        ):
            raise OSError("Simulated storage failure")

    monkeypatch.setattr(
        data_routes,
        "LocalFileStorage",
        lambda base_dir: FailingFileStorage(),
    )

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "source.txt",
                    b"Upload storage failure test.",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 500
    assert response.json() == {
        "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
    }


@pytest.mark.asyncio
async def test_upload_process_index_search_answer_workflow(
    tmp_path,
    monkeypatch,
    workflow_models,
    settings_stub,
):
    projects, assets, chunks = workflow_models

    project_assets = tmp_path / "assets" / "files"
    project_assets.mkdir(parents=True)

    monkeypatch.setattr(
        data_routes,
        "LocalFileStorage",
        lambda base_dir: RealLocalFileStorage(tmp_path),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyProjectRepository",
        lambda db_client: FakeProjectRepository(projects),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyAssetRepository",
        lambda db_client: FakeAssetRepository(assets),
    )

    # Use the test upload directory for asset resolution.
    monkeypatch.setattr(
        data_routes,
        "LocalAssetFileResolver",
        lambda base_dir: RealLocalAssetFileResolver(tmp_path),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyAssetProcessingRepository",
        lambda db_client: FakeAssetProcessingRepository(
            assets,
            chunks,
        ),
    )

    tracking_registry = TrackingLoaderRegistry(
        create_default_loader_registry()
    )

    app = FastAPI()

    # The processing semaphore is normally initialized by the
    # application's lifespan. This test creates FastAPI directly,
    # so we initialize it here.

    app.processing_semaphore = asyncio.Semaphore(2)

    app.include_router(data_routes.data_router)
    app.include_router(nlp_routes.nlp_router)
    app.loader_registry = tracking_registry
    app.chunker_factory = create_default_chunker_factory()
    app.db_client = object()
    app.vectordb_client = FakeVectorDB()
    app.embedding_client = FakeEmbeddingClient()
    app.generation_client = FakeGenerationClient()
    app.template_parser = TemplateParser(language="en")

    app.dependency_overrides[data_routes.get_settings] = (
        lambda: SimpleNamespace(
            FILE_DEAFAULT_CHUNK_SIZE=16,
            FILE_ALLOWED_EXTENTIONS=[
                "text/plain",
                "text/markdown",
                "text/x-markdown",
            ],
            FILE_MAX_SIZE_IN_MB=10,
        )
    )

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        # 1. Upload a text file.
        upload_response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "source.txt",
                    b"The answer is 42.",
                    "text/plain",
                )
            },
        )

        assert upload_response.status_code == 200
        assert (
            upload_response.json()["signal"]
            == ResponseSignal.FILE_UPLOAD_SUCCESS.value
        )

        # 2. Capture the event-loop thread ID BEFORE processing.
        event_loop_thread_id = threading.get_ident()

        # 3. Process the uploaded document.
        process_response = await client.post(
            "/api/v1/data/process/1",
            json={
                "chunk_size": 500,
                "overlap_size": 20,
            },
        )

        assert process_response.status_code == 200
        assert process_response.json()["no_files_success"] == 1

        # 4. Verify that processing ran in a worker thread,
        #    not in the event-loop thread.
        assert tracking_registry.processing_thread_id is not None

        assert (
                tracking_registry.processing_thread_id
                != event_loop_thread_id
        ), "Document loading blocked the event-loop thread!"

        assert len(chunks.chunks) == 1

        assert (
            assets.assets[0].asset_status
            == AssetStatus.CHUNKED.value
        )

        # 5. Push chunks into the vector database.
        push_response = await client.post(
            "/api/v1/nlp/index/push/1",
            json={},
        )

        assert push_response.status_code == 200

        assert (
            push_response.json()["signal"]
            == ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value
        )

        assert (
            assets.assets[0].asset_status
            == AssetStatus.INDEXED.value
        )

        # 6. Search the indexed document.
        search_response = await client.post(
            "/api/v1/nlp/index/search/1",
            json={
                "text": "answer",
                "limit": 1,
            },
        )

        assert search_response.status_code == 200

        assert (
            search_response.json()["result"][0]["text"]
            == "The answer is 42."
        )

        assert "telemetry" in search_response.json()

        # 7. Generate an answer using the retrieved document.
        answer_response = await client.post(
            "/api/v1/nlp/index/answer/1",
            json={
                "text": "What is the answer?",
                "debug": True,
            },
        )

        assert answer_response.status_code == 200

        answer = answer_response.json()

        assert (
            answer["answer"]
            == "The document says the answer is 42."
        )

        assert "full_prompt" in answer
        assert "chat_history" in answer
        assert "telemetry" in answer

    assert projects.project.project_id == 1


@pytest.mark.asyncio
async def test_markdown_upload_process_index_search_workflow(
    tmp_path,
    monkeypatch,
    workflow_models,
    settings_stub,
):
    projects, assets, chunks = workflow_models

    project_assets = tmp_path / "assets" / "files"
    project_assets.mkdir(parents=True)

    monkeypatch.setattr(
        data_routes,
        "LocalFileStorage",
        lambda base_dir: RealLocalFileStorage(tmp_path),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyProjectRepository",
        lambda db_client: FakeProjectRepository(projects),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyAssetRepository",
        lambda db_client: FakeAssetRepository(assets),
    )

    monkeypatch.setattr(
        data_routes,
        "LocalAssetFileResolver",
        lambda base_dir: RealLocalAssetFileResolver(tmp_path),
    )

    monkeypatch.setattr(
        data_routes,
        "SqlAlchemyAssetProcessingRepository",
        lambda db_client: FakeAssetProcessingRepository(
            assets,
            chunks,
        ),
    )
    app = FastAPI()
    app.processing_semaphore = asyncio.Semaphore(2)

    app.include_router(data_routes.data_router)
    app.include_router(nlp_routes.nlp_router)

    app.loader_registry = create_default_loader_registry()
    app.chunker_factory = create_default_chunker_factory()
    app.db_client = object()
    app.vectordb_client = FakeVectorDB(distance_method="cosine")
    app.embedding_client = FakeRankingEmbeddingClient()
    app.generation_client = FakeGenerationClient()
    app.template_parser = TemplateParser(language="en")

    app.dependency_overrides[data_routes.get_settings] = (
        lambda: SimpleNamespace(
            FILE_DEAFAULT_CHUNK_SIZE=16,
            FILE_ALLOWED_EXTENTIONS=[
                "text/plain",
                "text/markdown",
                "text/x-markdown",
            ],
            FILE_MAX_SIZE_IN_MB=10,
        )
    )

    markdown_content = b"""---
title: Markdown Test
language: en
---

# Markdown Ingestion

This document contains a unique phrase: **vector indexing verification**.

## Implementation

- Markdown headings are preserved.
- Lists are preserved.

<!-- This comment must not appear in the indexed content. -->

```python
def markdown_example():
    return "structured content"
```

| Component | Status |
|---|---|
| Loader | Ready |
| Indexing | Ready |
"""

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        # 1. Upload Markdown.
        upload_response = await client.post(
            "/api/v1/data/upload/1",
            files={
                "file": (
                    "guide.md",
                    markdown_content,
                    "text/markdown",
                )
            },
        )

        assert upload_response.status_code == 200
        assert (
            upload_response.json()["signal"]
            == ResponseSignal.FILE_UPLOAD_SUCCESS.value
        )
        distractors = {
            "database.md": (
                "# Database Setup\n\n"
                "Configure PostgreSQL connections and database migrations."
            ),
            "deployment.md": (
                "# Deployment Guide\n\n"
                "Build Docker images and configure production environments."
            ),
            "authentication.md": (
                "# Authentication\n\n"
                "Configure API keys, access tokens, and user permissions."
            ),
            "monitoring.md": (
                "# Monitoring\n\n"
                "Track application logs, metrics, and service health."
            ),
        }

        for filename, content in distractors.items():
            response = await client.post(
                "/api/v1/data/upload/1",
                files={
                    "file": (
                        filename,
                        content.encode("utf-8"),
                        "text/markdown",
                    )
                },
            )

            assert response.status_code == 200
        # 2. Process Markdown.
        process_response = await client.post(
            "/api/v1/data/process/1",
            json={"chunk_size": 500, "overlap_size": 20},
        )

        assert process_response.status_code == 200
        assert process_response.json()["no_files_success"] == 5
        assert len(chunks.chunks) == 5

        processed_text = chunks.chunks[0].chunk_text

        assert "# Markdown Ingestion" in processed_text
        assert "## Implementation" in processed_text
        assert "vector indexing verification" in processed_text
        assert "```python" in processed_text
        assert "| Component | Status |" in processed_text
        assert "Markdown Test" not in processed_text
        assert "This comment must not appear" not in processed_text

        # 3. Index Markdown.
        push_response = await client.post(
            "/api/v1/nlp/index/push/1",
            json={},
        )

        assert push_response.status_code == 200
        assert (
            push_response.json()["signal"]
            == ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value
        )

        assert assets.assets[0].asset_status == AssetStatus.INDEXED.value

        # 4. Search Markdown content.
        search_response = await client.post(
            "/api/v1/nlp/index/search/1",
            json={
                "text": "vector indexing verification",
                "limit": 3,
            },
        )

        assert search_response.status_code == 200

        results = search_response.json()["result"]

        assert len(results) == 3
        assert any(
            "vector indexing verification" in result["text"]
            for result in results
        )

    assert projects.project.project_id == 1

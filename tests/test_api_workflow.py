import os
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from models import AssetDataModel, ChunkDataModel, ProjectDataModel
from models.enums import AssetStatus, OpenAIEnum, ResponseSignal
from models.schemas import RetrievedDocument
from models.schemas import LLMResult
from routes import data as data_routes
from routes import nlp as nlp_routes
from stores.llm.templates import TemplateParser


class FakeProjectModel:
    def __init__(self):
        self.project = None

    async def get_project(self, project_id):
        return self.project if self.project and self.project.project_id == project_id else None

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
        next(asset for asset in self.assets if asset.asset_id == asset_id).asset_status = status


class FakeChunkModel:
    def __init__(self):
        self.chunks = []

    async def create_many_chunks(self, chunks):
        for chunk in chunks:
            chunk.chunk_id = len(self.chunks) + 1
            self.chunks.append(chunk)
        return len(chunks)

    async def get_project_asset_chunks(self, asset_id, page_no):
        return [chunk for chunk in self.chunks if
                chunk.chunk_asset_id == asset_id and page_no == 1]


class FakeUploadController:
    async def validate(self, upload):
        if upload.filename.endswith(".txt") and upload.content_type == "text/plain":
            return True, ResponseSignal.FILE_VALIDATED_SUCCESS.value
        return False, ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value

    def gen_unique_filename(self, filename, project_path):
        return f"test_{filename}"

    @staticmethod
    def join_path(project_path, filename):
        return os.path.join(project_path, filename)


class FakeProcessController:
    def __init__(self, project_id, assets_path):
        self.assets_path = assets_path

    def get_file_content(self, file_id):
        path = Path(self.assets_path) / str(1) / file_id
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def process_file_content(file_content, chunk_size, overlap_size):
        return [SimpleNamespace(page_content=file_content.strip(), metadata={"source": "upload"})]


class FakeEmbeddingClient:
    embedding_size = 2

    async def embed_text(self, prompts, document_type=None):
        def embed(text):
            return [float(len(text)), 1.0]

        content = embed(prompts) if isinstance(prompts, str) else [embed(text) for text
                                                                   in prompts]
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
    def __init__(self):
        self.records = []

    async def create_collection(self, collection_name, embedding_size, do_reset=False):
        if do_reset:
            self.records.clear()
        return True

    async def insert_many(self, collection_name, texts, metadatas, vectors, record_ids,
                          asset_ids):
        self.records.extend((text, vector) for text, vector in zip(texts, vectors))
        return {"success": len(texts), "failed": 0}

    async def search_by_vector(self, collection_name, vector, limit):
        return [RetrievedDocument(text=text, score=1.0) for text, _ in
                self.records[:limit]]

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

    monkeypatch.setattr(ProjectDataModel, "create_instance", classmethod(create_project_model))
    monkeypatch.setattr(AssetDataModel, "create_instance", classmethod(create_asset_model))
    monkeypatch.setattr(ChunkDataModel, "create_instance", classmethod(create_chunk_model))
    return projects, assets, chunks


@pytest.mark.asyncio
async def test_upload_process_index_search_answer_workflow(tmp_path, monkeypatch,
                                                           workflow_models,
                                                           settings_stub):
    projects, assets, chunks = workflow_models
    project_assets = tmp_path / "assets"
    project_assets.mkdir()
    monkeypatch.setattr(data_routes, "DataController", FakeUploadController)

    def get_project_path(project_id):
        project_path = project_assets / str(project_id)
        project_path.mkdir(exist_ok=True)
        return str(project_path)

    monkeypatch.setattr(data_routes, "ProjectController",
                        lambda: SimpleNamespace(get_project_path=get_project_path))
    monkeypatch.setattr(
        data_routes, "ProcessController",
        lambda project_id: FakeProcessController(project_id, project_assets)
    )

    app = FastAPI()
    app.include_router(data_routes.data_router)
    app.include_router(nlp_routes.nlp_router)
    app.db_client = object()
    app.vectordb_client = FakeVectorDB()
    app.embedding_client = FakeEmbeddingClient()
    app.generation_client = FakeGenerationClient()
    app.template_parser = TemplateParser(language="en")
    app.dependency_overrides[data_routes.get_settings] = lambda: SimpleNamespace(
        FILE_DEAFAULT_CHINK_SIZE=16)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        upload_response = await client.post(
            "/api/v1/data/upload/1",
            files={"file": ("source.txt", b"The answer is 42.", "text/plain")},
        )
        assert upload_response.status_code == 200
        assert upload_response.json()["signal"] == ResponseSignal.FILE_UPLOAD_SUCCESS.value

        process_response = await client.post("/api/v1/data/process/1",
                                             json={"chunk_size": 500,
                                                   "overlap_size": 20})
        assert process_response.status_code == 200
        assert process_response.json()["no_files_success"] == 1
        assert len(chunks.chunks) == 1
        assert assets.assets[0].asset_status == AssetStatus.CHUNKED.value

        push_response = await client.post("/api/v1/nlp/index/push/1", json={})
        assert push_response.status_code == 200
        assert push_response.json()["signal"] == (
            ResponseSignal.INSERT_INTO_VECTOR_DATABASE_SUCCESS.value)
        assert assets.assets[0].asset_status == AssetStatus.INDEXED.value

        search_response = await client.post("/api/v1/nlp/index/search/1",
                                            json={"text": "answer", "limit": 1})
        assert search_response.status_code == 200
        assert search_response.json()["result"][0]["text"] == "The answer is 42."
        assert "telemetry" in search_response.json()

        answer_response = await client.post(
            "/api/v1/nlp/index/answer/1",
            json={"text": "What is the answer?", "debug": True},
        )
        assert answer_response.status_code == 200
        answer = answer_response.json()
        assert answer["answer"] == "The document says the answer is 42."
        assert "full_prompt" in answer
        assert "chat_history" in answer
        assert "telemetry" in answer

    assert projects.project.project_id == 1

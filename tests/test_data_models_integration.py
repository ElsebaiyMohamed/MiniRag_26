import importlib
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from models import AssetDataModel, ChunkDataModel, ProjectDataModel
from models.db_schemas import Asset, DataChunk, Project


@pytest.mark.asyncio
async def test_project_asset_and_chunk_models(pgvector_session_factory, monkeypatch):
    base_data_model = importlib.import_module("models.BaseDataModel")
    monkeypatch.setattr(base_data_model, "get_settings", lambda: SimpleNamespace())
    projects = await ProjectDataModel.create_instance(pgvector_session_factory)
    assets = await AssetDataModel.create_instance(pgvector_session_factory)
    chunks = await ChunkDataModel.create_instance(pgvector_session_factory)

    project = await projects.create_project(Project())
    assert await projects.get_project(project.project_id) is not None
    existing_project = await projects.get_project_or_create_one(project.project_id)
    assert existing_project.project_id == project.project_id

    second_project = await projects.get_project_or_create_one(project_id=project.project_id + 1)
    project_page, total_pages = await projects.get_all_projects(page=1, page_size=1)
    assert len(project_page) == 1
    assert total_pages == 2
    assert await projects.delete_project(project_id=999999) is False

    first_asset = await assets.create_asset(Asset(
        asset_project_id=project.project_id,
        asset_type="FILE",
        asset_name="first.txt",
        asset_size=5,
        asset_status=0,
    ))
    additional_assets = [
        Asset(
            asset_project_id=project.project_id,
            asset_type="FILE",
            asset_name=f"extra-{index}.txt",
            asset_size=index,
            asset_status=index,
        )
        for index in (1, 2)
    ]
    assert await assets.create_many_assets(additional_assets, batch_size=1) == 2
    assert (await assets.get_asset_by_id(first_asset.asset_id)).asset_name == "first.txt"
    assert (await assets.get_asset_by_name(project.project_id, "first.txt")).asset_id == first_asset.asset_id
    assert len(await assets.get_all_project_assets(project.project_id, "FILE")) == 3
    assert len(await assets.get_all_project_assets(project.project_id, "FILE", asset_status=1)) == 1
    assert await assets.set_asset_status(first_asset.asset_id, 2) is True
    assert await assets.set_asset_status(999999, 2) is False

    first_chunk = await chunks.create_chunk(DataChunk(
        chunk_text="first",
        chunk_metadata={"page": 1},
        chunk_order=1,
        chunk_project_id=project.project_id,
        chunk_asset_id=first_asset.asset_id,
    ))
    additional_chunks = [
        DataChunk(
            chunk_text=f"chunk-{index}",
            chunk_metadata={"page": index},
            chunk_order=index + 1,
            chunk_project_id=project.project_id,
            chunk_asset_id=first_asset.asset_id,
        )
        for index in range(2)
    ]
    assert await chunks.create_many_chunks(additional_chunks, batch_size=1) == 2
    assert (await chunks.get_chunk(first_chunk.chunk_id)).chunk_text == "first"
    assert len(await chunks.get_project_chunks(project.project_id, page_no=1, page_size=2)) == 2
    assert len(await chunks.get_project_asset_chunks(
        first_asset.asset_id, page_no=1, page_size=2
    )) == 2
    assert await chunks.delete_chunks_by_asset_id(first_asset.asset_id) is True
    assert await chunks.delete_chunks_by_asset_id(first_asset.asset_id) is False
    assert await chunks.delete_chunks_by_project_id(project.project_id) == 0

    assert await assets.delete_asset(first_asset.asset_id) is True
    assert await assets.delete_asset(first_asset.asset_id) is False
    assert await projects.delete_project(project.project_id) is True
    assert await projects.get_project(project.project_id) is None
    assert await projects.delete_project(second_project.project_id) is True

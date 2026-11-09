import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from utils.metrics import setup_metrics


@pytest.mark.asyncio
async def test_metrics_use_route_templates_instead_of_concrete_paths(monkeypatch):
    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    app = FastAPI()

    @app.get("/projects/{project_id}")
    async def get_project(project_id: int):
        return {"project_id": project_id}

    setup_metrics(app)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/projects/17")).status_code == 200
        assert (await client.get("/projects/18")).status_code == 200
        metrics = (await client.get("/metrics")).text

    assert 'endpoint="/projects/{project_id}"' in metrics
    assert 'endpoint="/projects/17"' not in metrics
    assert 'endpoint="/projects/18"' not in metrics

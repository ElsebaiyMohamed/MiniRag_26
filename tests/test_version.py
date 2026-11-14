import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

from fastapi.testclient import TestClient

import __version__ as app_version
from main import app


def test_version_matches_pyproject():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"

    with pyproject_path.open("rb") as file:
        expected_version = tomllib.load(file)["project"]["version"]

    assert app_version.__version__ == expected_version
    assert app.version == expected_version


def test_version_fallback_when_package_metadata_missing(monkeypatch):
    def raise_package_not_found(_package_name):
        raise PackageNotFoundError

    monkeypatch.setattr(app_version, "version", raise_package_not_found)

    expected_version = app_version._version_from_pyproject()

    assert app_version.get_app_version() == expected_version


def test_version_endpoint():
    with TestClient(app) as client:
        response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": app.version}


def test_root_endpoint_uses_canonical_version():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == app.version
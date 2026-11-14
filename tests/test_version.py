
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


def test_pyproject_version_takes_priority_over_installed_metadata(monkeypatch):
    monkeypatch.setattr(app_version, "version", lambda _: "1.2.0")

    expected_version = app_version._version_from_pyproject()

    assert app_version.get_app_version() == expected_version


def test_metadata_fallback_when_pyproject_missing(monkeypatch):
    def raise_file_not_found():
        raise FileNotFoundError("pyproject.toml not found")

    monkeypatch.setattr(
        app_version, "_version_from_pyproject", raise_file_not_found
    )
    monkeypatch.setattr(
        app_version, "version", lambda _: "1.2.0"
    )

    assert app_version.get_app_version() == "1.2.0"


def test_metadata_fallback_raises_when_package_missing(monkeypatch):
    def raise_file_not_found():
        raise FileNotFoundError("pyproject.toml not found")

    def raise_package_not_found(_):
        raise PackageNotFoundError

    monkeypatch.setattr(
        app_version, "_version_from_pyproject", raise_file_not_found
    )
    monkeypatch.setattr(
        app_version, "version", raise_package_not_found
    )

    import pytest

    with pytest.raises(RuntimeError, match="Cannot determine application version"):
        app_version.get_app_version()


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

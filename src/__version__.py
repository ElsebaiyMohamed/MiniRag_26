
import logging
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

logger = logging.getLogger(__name__)

PACKAGE_NAME = "minirag-26"


def _version_from_pyproject() -> str:
    for parent in Path(__file__).resolve().parents:
        pyproject_path = parent / "pyproject.toml"

        if pyproject_path.is_file():
            with pyproject_path.open("rb") as file:
                pyproject = tomllib.load(file)

            return pyproject["project"]["version"]

    raise FileNotFoundError("Could not find pyproject.toml")


def get_app_version() -> str:
    try:
        return _version_from_pyproject()
    except FileNotFoundError:
        logger.warning(
            "pyproject.toml not found; falling back to installed package metadata"
        )

    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError as exc:
        raise RuntimeError(
            "Cannot determine application version: "
            "neither pyproject.toml nor package metadata is available"
        ) from exc


__version__ = get_app_version()

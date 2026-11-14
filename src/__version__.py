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
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        logger.debug(
            "Package metadata for %s not found; reading pyproject.toml",
            PACKAGE_NAME,
        )
        return _version_from_pyproject()


__version__ = get_app_version()
from pathlib import Path

import pytest

from ingestion.exceptions import UnsupportedFileType
from ingestion.loaders import (
    LoaderRegistry,
    create_default_loader_registry,
)


class FakeLoader:
    def __init__(self, extensions, mime_types):
        self.extensions = extensions
        self.mime_types = mime_types

    def load(self, path: Path):
        return []


def test_register_and_lookup_loader():
    registry = LoaderRegistry()
    loader = FakeLoader(
        extensions=(".txt",),
        mime_types=("text/plain",),
    )

    registry.register(loader)

    assert registry.for_path(Path("document.txt")) is loader


def test_lookup_is_case_insensitive():
    registry = LoaderRegistry()
    loader = FakeLoader(
        extensions=(".pdf",),
        mime_types=("application/pdf",),
    )

    registry.register(loader)

    assert registry.for_path(Path("document.PDF")) is loader


def test_duplicate_extension_registration_raises_error():
    registry = LoaderRegistry()

    registry.register(
        FakeLoader((".txt",), ("text/plain",))
    )

    with pytest.raises(ValueError):
        registry.register(
            FakeLoader((".TXT",), ("text/plain",))
        )


def test_unknown_extension_raises_unsupported_file_type():
    registry = LoaderRegistry()

    with pytest.raises(UnsupportedFileType):
        registry.for_path(Path("document.csv"))


def test_supported_extensions():
    registry = create_default_loader_registry()

    assert registry.supported_extensions() == {
        ".txt",
        ".pdf",
        ".md",
        ".markdown",
    }


def test_supported_mime_types():
    registry = create_default_loader_registry()

    assert registry.supported_mime_types() == {
        "text/plain",
        "application/pdf",
        "text/markdown",
        "text/x-markdown",
    }
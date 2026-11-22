import importlib
import os
import sys
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from controllers.ProcessController import ProcessController
from ingestion.chunkers import Chunk, create_default_chunker_factory
from ingestion.loaders import LoadedDocument, create_default_loader_registry

process_controller_module = importlib.import_module("controllers.ProcessController")


def make_controller(project_path):
    controller = ProcessController.__new__(ProcessController)
    controller.project_path = str(project_path)
    controller.loader_registry = create_default_loader_registry()
    controller.chunker_factory = create_default_chunker_factory()
    return controller




def test_process_file_content_maps_documents_to_chunks(tmp_path):
    controller = make_controller(tmp_path)
    documents = [
        LoadedDocument(text="first line\nsecond line", metadata={"page": 1}),
    ]

    chunks = controller.process_file_content(documents, chunk_size=100)

    assert chunks == [
        Chunk(
            text="first line\nsecond line",
            metadata={"page": 1},
            order=1
        )
    ]


def test_get_file_content_loads_text_and_returns_none_for_missing_or_unsupported(
    tmp_path,
):
    controller = make_controller(tmp_path)
    text_file = tmp_path / "source.txt"
    text_file.write_text("first line\nsecond line", encoding="utf-8")
    (tmp_path / "unsupported.csv").write_text("value", encoding="utf-8")

    documents = controller.get_file_content("source.txt")

    assert [document.text for document in documents] == [
        "first line\nsecond line"
    ]
    assert controller.get_file_content("missing.txt") is None
    assert controller.get_file_content("unsupported.csv") is None


def test_get_file_content_uses_pdf_loader(tmp_path):
    controller = make_controller(tmp_path)

    pdf_file = tmp_path / "source.pdf"
    pdf_file.write_bytes(b"placeholder")

    loaded_documents = [LoadedDocument(text="pdf text", metadata={})]

    loader = Mock()
    loader.load.return_value = loaded_documents

    controller.loader_registry._loaders[".pdf"] = loader

    result = controller.get_file_content("source.pdf")

    assert result == loaded_documents
    loader.load.assert_called_once_with(pdf_file)

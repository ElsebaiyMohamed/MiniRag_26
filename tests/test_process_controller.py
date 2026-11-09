import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from controllers.ProcessController import Document, ProcessController

process_controller_module = importlib.import_module("controllers.ProcessController")


def make_controller(project_path):
    controller = ProcessController.__new__(ProcessController)
    controller.project_path = str(project_path)
    return controller


def test_simple_text_splitter_groups_lines_and_keeps_page_metadata(tmp_path):
    controller = make_controller(tmp_path)
    metadata = [{"page": 1}, {"page": 2}]

    chunks = controller.simple_text_spliter(
        pages=["one\n two \n\nx", "three\nfour"],
        metadatas=metadata,
        chunk_size=8,
    )

    assert chunks == [
        Document(page_content="one\ntwo\nthree", metadata=metadata[1]),
        Document(page_content="four", metadata=metadata[1]),
    ]


def test_process_file_content_maps_documents_to_chunks(tmp_path):
    controller = make_controller(tmp_path)
    documents = [
        Document(page_content="first line\nsecond line", metadata={"page": 1}),
    ]

    chunks = controller.process_file_content(documents, chunk_size=100)

    assert chunks == [
        Document(
            page_content="first line\nsecond line",
            metadata={"page": 1},
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

    assert [document.page_content for document in documents] == [
        "first line\nsecond line"
    ]
    assert controller.get_file_content("missing.txt") is None
    assert controller.get_file_content("unsupported.csv") is None


def test_get_file_content_uses_pdf_loader(tmp_path, monkeypatch):
    controller = make_controller(tmp_path)
    pdf_file = tmp_path / "source.pdf"
    pdf_file.write_bytes(b"placeholder")
    loaded_documents = [SimpleNamespace(page_content="pdf text", metadata={})]
    loader = Mock()
    loader.load.return_value = loaded_documents
    pdf_loader = Mock(return_value=loader)
    monkeypatch.setattr(process_controller_module, "PyMuPDFLoader", pdf_loader)

    assert controller.get_file_content("source.pdf") == loaded_documents
    pdf_loader.assert_called_once_with(str(pdf_file))
    loader.load.assert_called_once_with()

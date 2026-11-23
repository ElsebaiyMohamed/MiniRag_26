
from pathlib import Path

import pymupdf
import pytest

from ingestion.exceptions import UnsupportedFile
from ingestion.loaders.pdf import PdfLoader

PDF_FIXTURES = (
    Path(__file__).parent / "fixtures" / "docs" / "pdf"
)


def test_load_multipage_pdf():
    path = PDF_FIXTURES / "multipage" / "multipage_extractable_text.pdf"

    documents = PdfLoader().load(path)

    assert len(documents) == 8

    for page_number, document in enumerate(documents):
        assert document.text
        assert document.metadata["page"] == page_number
        assert document.metadata["total_pages"] == 8
        assert document.metadata["source"] == str(path.resolve())
        assert document.metadata["file_path"] == str(path.resolve())

    assert "PDF-MULTI-001" in documents[0].text


def test_encrypted_pdf_raises_unsupported_file():
    path = PDF_FIXTURES / "edge_cases" / "encrypted_password_fixture.pdf"

    with pytest.raises(UnsupportedFile, match="Encrypted PDF"):
        PdfLoader().load(path)


def test_corrupted_pdf_raises_unsupported_file():
    path = PDF_FIXTURES / "edge_cases" / "corrupted.pdf"

    with pytest.raises(
        UnsupportedFile,
        match="Corrupted PDF contains no recoverable pages",
    ):
        PdfLoader().load(path)


def test_image_only_pdf_returns_empty_text_without_ocr():
    path = PDF_FIXTURES / "edge_cases" / "image_only_no_ocr.pdf"

    documents = PdfLoader().load(path)

    assert documents
    assert all(document.text == "" for document in documents)

    for page_number, document in enumerate(documents):
        assert document.metadata["page"] == page_number
        assert document.metadata["total_pages"] == len(documents)


def test_empty_text_page_is_preserved(tmp_path):
    path = tmp_path / "empty_page.pdf"

    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()

    documents = PdfLoader().load(path)

    assert len(documents) == 1
    assert documents[0].text == ""
    assert documents[0].metadata["page"] == 0
    assert documents[0].metadata["total_pages"] == 1

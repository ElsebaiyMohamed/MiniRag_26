import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from controllers.ProcessController import Document, ProcessController


@pytest.fixture
def processor():
    """Instantiate ProcessController without triggering settings/path side effects."""
    with patch('controllers.BaseController.BaseController.__init__', return_value=None), \
         patch('controllers.ProcessController.ProjectController') as mock_pc:
        mock_pc.return_value.get_project_path.return_value = '/tmp/fake_project'
        yield ProcessController(project_id=1)


def test_groups_short_lines_into_single_chunk(processor):
    """Lines that fit under chunk_size are accumulated into one chunk."""
    pages = ["line one here\nline two here"]
    metadatas = [{"page": 1}]
    chunks = processor.simple_text_spliter(pages, metadatas, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0].page_content == "line one here\nline two here"
    assert chunks[0].metadata == {"page": 1}


def test_drops_single_char_lines(processor):
    """OLD behavior: lines with stripped length <= 1 are dropped."""
    pages = ["a\nbb\nccc"]
    metadatas = [{"page": 1}]
    chunks = processor.simple_text_spliter(pages, metadatas, chunk_size=1000)

    assert len(chunks) == 1
    # 'a' is dropped, only 'bb' and 'ccc' remain
    assert chunks[0].page_content == "bb\nccc"


def test_chunk_can_exceed_chunk_size_soft_limit(processor):
    """OLD behavior: a single long line is NOT split -> one chunk larger than chunk_size."""
    long_line = ("word " * 40).strip()  # ~200 chars, no newline
    pages = [long_line]
    metadatas = [{"page": 1}]
    chunks = processor.simple_text_spliter(pages, metadatas, chunk_size=50)

    assert len(chunks) == 1
    assert len(chunks[0].page_content) > 50  # soft limit, exceeds requested size


def test_flushes_chunk_when_exceeding_size(processor):
    """A chunk is flushed once accumulated text length exceeds chunk_size."""
    pages = ["aaaaaaaaaa\nbbbbbbbbbb\ncccccccccc"]  # three 10-char lines
    metadatas = [{"page": 1}]
    chunks = processor.simple_text_spliter(pages, metadatas, chunk_size=15)

    # line1+line2 exceed 15 -> flushed; line3 flushed at the end
    assert len(chunks) == 2
    assert chunks[0].page_content == "aaaaaaaaaa\nbbbbbbbbbb"
    assert chunks[1].page_content == "cccccccccc"


def test_metadata_passed_through(processor):
    """OLD behavior: chunk metadata is exactly the page metadata provided."""
    pages = ["some content here"]
    metadatas = [{"page": 3, "source": "file.pdf"}]
    chunks = processor.simple_text_spliter(pages, metadatas, chunk_size=1000)

    assert len(chunks) == 1
    assert chunks[0].metadata == {"page": 3, "source": "file.pdf"}


def test_process_file_content_overlap_has_no_effect(processor):
    """OLD behavior: overlap_size is accepted but never applied."""
    docs = [Document(page_content="hello world\nfoo bar baz", metadata={"page": 1})]

    chunks_no_overlap = processor.process_file_content(file_content=docs, chunk_size=1000, overlap_size=0)
    chunks_with_overlap = processor.process_file_content(file_content=docs, chunk_size=1000, overlap_size=50)

    assert [c.page_content for c in chunks_no_overlap] == [c.page_content for c in chunks_with_overlap]
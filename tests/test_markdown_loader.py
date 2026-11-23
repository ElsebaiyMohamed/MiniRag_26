import os
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")),
)

from ingestion.loaders import (
    MarkdownLoader,
    create_default_loader_registry,
)


@pytest.fixture
def loader():
    return MarkdownLoader()


@pytest.mark.parametrize("extension", [".md", ".markdown"])
def test_loads_markdown_extensions(loader, tmp_path, extension):
    path = tmp_path / f"document{extension}"
    path.write_text("# Heading\n\nMarkdown body.", encoding="utf-8")

    documents = loader.load(path)

    assert len(documents) == 1
    assert documents[0].text == "# Heading\n\nMarkdown body."
    assert documents[0].metadata == {"source": str(path)}


def test_preserves_markdown_structure(loader, tmp_path):
    content = (
        "# Heading\n\n"
        "- First item\n"
        "- Second item\n\n"
        "| Name | Value |\n"
        "| --- | --- |\n"
        "| Item | 42 |\n\n"
        "```python\n"
        "print('hello')\n"
        "```\n"
    )

    path = tmp_path / "structure.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == content


def test_removes_yaml_front_matter(loader, tmp_path):
    content = (
        "---\n"
        "title: Example\n"
        "author: Test\n"
        "---\n"
        "# Actual content\n\n"
        "Keep this body unchanged.\n"
    )

    path = tmp_path / "frontmatter.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == (
        "# Actual content\n\n"
        "Keep this body unchanged.\n"
    )


def test_removes_yaml_front_matter_with_crlf(loader, tmp_path):
    content = (
        "---\r\n"
        "title: Example\r\n"
        "---\r\n"
        "# Body\r\n"
    )

    path = tmp_path / "windows.md"
    path.write_bytes(content.encode("utf-8"))

    documents = loader.load(path)

    assert documents[0].text == "# Body\n"

def test_does_not_remove_unclosed_front_matter(loader, tmp_path):
    content = "---\ntitle: Example\n# Body\n"

    path = tmp_path / "unclosed.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == content


def test_strips_single_and_multiline_html_comments(loader, tmp_path):
    content = (
        "# Heading\n"
        "<!-- hidden comment -->\n"
        "Visible text.\n"
        "<!--\n"
        "hidden multiline comment\n"
        "-->\n"
        "Final text.\n"
    )

    path = tmp_path / "comments.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == (
        "# Heading\n\n"
        "Visible text.\n\n"
        "Final text.\n"
    )


def test_preserves_arabic_markdown(loader, tmp_path):
    content = "# العنوان\n\nهذا نص باللغة العربية.\n"

    path = tmp_path / "arabic.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == content


def test_loads_empty_markdown_file(loader, tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("", encoding="utf-8")

    documents = loader.load(path)

    assert len(documents) == 1
    assert documents[0].text == ""
    assert documents[0].metadata == {"source": str(path)}


def test_preserves_horizontal_rule_without_front_matter(loader, tmp_path):
    content = "# Heading\n\n---\n\nBody.\n"

    path = tmp_path / "horizontal-rule.md"
    path.write_text(content, encoding="utf-8")

    documents = loader.load(path)

    assert documents[0].text == content


def test_default_registry_registers_markdown_loader():
    registry = create_default_loader_registry()

    assert registry.supported_extensions() == {
        ".txt",
        ".pdf",
        ".md",
        ".markdown",
    }

    assert isinstance(
        registry.for_path(Path("document.md")),
        MarkdownLoader,
    )

    assert isinstance(
        registry.for_path(Path("document.markdown")),
        MarkdownLoader,
    )

def test_loads_utf8_with_bom(loader, tmp_path):
    content = "# UTF-8 Document\n\nContent with BOM."

    path = tmp_path / "utf8-bom.md"
    path.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

    documents = loader.load(path)

    assert documents[0].text == content


def test_loads_windows_1252(loader, tmp_path):
    content = (
        "# Café Documentation\n\n"
        "The price is 10 € — déjà vu."
    )

    path = tmp_path / "windows-1252.md"
    path.write_bytes(content.encode("cp1252"))

    documents = loader.load(path)

    assert documents[0].text == content


def test_loads_latin1_compatible_content(loader, tmp_path):
    content = (
        "# Documentation\n\n"
        "Café, naïve, résumé, and jalapeño."
    )

    path = tmp_path / "latin1.md"
    path.write_bytes(content.encode("iso-8859-1"))

    documents = loader.load(path)

    assert documents[0].text == content


def test_loads_arabic_windows_1256(loader, tmp_path):
    content = (
        "# توثيق المشروع\n\n"
        "هذا مستند باللغة العربية يحتوي على معلومات "
        "حول المشروع وطريقة استخدامه والميزات المتاحة."
    )

    path = tmp_path / "arabic-1256.md"
    path.write_bytes(content.encode("cp1256"))

    documents = loader.load(path)

    assert documents[0].text == content
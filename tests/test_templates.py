import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from stores.llm.templates.template_parser import TemplateParser


def test_template_parser_substitutes_prompt_variables():
    parser = TemplateParser(language="en")

    prompt = parser.get("rag", "document_prompt", {"doc_num": 2, "chunk_text": "facts"})

    assert "Document No: 2" in prompt
    assert "Content: facts" in prompt


def test_template_parser_falls_back_to_default_language():
    parser = TemplateParser(language="missing", default_language="en")

    prompt = parser.get("rag", "footer_prompt", {"query": "What happened?"})

    assert "What happened?" in prompt


def test_template_parser_returns_none_for_missing_group_or_key():
    parser = TemplateParser(language="en")

    assert parser.get("", "system_prompt") is None
    assert parser.get("missing", "unknown") is None
    assert parser.get("rag", "missing_prompt") is None

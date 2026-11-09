import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from models.schemas.nlp import SearchRequest


def test_search_request_debug_flag():
    req = SearchRequest(text="hello", limit=10)
    assert req.debug is False, "Debug flag should default to False"

    req_debug = SearchRequest(text="hello", limit=10, debug=True)
    assert req_debug.debug is True
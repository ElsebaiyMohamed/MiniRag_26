
from pathlib import Path

from main import app
from models.enums import ResponseSignal

API_DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "Api.md"


def _assert_documented(items: set[str], documentation: str, item_type: str):
    missing = sorted(item for item in items if item not in documentation)

    assert not missing, (
        f"Undocumented {item_type} in docs/Api.md:\n"
        + "\n".join(f"- {item}" for item in missing)
    )


def test_all_response_signals_are_documented():
    documentation = API_DOC_PATH.read_text(encoding="utf-8")
    signals = {signal.value for signal in ResponseSignal}

    _assert_documented(signals, documentation, "ResponseSignal values")


def test_all_openapi_paths_are_documented():
    documentation = API_DOC_PATH.read_text(encoding="utf-8")
    paths = set(app.openapi()["paths"])

    _assert_documented(paths, documentation, "OpenAPI paths")


def test_drift_check_detects_a_new_signal():
    documentation = API_DOC_PATH.read_text(encoding="utf-8")

    try:
        _assert_documented(
            {"TEMPORARY_DUMMY_SIGNAL"},
            documentation,
            "ResponseSignal values",
        )
    except AssertionError as exc:
        assert "TEMPORARY_DUMMY_SIGNAL" in str(exc)
    else:
        raise AssertionError("The drift check did not detect a missing signal")

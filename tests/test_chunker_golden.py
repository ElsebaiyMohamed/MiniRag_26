import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS_DIR = ROOT / "tests" / "fixtures" / "docs"
GOLDEN_DIR = ROOT / "tests" / "fixtures" / "golden"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from controllers.ProcessController import ProcessController
from scripts.generate_chunker_goldens import (
    discover_fixtures,
    load_fixture,
    normalize_metadata,
)


def golden_path_for(source_path: Path) -> Path:
    relative_source = source_path.relative_to(DOCS_DIR)
    return GOLDEN_DIR / relative_source.with_suffix(".json")


def read_golden(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_supported_fixture_has_a_golden():
    fixtures = discover_fixtures(DOCS_DIR, include_stress=False)

    expected = {golden_path_for(path) for path in fixtures}
    actual = set(GOLDEN_DIR.rglob("*.json")) if GOLDEN_DIR.exists() else set()

    missing = sorted(path.relative_to(ROOT).as_posix() for path in expected - actual)
    unexpected = sorted(path.relative_to(ROOT).as_posix() for path in actual - expected)

    assert not missing, f"Missing golden files. Regenerate them: {missing}"
    assert not unexpected, f"Goldens without matching fixtures: {unexpected}"


GOLDEN_FILES = sorted(GOLDEN_DIR.rglob("*.json")) if GOLDEN_DIR.exists() else []


@pytest.mark.parametrize(
    "golden_path",
    GOLDEN_FILES,
    ids=lambda path: path.relative_to(GOLDEN_DIR).as_posix(),
)
def test_legacy_chunker_matches_golden(golden_path: Path):
    golden = read_golden(golden_path)
    source_path = DOCS_DIR / golden["source"]

    assert source_path.is_file(), f"Missing source fixture: {source_path}"

    try:
        documents = load_fixture(source_path)
    except Exception as exc:
        assert golden.get("load_error", {}).get("type") == type(exc).__name__
        return

    assert "load_error" not in golden

    processor = object.__new__(ProcessController)

    chunks = processor.process_file_content(
        file_content=documents,
        chunk_size=golden["parameters"]["chunk_size"],
        overlap_size=golden["parameters"]["overlap_size"],
    )

    actual_chunks = [
        {
            "page_content": chunk.page_content,
            "metadata": normalize_metadata(chunk.metadata, DOCS_DIR),
        }
        for chunk in chunks
    ]

    assert actual_chunks == golden["chunks"]
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS_DIR = ROOT / "tests" / "fixtures" / "docs"
GOLDEN_DIR = ROOT / "tests" / "fixtures" / "golden"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

def _is_stress_enabled() -> bool:
    """Check if stress testing is enabled via environment variable or CLI flag."""
    return os.getenv("RUN_STRESS", "false").lower() in ("true", "1", "yes") or any("stress" in arg for arg in sys.argv)

# Module-level constant controlling stress inclusion
INCLUDE_STRESS = _is_stress_enabled()

def test_every_supported_fixture_has_a_golden():
    fixtures = discover_fixtures(DOCS_DIR, include_stress=INCLUDE_STRESS)

    expected = {golden_path_for(path) for path in fixtures}
    actual = set(GOLDEN_DIR.rglob("*.json")) if GOLDEN_DIR.exists() else set()
    if not INCLUDE_STRESS:
        actual = {p for p in actual if "stress" not in p.parts and "stress" not in p.name.lower()}
    missing = sorted(path.relative_to(ROOT).as_posix() for path in expected - actual)
    unexpected = sorted(path.relative_to(ROOT).as_posix() for path in actual - expected)

    assert not missing, f"Missing golden files. Regenerate them: {missing}"
    assert not unexpected, f"Goldens without matching fixtures: {unexpected}"


def _get_golden_files() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    all_files = sorted(GOLDEN_DIR.rglob("*.json"))
    if not INCLUDE_STRESS:
        return [f for f in all_files if "stress" not in f.parts and "stress" not in f.name.lower()]
    return all_files


GOLDEN_FILES = _get_golden_files()


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
    except Exception as exc:  # noqa: BLE001
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
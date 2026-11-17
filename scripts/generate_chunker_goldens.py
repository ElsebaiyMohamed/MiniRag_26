from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from controllers.ProcessController import ProcessController  # noqa: E402


SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate characterization goldens for the legacy TXT/PDF chunker."
    )
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--overlap-size", type=int, default=20)
    parser.add_argument(
        "--include-stress",
        action="store_true",
        help="Include large stress fixtures in golden generation."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "docs",
    )
    parser.add_argument(
        "--golden-dir",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "golden",
    )
    return parser.parse_args()


def discover_fixtures(docs_dir: Path, include_stress: bool = False) -> list[Path]:
    """Discover all supported fixtures, optionally including stress fixtures."""
    all_files = sorted(docs_dir.rglob("*.*"))
    supported_extensions = {".txt", ".pdf"}

    fixtures = [
        f for f in all_files
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    if not include_stress:
        fixtures = [
            f for f in fixtures
            if "stress" not in f.parts and "stress" not in f.name.lower()
        ]

    return fixtures


def load_fixture(path: Path):
    """Use the same document loaders as ProcessController."""
    extension = path.suffix.lower()

    if extension == ".txt":
        loader = TextLoader(str(path), encoding="utf-8")
    elif extension == ".pdf":
        loader = PyMuPDFLoader(str(path))
    else:
        raise ValueError(f"Unsupported fixture format: {path.suffix}")

    return loader.load()


def normalize_metadata(value: Any, docs_dir: Path) -> Any:
    """
    Normalize machine-specific source paths while preserving other metadata.

    The loader's absolute `source` path becomes a path relative to docs_dir.
    """
    if isinstance(value, dict):
        normalized = {}

        for key, item in value.items():
            if key == "source" and isinstance(item, str):
                try:
                    normalized_path = Path(item).resolve().relative_to(
                        docs_dir.resolve()
                    )
                    normalized[key] = normalized_path.as_posix()
                    continue
                except (OSError, ValueError):
                    pass

            normalized[key] = normalize_metadata(item, docs_dir)

        return normalized

    if isinstance(value, list):
        return [normalize_metadata(item, docs_dir) for item in value]

    return value


def build_golden(
    source_path: Path,
    docs_dir: Path,
    chunk_size: int,
    overlap_size: int,
) -> dict[str, Any]:
    relative_source = source_path.relative_to(docs_dir)

    golden: dict[str, Any] = {
        "schema_version": 1,
        "source": relative_source.as_posix(),
        "format": source_path.suffix.lower().lstrip("."),
        "parameters": {
            "chunk_size": chunk_size,
            "overlap_size": overlap_size,
        },
    }

    try:
        documents = load_fixture(source_path)
    except Exception as exc:
        # Keep the exception type, not its message: messages can contain
        # machine-specific paths or vary between dependency versions.
        golden["load_error"] = {
            "type": type(exc).__name__,
        }
        return golden

    # ProcessController's splitter does not depend on initialized controller
    # state. Avoid __init__, which creates project/settings side effects.
    processor = object.__new__(ProcessController)

    chunks = processor.process_file_content(
        file_content=documents,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
    )

    golden["chunks"] = [
        {
            "page_content": chunk.page_content,
            "metadata": normalize_metadata(chunk.metadata, docs_dir),
        }
        for chunk in chunks
    ]

    return golden


def write_golden(
    golden: dict[str, Any],
    source_path: Path,
    docs_dir: Path,
    golden_dir: Path,
) -> Path:
    relative_source = source_path.relative_to(docs_dir)

    # Keep the format/category directory structure, replacing the extension.
    output_path = golden_dir / relative_source.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(golden, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)

    return output_path


def main() -> int:
    args = parse_args()

    docs_dir = args.docs_dir.resolve()
    golden_dir = args.golden_dir.resolve()

    if not docs_dir.is_dir():
        print(f"Fixture directory does not exist: {docs_dir}", file=sys.stderr)
        return 1

    fixtures = discover_fixtures(docs_dir, args.include_stress)

    if not fixtures:
        print(f"No supported TXT/PDF fixtures found under: {docs_dir}")
        return 0

    generated = 0
    load_errors = 0

    for fixture in fixtures:
        golden = build_golden(
            source_path=fixture,
            docs_dir=docs_dir,
            chunk_size=args.chunk_size,
            overlap_size=args.overlap_size,
        )

        output_path = write_golden(
            golden=golden,
            source_path=fixture,
            docs_dir=docs_dir,
            golden_dir=golden_dir,
        )

        generated += 1

        if "load_error" in golden:
            load_errors += 1
            print(
                f"[LOAD ERROR] {fixture.relative_to(docs_dir)} "
                f"({golden['load_error']['type']})"
            )
        else:
            print(f"[GENERATED]  {output_path.relative_to(ROOT)}")

    print()
    print(f"Fixtures discovered: {len(fixtures)}")
    print(f"Goldens generated:   {generated}")
    print(f"Load errors stored:  {load_errors}")
    print(f"Output directory:    {golden_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
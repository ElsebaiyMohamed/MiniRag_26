from __future__ import annotations

import argparse
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "docs" / "Changelog.md"

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.dev$")
UNRELEASED_PATTERN = re.compile(
    r"(?m)^## \[Unreleased\]\s*$"
)
NEXT_SECTION_PATTERN = re.compile(
    r"(?m)^## \["
)


def read_project_version() -> str:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def update_project_version(content: str, new_version: str) -> str:
    pattern = re.compile(
        r"(?m)(^\[project\]\s*\n(?:(?!^\[).*\n)*?^version\s*=\s*)"
        r'(["\']).*?\2'
    )

    updated, count = pattern.subn(
        lambda match: f'{match.group(1)}"{new_version}"',
        content,
        count=1,
    )

    if count != 1:
        raise ValueError("Could not update [project].version in pyproject.toml")

    return updated


def prepare_changelog(
    content: str,
    version: str,
    release_date: str,
) -> tuple[str, str]:
    if re.search(
        rf"(?m)^## \[{re.escape(version)}\](?:\s|$)",
        content,
    ):
        raise ValueError(
            f"Changelog already contains a section for {version}"
        )

    unreleased = UNRELEASED_PATTERN.search(content)

    if not unreleased:
        raise ValueError("Could not find the Unreleased changelog section")

    section_start = unreleased.end()
    next_section = NEXT_SECTION_PATTERN.search(content, section_start)

    if not next_section:
        raise ValueError("Could not find the section following Unreleased")

    entries = content[section_start:next_section.start()].strip()

    if not entries:
        raise ValueError(
            "The Unreleased section is empty. Add changelog entries "
            "before creating a nightly release."
        )

    release_section = (
        f"## [{version}] - {release_date}\n\n"
        f"{entries}\n\n"
    )

    updated = (
        content[:unreleased.start()]
        + "## [Unreleased]\n\n"
        + release_section
        + content[next_section.start():]
    )

    return updated, release_section.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a versioned MiniRag development release."
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Development version, e.g. 1.3.1.dev",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Release date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--notes-file",
        default="release-notes.md",
        help="Path for the extracted release notes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview changes without modifying files.",
    )

    args = parser.parse_args()

    if not VERSION_PATTERN.fullmatch(args.version):
        parser.error("Version must follow the format X.Y.Z.dev")

    try:
        datetime.strptime(args.date, "%Y-%m-%d")

        with PYPROJECT.open("r", encoding="utf-8") as file:
            pyproject_content = file.read()

        with CHANGELOG.open("r", encoding="utf-8") as file:
            changelog_content = file.read()

        current_version = read_project_version()

        updated_pyproject = update_project_version(
            pyproject_content,
            args.version,
        )

        updated_changelog, release_notes = prepare_changelog(
            changelog_content,
            args.version,
            args.date,
        )

        if args.dry_run:
            print(f"Current version: {current_version}")
            print(f"New version:     {args.version}")
            print("\nRelease notes preview:\n")
            print(release_notes)
            print("\nDry run completed. No files were modified.")
            return 0

        PYPROJECT.write_text(updated_pyproject, encoding="utf-8")
        CHANGELOG.write_text(updated_changelog, encoding="utf-8")

        notes_path = Path(args.notes_file)
        if not notes_path.is_absolute():
            notes_path = ROOT / notes_path

        notes_path.write_text(release_notes, encoding="utf-8")

        print(f"Updated project version: {current_version} -> {args.version}")
        print(f"Updated changelog: {CHANGELOG}")
        print(f"Generated release notes: {notes_path}")

        return 0

    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
        print(f"Nightly release preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

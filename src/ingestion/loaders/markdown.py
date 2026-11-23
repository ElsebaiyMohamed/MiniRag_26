import re
from pathlib import Path
from typing import List

from charset_normalizer import from_bytes

from .base import LoadedDocument


class MarkdownLoader:
    extensions = (".md", ".markdown")
    mime_types = (
        "text/markdown",
        "text/x-markdown",
        "text/plain",
    )

    @staticmethod
    def _remove_yaml_front_matter(text: str) -> str:
        lines = text.splitlines(keepends=True)

        if not lines or lines[0].rstrip("\r\n") != "---":
            return text

        for index in range(1, len(lines)):
            delimiter = lines[index].rstrip("\r\n")

            if delimiter in ("---", "..."):
                return "".join(lines[index + 1:])

        # No closing delimiter: preserve the original content.
        return text

    @staticmethod
    def _strip_html_comments(text: str) -> str:
        return re.sub(
            r"<!--.*?(?:-->|$)",
            "",
            text,
            flags=re.DOTALL,
        )

    def load(self, path: Path) -> List[LoadedDocument]:
        raw_content = path.read_bytes()

        if not raw_content:
            text = ""
        else:
            matches = list(from_bytes(raw_content))

            if not matches:
                raise UnicodeError(
                    f"Could not detect the encoding of Markdown file: {path}"
                )

            detected = matches[0]

            # Prefer Windows-1252 when it is a close match.
            # Some single-byte Western encodings are indistinguishable
            # from short samples, and charset-normalizer may rank
            # less common encodings above it.
            windows_1252 = next(
                (match for match in matches if match.encoding == "cp1252"),
                None,
            )

            if (
                    windows_1252 is not None
                    and windows_1252.chaos <= detected.chaos + 0.01
                    and windows_1252.coherence >= detected.coherence - 0.10
            ):
                detected = windows_1252

            text = str(detected)
            text = text.removeprefix("\ufeff")

        # Normalize line endings across operating systems.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        text = self._remove_yaml_front_matter(text)
        text = self._strip_html_comments(text)

        return [
            LoadedDocument(
                text=text,
                metadata={"source": str(path)},
            )
        ]
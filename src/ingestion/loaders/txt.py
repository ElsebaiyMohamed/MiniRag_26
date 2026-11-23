from pathlib import Path
from typing import List

from .base import LoadedDocument


class TxtLoader:
    extensions = (".txt",)
    mime_types = ("text/plain",)

    def load(self, path: Path) -> List[LoadedDocument]:
        text = path.read_text(encoding="utf-8")

        return [
            LoadedDocument(
                text=text,
                metadata={"source": str(path)},
            )
        ]
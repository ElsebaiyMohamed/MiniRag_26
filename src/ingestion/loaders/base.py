from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, List, Tuple


@dataclass
class LoadedDocument:
    text: str
    metadata: dict


class DocumentLoader(Protocol):
    extensions: Tuple[str, ...]
    mime_types: Tuple[str, ...]

    def load(self, path: Path) -> List[LoadedDocument]:
        ...

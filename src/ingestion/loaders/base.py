from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, List, Tuple


@dataclass
class LoadedDocument:
    text: str
    metadata: dict

    @property
    def page_content(self) -> str:
        """Compatibility with LangChain Document."""
        return self.text


class DocumentLoader(Protocol):
    extensions: Tuple[str, ...]
    mime_types: Tuple[str, ...]

    def load(self, path: Path) -> List[LoadedDocument]:
        ...

from dataclasses import dataclass, field
from typing import Protocol, List, Dict, Any, Iterable

from ..loaders import LoadedDocument


@dataclass
class Chunk:
    """Represents a processed text chunk with its sequence order and metadata."""
    text: str
    order: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def page_content(self) -> str:
        """Compatibility with LangChain Document."""
        return self.text


class Chunker(Protocol):
    """Protocol defining the interface for document chunkers."""

    def chunk(
        self,
        documents: Iterable[LoadedDocument],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[Chunk]:
        ...
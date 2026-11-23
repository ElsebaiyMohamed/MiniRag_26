from .base import Chunker
from .default import DefaultChunker


class ChunkerFactory:
    """Factory to instantiate the configured chunker implementation."""
    def __init__(self):
        self._chunkers: dict[str, Chunker] = {}

    def register(self, name: str, chunker: Chunker) -> None:
        self._chunkers[name] = chunker

    def get_chunker(self, name: str):
        chunker = self._chunkers.get(name, DefaultChunker)
        return chunker

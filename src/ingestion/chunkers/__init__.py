from .base import Chunk, Chunker
from .default import DefaultChunker
from .factory import ChunkerFactory

def create_default_chunker_factory() -> ChunkerFactory:
    chunker_factory = ChunkerFactory()
    chunker_factory.register(name='default', chunker=DefaultChunker())
    # new register per chunkers

    return chunker_factory


__all__ = [
    Chunk,
    Chunker,
    DefaultChunker,
    ChunkerFactory,
    create_default_chunker_factory
]
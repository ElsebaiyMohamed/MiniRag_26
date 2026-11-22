from dataclasses import dataclass
from pathlib import Path
from typing import List, Iterable

from ingestion.chunkers import ChunkerFactory, Chunk
from ingestion.exceptions import UnsupportedFileType
from ingestion.loaders import LoaderRegistry, LoadedDocument
from .BaseController import BaseController
from .ProjectController import ProjectController


@dataclass
class Document:
    page_content: str
    metadata: dict


class ProcessController(BaseController):
    def __init__(
            self,
            project_id: int,
            loader_registry: LoaderRegistry,
            chunker_factory: ChunkerFactory
    ):
        super().__init__()

        self.project_id = str(project_id)
        self.project_path = ProjectController().get_project_path(self.project_id)
        self.loader_registry = loader_registry
        self.chunker_factory = chunker_factory


    def get_file_content(self, file_id: str):
        file_path = Path(self.join_path(self.project_path, file_id))

        if not self.file_exist_on_path(str(file_path)):
            return None

        try:
            loader = self.loader_registry.for_path(file_path)
        except UnsupportedFileType:
            return None

        return loader.load(file_path)

    def process_file_content(
        self,
        documents: Iterable[LoadedDocument],
        chunker: str = 'default',
        chunk_size: int = 100,
        overlap_size: int = 20,
    ) -> List[Chunk]:

        # LoadedDocument uses "text".
        # Legacy characterization fixtures use LangChain's "page_content".
        chunker = self.chunker_factory.get_chunker(name=chunker)
        return chunker.chunk(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=overlap_size
        )

    def process_file(
        self,
        file_id: str,
        chunker: str = 'default',
        chunk_size: int = 100,
        overlap_size: int = 20,
    ):
        """
        Load and split a file in one synchronous operation.

        This method is intended to run inside asyncio.to_thread().
        File loading (including PDF access) and splitting therefore
        happen in the same worker thread.
        """
        file_content = self.get_file_content(file_id)

        if file_content is None:
            return None

        return self.process_file_content(
            file_content=file_content,
            chunker=chunker,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
        )

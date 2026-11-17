from dataclasses import dataclass
from pathlib import Path
from typing import List

from ingestion.exceptions import UnsupportedFileType
from ingestion.loaders import LoaderRegistry
from .BaseController import BaseController
from .ProjectController import ProjectController


@dataclass
class Document:
    page_content: str
    metadata: dict


class ProcessController(BaseController):
    def __init__(self, project_id: int, loader_registry: LoaderRegistry,):
        super().__init__()

        self.project_id = str(project_id)
        self.project_path = ProjectController().get_project_path(self.project_id)
        self.loader_registry = loader_registry


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
        file_content: list,
        chunk_size: int = 100,
        overlap_size: int = 20,
    ):
        # LoadedDocument uses "text".
        # Legacy characterization fixtures use LangChain's "page_content".
        file_text = [
            document.text
            if hasattr(document, "text")
            else document.page_content
            for document in file_content
        ]

        file_metadata = [
            document.metadata
            for document in file_content
        ]

        chunks = self.simple_text_spliter(
            file_text,
            file_metadata,
            chunk_size=chunk_size,
        )

        return chunks


    def simple_text_spliter(self, pages: List[str], metadatas: List[dict], chunk_size: int, spliter_tag: str='\n'):
        chunks = []
        chunk_text = ''
        # page_no = set()
        for page, page_metadata in zip(pages, metadatas):
            page_lines = [l.strip() for l in page.split(spliter_tag) if len(l.strip()) >1]
            # page_no.add(page_metadata['page'])
            for i in range(len(page_lines)):
                line = page_lines[i]
                chunk_text = chunk_text + spliter_tag + line
                if len(chunk_text) > chunk_size:

                    # page_metadata['page'] = ', '.join(list(page_no))
                    chunks.append(Document(
                        page_content=chunk_text.strip(),
                        metadata=page_metadata
                    ))
                    # page_no = set()
                    chunk_text = ''
        if chunk_text:
            chunks.append(
                Document(
                    page_content=chunk_text.strip(),
                    metadata=page_metadata
                )
            )
        return chunks


    def process_file(
        self,
        file_id: str,
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
            chunk_size=chunk_size,
            overlap_size=overlap_size,
        )

from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyMuPDFLoader

from .base import LoadedDocument


class PdfLoader:
    extensions = (".pdf",)
    mime_types = ("application/pdf",)

    def load(self, path: Path) -> List[LoadedDocument]:
        documents = PyMuPDFLoader(str(path)).load()

        return [
            LoadedDocument(
                text=document.page_content,
                metadata=document.metadata,
            )
            for document in documents
        ]
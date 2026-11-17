from pathlib import Path
from typing import List

from langchain_community.document_loaders import TextLoader

from .base import LoadedDocument


class TxtLoader:
    extensions = (".txt",)
    mime_types = ("text/plain",)

    def load(self, path: Path) -> List[LoadedDocument]:
        documents = TextLoader(
            str(path),
            encoding="utf-8",
        ).load()

        return [
            LoadedDocument(
                text=document.page_content,
                metadata=document.metadata,
            )
            for document in documents
        ]
from typing import Iterable, List

from .base import Chunk
from ..loaders import LoadedDocument


class DefaultChunker:
    """Reproduces the exact legacy newline-based splitting behavior."""

    def chunk(
        self,
        documents: Iterable[LoadedDocument],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[Chunk]:
        # Note: chunk_overlap is accepted per protocol contract but ignored per legacy rules.
        chunks: List[Chunk] = []
        current_chunk_text = ""
        current_metadata = {}
        order = 0

        for doc in documents:
            doc_text = doc.text or ""
            doc_metadata = doc.metadata or {}
            lines = doc_text.split("\n")

            for line in lines:
                cleaned_line = line.strip()
                # Discard lines of length <= 1
                if len(cleaned_line) <= 1:
                    continue

                # If adding this line exceeds chunk_size and we already have text, flush current chunk
                if len(current_chunk_text) + len(cleaned_line) > chunk_size and current_chunk_text:
                    chunks.append(
                        Chunk(
                            text=current_chunk_text.strip(),
                            order=order,
                            metadata=current_metadata,
                        )
                    )
                    order += 1
                    current_chunk_text = ""

                # Append line to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n" + cleaned_line
                else:
                    current_chunk_text = cleaned_line
                    # Preserve the metadata of the page/document that triggers the flush / starts the chunk
                    current_metadata = doc_metadata

        # Flush any remaining text in the buffer
        if current_chunk_text:
            chunks.append(
                Chunk(
                    text=current_chunk_text.strip(),
                    order=order,
                    metadata=current_metadata,
                )
            )

        return chunks
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pymupdf

from .base import LoadedDocument
from ..exceptions import UnsupportedFile


def _normalize_pdf_date(value: str) -> str:
    """Convert a PDF date such as D:20261116051340+00'00' to ISO format."""
    if not value.startswith("D:"):
        return value

    date_part = value[2:16]
    try:
        parsed = datetime.strptime(date_part, "%Y%m%d%H%M%S")
    except ValueError:
        return value

    timezone_part = value[16:]
    if timezone_part:
        sign = 1 if timezone_part[0] == "+" else -1
        digits = "".join(char for char in timezone_part[1:] if char.isdigit())

        if len(digits) >= 4:
            offset_minutes = sign * (
                int(digits[:2]) * 60 + int(digits[2:4])
            )
            from datetime import timedelta

            parsed = parsed.replace(
                tzinfo=timezone(timedelta(minutes=offset_minutes))
            )
        else:
            parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.isoformat()


class PdfLoader:
    extensions = (".pdf",)
    mime_types = ("application/pdf",)

    def load(self, path: Path) -> List[LoadedDocument]:
        documents = []
        path = path.resolve()

        try:
            document = pymupdf.open(path)
        except Exception as exc:
            raise UnsupportedFile(f"Unable to open PDF: {path}") from exc

        try:
            if document.is_encrypted:
                raise UnsupportedFile(f"Encrypted PDF is not supported: {path}")
            if document.is_repaired and len(document) == 0:
                raise UnsupportedFile(
                    f"Corrupted PDF contains no recoverable pages: {path}"
                )
            metadata = {
                key: value
                for key, value in document.metadata.items()
                if isinstance(value, (str, int))
            }

            metadata.update({
                "source": str(path),
                "file_path": str(path),
                "total_pages": len(document),
            })

            for source_key, normalized_key in (
                ("creationDate", "creationdate"),
                ("modDate", "moddate"),
            ):
                value = metadata.get(source_key)
                if isinstance(value, str):
                    metadata[normalized_key] = _normalize_pdf_date(value)

            for page_number, page in enumerate(document):
                page_metadata = {
                    **metadata,
                    "page": page_number,
                }

                documents.append(
                    LoadedDocument(
                        text=page.get_text("text").strip(),
                        metadata=page_metadata,
                    )
                )
        finally:
            document.close()

        return documents
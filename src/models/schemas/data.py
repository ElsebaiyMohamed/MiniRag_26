from typing import Optional

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    chunker: Optional[str] = 'default'
    chunk_size: Optional[int] = 100
    overlap_size: Optional[int] = 20
    do_reset: Optional[int] = 0

class RetrievedDocument(BaseModel):
    text: str
    score: float

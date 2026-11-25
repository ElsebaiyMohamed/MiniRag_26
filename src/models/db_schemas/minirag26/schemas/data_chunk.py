import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from .base import SQLAlchemyBase


class DataChunk(SQLAlchemyBase):
    __tablename__ = 'chunks'

    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    chunk_text = Column(String, nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)
    chunk_order = Column(Integer, nullable=False)

    chunk_project_id = Column(
        Integer,
        ForeignKey('projects.project_id', ondelete="CASCADE"),
        nullable=False,
    )
    chunk_asset_id = Column(
        Integer,
        ForeignKey('assets.asset_id', ondelete="CASCADE"),
        nullable=False,
    )

    chunk_pushed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates='chunks')
    asset = relationship("Asset", back_populates='chunks')

    __table_args__ = (
        Index('ix_chunks_project_asset', chunk_project_id, chunk_asset_id),
        Index('ix_chunk_asset_id', chunk_asset_id),
    )
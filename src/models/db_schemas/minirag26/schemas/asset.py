import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from .base import SQLAlchemyBase


class Asset(SQLAlchemyBase):
    __tablename__ = 'assets'

    asset_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_size = Column(Integer, nullable=False)
    asset_config = Column(JSONB, nullable=True)
    asset_status = Column(Integer, nullable=False)

    asset_project_id = Column(
        Integer,
        ForeignKey('projects.project_id', ondelete="CASCADE"),
        nullable=False,
    )
    asset_pushed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates='assets')
    chunks = relationship(
        "DataChunk",
        back_populates='asset',
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            'asset_project_id',
            'asset_name',
            name='uq_assets_project_asset_name',
        ),
        CheckConstraint(
            'asset_status IN (0, 1, 2)',
            name='ck_assets_asset_status',
        ),
        Index('ix_asset_project_id', asset_project_id),
    )
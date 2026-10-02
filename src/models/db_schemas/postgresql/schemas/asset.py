import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index

from .base import SQLAlcemyBase


class Asset(SQLAlcemyBase):
    __tablename__ = 'assets'
    
    asset_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False) 
    asset_type = Column(String, nullable=False) 
    asset_name = Column(String, nullable=False) 
    asset_size = Column(Integer, nullable=False) 
    asset_config = Column(JSONB, nullable=True) 
    asset_project_id = Column(Integer, ForeignKey('projects.project_id'), autoincrement=True)
    asset_pushed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        
    
    project = relationship("Project", back_populates='assets')

    __table_args__ = (
        Index('ix_asset_project_id', asset_project_id),
    )

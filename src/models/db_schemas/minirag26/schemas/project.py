import uuid

from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship  

from .base import SQLAlcemyBase


class Project(SQLAlcemyBase):
    __tablename__ = 'projects'
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    assets = relationship("Asset", back_populates="project")
    chunks = relationship("DataChunk", back_populates="project")

import uuid
import datetime

from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from .base import SQLAlcemyBase


class Project(SQLAlcemyBase):
    __tablename__ = 'projects'
    
    project_id = Column(Integer, primary_ket=True, autoincrement=True)
    project_uuid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


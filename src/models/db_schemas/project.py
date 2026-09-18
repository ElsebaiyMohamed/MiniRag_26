from pydantic import BaseModel, Field
from typing import Optional
from bson.objectid import ObjectId



class Project(BaseModel):
    _id: Optional[ObjectId]
    project_id: str = Field(..., min_length=1)
    
    
    class Config:
        arbitrary_types_allowed = True
    

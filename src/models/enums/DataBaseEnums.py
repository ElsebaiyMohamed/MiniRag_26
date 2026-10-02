from enum import Enum

class AppDataBase(Enum):
    MONGO = 'mongo'
    POSTGRES = 'postgres'


class DataBaseEnum(Enum):
    COLLECTION_PROJECT_NAME = 'projects'
    COLLECTION_CHUNK_NAME = "chunks"
    COLLECTION_ASSET_NAME = 'assets'

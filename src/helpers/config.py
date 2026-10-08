from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    
    FILE_ALLOWED_EXTENTIONS: list
    FILE_MAX_SIZE_IN_MB: int
    FILE_DEAFAULT_CHINK_SIZE: int
    
    
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    VECTORDB_BACKEND_LITERAL: List[str] = None
    VECTORDB_BACKEND: str=""
    VECTOR_DB_FILE_PATH: str=""
    VECTOR_DB_DISTANCE_METRIC: str=''
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int
    
    OPENAI_API_KEY: str
    OPENAI_API_URL: str
    COHERE_API_KEY: str
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    
    GENERATION_MODEL_ID: str=None
    EMBEDDING_MODEL_ID: str=None
    EMBEDDING_MODEL_SIZE: int=None
    INPUT_DEFAULT_MAX_CHAR: int=None
    DEAFAULT_MAX_OUTPUT_TOKENS: int=None
    GENERATION_DEFAULT_TEMPERATURE: float=None
    

    # ========================= Template Configs =========================
    PRIMARY_LANG: str = "ar"
    DEFAULT_LANG: str = "en"
    
    class Config:
        env_file = ".env.app"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
def get_settings() -> Settings:
    return Settings()

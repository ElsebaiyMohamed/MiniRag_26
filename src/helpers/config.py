from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env.app"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", case_sensitive=True)

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
    VECTOR_DB_DISTANCE_METRIC: str = "cosine"
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int

    OPENAI_API_KEY: str | None = None
    OPENAI_API_URL: str | None = None
    COHERE_API_KEY: str | None = None

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    GENERATION_MODEL_ID: str=None
    EMBEDDING_MODEL_ID: str=None
    EMBEDDING_MODEL_SIZE: int=None
    INPUT_DEFAULT_MAX_CHAR: int=None
    DEAFAULT_MAX_OUTPUT_TOKENS: int=None
    GENERATION_DEFAULT_TEMPERATURE: float=None


    # ========================= Template Configs =========================
    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    @model_validator(mode="after")
    def _check_provider_keys(self):
        backends = {self.GENERATION_BACKEND, self.EMBEDDING_BACKEND}
        if "OPENAI" in backends and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when a backend is OPENAI")
        if "COHERE" in backends and not self.COHERE_API_KEY:
            raise ValueError("COHERE_API_KEY is required when a backend is COHERE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

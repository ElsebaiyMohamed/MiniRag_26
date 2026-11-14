import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[1] / ".env.app"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


    APP_NAME: str
    APP_DESCRIPTION: str

    FILE_ALLOWED_EXTENTIONS: list
    FILE_MAX_SIZE_IN_MB: int
    FILE_DEAFAULT_CHINK_SIZE: int
    PROCESSING_MAX_CONCURRENCY: int = Field(default=2, ge=1)

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    VECTORDB_BACKEND_LITERAL: list[str] | None = None
    VECTORDB_BACKEND: str = ""
    VECTOR_DB_DISTANCE_METRIC: str = "cosine"
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int

    OPENAI_API_KEY: str = None
    OPENAI_API_URL: str | None = None
    COHERE_API_KEY: str = None

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str



    LLM_REQUEST_TIMEOUT_SEC: int = 60
    GENERATION_MODEL_ID: str | None = None
    EMBEDDING_MODEL_ID: str | None = None
    EMBEDDING_MODEL_SIZE: int | None = None

    INPUT_DEFAULT_MAX_CHAR: int = 2048
    DEAFAULT_MAX_OUTPUT_TOKENS: int = 2048
    GENERATION_DEFAULT_TEMPERATURE: float = 0.001

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

    @model_validator(mode="before")
    @classmethod
    def warn_deprecated_app_version(cls, values):
        if isinstance(values, dict) and "APP_VERSION" in values:
            logger.warning("APP_VERSION is deprecated and ignored. " "Use the version declared in pyproject.toml.")
            values.pop("APP_VERSION")

        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()

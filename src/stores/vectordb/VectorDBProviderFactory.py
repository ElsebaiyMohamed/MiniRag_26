
from sqlalchemy.orm import sessionmaker

from controllers import BaseController
from models.enums import VectorDBEnums
from .providers import PgVector


class VectorDBProviderFactory:
    def __init__(self, config, db_client: sessionmaker=None):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client
    def create(self, provider: str):
        if provider == VectorDBEnums.PGVECTOR.value:
            return PgVector(
                db_client=self.db_client,
                distance_method=self.config.VECTOR_DB_DISTANCE_METRIC,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD
            )
        raise ValueError(
            f"Unsupported VectorDB provider '{provider}'. Supported: PGVECTOR")

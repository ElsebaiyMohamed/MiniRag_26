
from sqlalchemy.orm import sessionmaker

from models.enums import VectorDBEnums
from controllers import BaseController
from .providers import QdrantDB, PgVector



class VectorDBProviderFactory:
    def __init__(self, config, db_client: sessionmaker=None):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client
    def create(self, provider: str):
        if provider == VectorDBEnums.QDRANT.value:
            return QdrantDB(
                db_client=self.base_controller.get_database_path(self.config.VECTOR_DB_FILE_PATH),
                distance_method=self.config.VECTOR_DB_DISTANCE_METRIC
            )
        
        if provider == VectorDBEnums.PGVECTOR.value:
            return PgVector(
                db_client=self.db_client,
                distance_method=self.config.VECTOR_DB_DISTANCE_METRIC,
                default_vector_size=self.config.EMBEDDING_MODEL_SIZE,
                index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD
            )
        return None

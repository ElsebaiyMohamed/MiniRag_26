from enum import Enum

class VectorDBEnums(Enum):
    QDRANT = 'QDRANT'
    PGVECTOR = 'PGVECTOR'
    


class PgVectorTableSchemaEnums(Enum):
    ID = 'id'
    TEXT = 'text'
    VECTOR = 'vector'
    CHUNK_ID = 'chunk_id'
    METADATA = 'metadata'
    _PREFIX = 'pgvector'
    
class DistanceMethodEnums(Enum):
    COSINE = 'cosine'
    DOT = 'dot'
class PgVectorDistanceMethodEnums(Enum):
    COSINE = 'vector_cosine_ops'
    DOT = 'vector_12_ops'

class PgVectorIndexEnums(Enum):
    HNSW = 'hnsw'
    IVFFLAT = 'ivfflat'


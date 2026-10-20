from enum import Enum

class VectorDBEnums(Enum):
    PGVECTOR = 'PGVECTOR'



class PgVectorTableSchemaEnums(Enum):
    ID = 'id'
    TEXT = 'text'
    VECTOR = 'vector'
    CHUNK_ID = 'chunk_id'
    ASSET_ID = 'asset_id'
    METADATA = 'metadata'
    _PREFIX = 'pgvector'

class DistanceMethodEnums(Enum):
    COSINE = 'cosine'
    DOT = 'dot'
class PgVectorDistanceMethodEnums(Enum):
    COSINE = 'vector_cosine_ops'
    DOT = 'vector_ip_ops'
class PgVectorOperatorEnums(Enum):            # query operator
    COSINE = '<=>'
    DOT = '<#>'

class PgVectorIndexEnums(Enum):
    HNSW = 'hnsw'
    IVFFLAT = 'ivfflat'


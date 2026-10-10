APP_NAME="MiniRag_26"
APP_VERSION="0.1"
APP_DESCRIPTION="Question Answering System"


FILE_ALLOWED_EXTENTIONS=["application/pdf", "text/plain"]
FILE_MAX_SIZE_IN_MB=10
FILE_DEAFAULT_CHINK_SIZE=256000 # 256kp

# ========================== Database Config ======================

POSTGRES_USERNAME="postgres"
POSTGRES_PASSWORD=""
POSTGRES_HOST="pgvector"
POSTGRES_PORT=5433
POSTGRES_MAIN_DATABASE="minirag26"

# ========================== Vector Database Config ======================
VECTORDB_BACKEND_LITERAL=["QDRANT", "PGVECTOR"]
VECTORDB_BACKEND="PGVECTOR"
VECTOR_DB_FILE_PATH="qdrant_db"
VECTOR_DB_DISTANCE_METRIC="cosine"
VECTOR_DB_PGVEC_INDEX_THRESHOLD=1500

# ========================== LLM Config ======================
OPENAI_API_KEY=""
OPENAI_API_URL=""
COHERE_API_KEY=""
GENERATION_BACKEND="COHERE"
EMBEDDING_BACKEND="COHERE"

GENERATION_MODEL_ID="command-r-plus-08-2024"
"
EMBEDDING_MODEL_ID="embed-english-light-v3.0"
EMBEDDING_MODEL_SIZE="384"

INPUT_DEFAULT_MAX_CHAR=1024
DEAFAULT_MAX_OUTPUT_TOKENS=200
GENERATION_DEFAULT_TEMPERATURE=0.1

# ========================= Template Configs =========================
PRIMARY_LANG = "en"
DEFAULT_LANG = "en"

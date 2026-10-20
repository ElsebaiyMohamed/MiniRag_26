from enum import Enum

class ResponseSignal(Enum):
    FILE_VALIDATED_SUCCESS = 'file validated success'
    FILE_TYPE_NOT_SUPPORTED = 'file type not supported'
    FILE_SIZE_EXCEEDED = 'file size exceeded'
    FILE_UPLOAD_FAILED = 'file upload failed'
    FILE_UPLOAD_SUCCESS = 'file upload success'
    PROJECT_NOT_FOUND = 'project not found'
    NO_FILES_ERROR = 'project is empty'
    FILES_ALREADY_PROCESSED="Project files are already up-to-date. No further processing required."
    PROCESSING_FAILED = 'file chunking failed'
    PROCESSING_SUCCESS = 'file chunking success'
    FILES_NEED_CHUNKING = 'chunk files first before indexing'
    NO_FILES_TO_BE_INDEXED = 'project chunked files already indexed'
    INSERT_INTO_VECTORDB_ERROR = 'failed to insert into vector database'
    INSERT_INTO_VECTOR_DATABASE_SUCCESS= "file indexed successfully"
    VECTORDB_COLLECTION_INFO_RETRIEVED = 'collection information retrieved successfully'
    VECTORDB_COLLECTION_INFO_NOT_FOUND = 'the collection not found'
    VECTORDB_SEARCH_ERROR = 'vectordb search error'
    VECTORDB_SEARCH_SUCCESS = 'vectordb search success'
    RAG_ANSWER_SUCCESS = 'rag answer success'
    RAG_ANSWER_ERROR = 'rag answer error'
